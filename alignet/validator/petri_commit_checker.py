"""
Petri Commit Checker for Alignet Subnet Validator.

This module checks for new commits on the astro-petri repository
and triggers Docker image rebuild when updates are detected.
"""

import asyncio
import logging
import subprocess
import os
from typing import Optional
import aiohttp
from alignet.validator.sandbox.sandbox_management import SandboxManager

from alignet.utils.logging import get_logger
logger = get_logger()

PETRI_REPO_URL = "https://github.com/AstrowareAI/astro-petri.git"
PETRI_REPO_BRANCH = "alignet"
COMMIT_CHECK_INTERVAL = 300  # Check every 5 minutes
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Optional: GitHub token for higher rate limits


class PetriCommitChecker:
    """Checks for new commits on astro-petri repository and rebuilds Docker image."""
    
    def __init__(
        self,
        sandbox_manager: SandboxManager,
        check_interval: int = COMMIT_CHECK_INTERVAL
    ):
        """
        Initialize the commit checker.
        
        Args:
            sandbox_manager: SandboxManager instance for rebuilding images
            check_interval: Interval in seconds between checks (default: 5 minutes)
        """
        self.sandbox_manager = sandbox_manager
        self.check_interval = check_interval
        self.last_commit_hash: Optional[str] = None
        self.running = False
        self.check_task: Optional[asyncio.Task] = None
        
        logger.info(f"PetriCommitChecker initialized (check interval: {check_interval}s)")
        if GITHUB_TOKEN:
            logger.info("GitHub token found - using authenticated API requests (higher rate limit)")
        else:
            logger.info("No GitHub token - using unauthenticated API requests (60 req/h limit)")
    
    async def get_latest_commit_hash(self) -> Optional[str]:
        """
        Get the latest commit hash from the astro-petri repository.
        
        Returns:
            Latest commit hash or None if failed
        """
        try:
            # Use GitHub API to get latest commit
            api_url = f"https://api.github.com/repos/AstrowareAI/astro-petri/commits/{PETRI_REPO_BRANCH}"
            
            # GitHub API requires User-Agent header, otherwise returns 403
            # Using format from test_github_api.py
            headers = {
                "Accept": "application/vnd.github+json",
                "User-Agent": "Alignet-Subnet-Validator/1.0",
            }
            
            # Add Authorization header if token is provided (for higher rate limits)
            if GITHUB_TOKEN:
                headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
            
            timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(api_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        commit_hash = data.get("sha", "").strip()
                        if commit_hash:
                            logger.debug(f"Latest commit hash: {commit_hash[:8]}")
                            return commit_hash
                    elif response.status == 403:
                        # Check if it's rate limiting
                        rate_limit_remaining = response.headers.get("X-RateLimit-Remaining")
                        rate_limit_reset = response.headers.get("X-RateLimit-Reset")
                        try:
                            error_text = await response.text()
                            error_preview = error_text[:200] if error_text else "N/A"
                        except:
                            error_preview = "Could not read response body"
                        logger.warning(
                            f"GitHub API returned 403. "
                            f"Rate limit remaining: {rate_limit_remaining}, "
                            f"Reset at: {rate_limit_reset}. "
                            f"Response: {error_preview}"
                        )
                        return None
                    else:
                        try:
                            error_text = await response.text()
                            error_preview = error_text[:200] if error_text else "N/A"
                        except:
                            error_preview = "Could not read response body"
                        logger.warning(
                            f"Failed to fetch commit hash: HTTP {response.status}. "
                            f"Response: {error_preview}"
                        )
                        return None
                        
        except asyncio.TimeoutError:
            logger.error("Timeout while fetching latest commit hash from GitHub API")
            return None
        except Exception as e:
            logger.error(f"Error fetching latest commit hash: {str(e)}")
            return None
    
    async def check_and_rebuild(self) -> bool:
        """
        Check for new commits and rebuild Docker image if needed.
        
        Returns:
            True if rebuild was triggered, False otherwise
        """
        try:
            latest_commit = await self.get_latest_commit_hash()
            
            if not latest_commit:
                logger.warning("Could not fetch latest commit hash, skipping check")
                return False
            
            
            # Check if commit has changed
            if self.last_commit_hash is None or latest_commit != self.last_commit_hash:
                logger.info(
                    f"New commit detected! "
                    f"Old: {self.last_commit_hash[:8] if self.last_commit_hash else 'None'}, "
                    f"New: {latest_commit[:8]}. "
                    f"Triggering Docker image rebuild..."
                )
                
                # Rebuild the Petri Docker image
                try:
                    self.sandbox_manager._build_petri_image()
                    self.last_commit_hash = latest_commit
                    logger.info("Petri Docker image rebuilt successfully")
                    return True
                except Exception as e:
                    logger.error(f"Failed to rebuild Petri Docker image: {str(e)}")
                    return False
            else:
                logger.debug(f"No new commits (current: {latest_commit[:8]})")
                return False
                
        except Exception as e:
            logger.error(f"Error in check_and_rebuild: {str(e)}")
            return False

