"""
Petri Commit Checker for Alignet Subnet Validator.

This module checks for new commits on the astro-petri repository
and triggers Docker image rebuild when updates are detected.
"""

from alignet.validator.base_commit_checker import BaseCommitChecker
from alignet.validator.sandbox.sandbox_management import SandboxManager
from alignet.validator.constants import (
    PETRI_REPO_OWNER,
    PETRI_REPO_NAME,
    PETRI_REPO_BRANCH,
    PETRI_COMMIT_CHECK_INTERVAL,
)
from alignet.utils.logging import get_logger

logger = get_logger()


class PetriCommitChecker(BaseCommitChecker):
    """Checks for new commits on astro-petri repository and rebuilds Docker image."""
    
    def __init__(
        self,
        sandbox_manager: SandboxManager,
        check_interval: int = PETRI_COMMIT_CHECK_INTERVAL
    ):
        """
        Initialize the commit checker.
        
        Args:
            sandbox_manager: SandboxManager instance for rebuilding images
            check_interval: Interval in seconds between checks (default: 5 minutes)
        """
        super().__init__(
            repo_owner=PETRI_REPO_OWNER,
            repo_name=PETRI_REPO_NAME,
            repo_branch=PETRI_REPO_BRANCH,
            check_interval=check_interval
        )
        self.sandbox_manager = sandbox_manager
    
    async def on_commit_detected(self, commit_hash: str) -> bool:
        """
        Handle new commit detection by rebuilding Docker image.
        
        Args:
            commit_hash: The new commit hash
            
        Returns:
            True if rebuild was successful, False otherwise
        """
        try:
            logger.info(f"Triggering Docker image rebuild for commit {commit_hash[:8]}...")
            
            # Rebuild the Petri Docker image
            self.sandbox_manager._build_petri_image()
            logger.info("Petri Docker image rebuilt successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to rebuild Petri Docker image: {str(e)}")
            return False
    
    async def check_and_rebuild(self) -> bool:
        """
        Check for new commits and rebuild Docker image if needed.
        
        Returns:
            True if rebuild was triggered, False otherwise
        """
        return await self.check_and_update()

