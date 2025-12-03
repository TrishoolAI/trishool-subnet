"""
REST API Client for Alignet Subnet Validator.

This module provides a REST API client for connecting to the subnet platform
and fetching miner submissions, submitting scores, etc.
"""

import asyncio
import json
import logging
import aiohttp
from typing import Dict, Any, Optional, List, Union
import os
import sys
from datetime import datetime

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from alignet.cli.bts_signature import load_wallet, build_pair_auth_payload

from alignet.utils.logging import get_logger
logger = get_logger()


class PlatformAPIClient:
    """REST API client for connecting to the subnet platform."""
    
    def __init__(
        self,
        platform_api_url: str = "http://localhost:8000",
        coldkey_name: Optional[str] = None,
        hotkey_name: Optional[str] = None,
        network: str = "finney",
        netuid: int = 35,
    ):
        """
        Initialize the REST API client.
        
        Args:
            platform_api_url: Base URL of the platform API
            coldkey_name: Coldkey name for authentication
            hotkey_name: Hotkey name for authentication
            network: Bittensor network (default: finney)
            netuid: Subnet UID (default: 35)
        """
        self.platform_api_url = platform_api_url.rstrip('/')
        self.coldkey_name = coldkey_name or os.getenv("COLDKEY_NAME")
        self.hotkey_name = hotkey_name or os.getenv("HOTKEY_NAME")
        self.network = network
        self.netuid = netuid
        self.wallet = None
        
        # Load wallet if credentials provided
        if self.coldkey_name and self.hotkey_name:
            try:
                self.wallet = load_wallet(self.coldkey_name, self.hotkey_name)
                logger.info(f"Loaded wallet: {self.coldkey_name}/{self.hotkey_name}")
            except Exception as e:
                logger.warning(f"Failed to load wallet: {str(e)}")
        
        logger.info(f"PlatformAPIClient initialized with URL: {self.platform_api_url}")
    
    def _build_auth_headers(self) -> Dict[str, str]:
        """
        Build authentication headers with signature.
        
        Returns:
            Dictionary with authentication headers
        """
        if not self.wallet:
            raise ValueError("Wallet not loaded. Cannot build auth headers.")
        
        payload = build_pair_auth_payload(
            network=self.network,
            netuid=self.netuid,
            slot="1",
            wallet_name=self.coldkey_name,
            wallet_hotkey=self.hotkey_name,
        )
        
        headers = {
            "X-Sign-Message": payload["message"],
            "X-Signature": payload["signature"],
            "Content-Type": "application/json",
        }
        
        return headers
    
    async def get_evaluation_agents(self) -> Optional[Dict[str, Any]]:
        """
        Get PetriConfig for evaluation submission.
        
        Returns:
            PetriConfigResponse dictionary or None if no submission available
        """
        try:
            headers = self._build_auth_headers()
            url = f"{self.platform_api_url}/api/v1/validator/evaluation-agents"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data:
                            return data
                        else:
                            logger.debug("No evaluation submission available")
                            return None
                    elif response.status == 404:
                        # No submission available
                        logger.debug("No evaluation submission available (404)")
                        return None
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get evaluation agents: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error fetching evaluation agents: {str(e)}")
            return None
    
    async def submit_scores(self, scores: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Submit scores for miner submissions.
        
        Args:
            scores: List of score dictionaries with 'agent_id' and 'score' keys
            
        Returns:
            Response dictionary with status, message, session_id, and count
        """
        try:
            headers = self._build_auth_headers()
            url = f"{self.platform_api_url}/api/v1/validator/submit_scores"
            
            # Format scores according to API spec
            # API expects: {"scores": [{"agent_id": "...", "score": 0.0}]}
            body = {
                "scores": [
                    {"agent_id": score["agent_id"], "score": score["score"]}
                    for score in scores
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=body) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Submitted {len(scores)} scores successfully")
                        return data
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to submit scores: {response.status} - {error_text}")
                        return {
                            "status": "error",
                            "message": f"HTTP {response.status}: {error_text}",
                            "session_id": None,
                            "count": 0
                        }
                        
        except Exception as e:
            logger.error(f"Error submitting scores: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "session_id": None,
                "count": 0
            }
    
    async def submit_petri_output(
        self, 
        submission_id: str, 
        petri_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Submit full Petri evaluation output to platform.
        
        Args:
            submission_id: Submission ID
            petri_output: Full Petri output JSON (containing run_id, timestamp, config, results, summary)
            
        Returns:
            Response dictionary with status, message, and run_id
        """
        try:
            os.makedirs("score_submissions", exist_ok=True)
            url = f"{self.platform_api_url}/api/v1/validator/submit_scores/{submission_id}"

            async with aiohttp.ClientSession() as session:
                ## retry 3 times
                error_text = None
                for i in range(3):
                    headers = self._build_auth_headers()
                    # save request to file
                    # with open(f"score_submissions/{submission_id}_request.json", "w") as f:
                    #     petri_output["submission_id"] = submission_id
                    #     petri_output["headers"] = headers
                    #     json.dump(petri_output, f, indent=2)

                    async with session.post(url, headers=headers, json=petri_output) as response:
                        if response.status == 200:
                            data = await response.json()
                            logger.info(f"Submitted Petri output for submission {submission_id}, run_id: {petri_output.get('run_id', 'unknown')}")
                            return data
                        else:
                            error_text = await response.text()
                            logger.error(f"Failed to submit Petri output, retrying... ({i+1}/3)")
                            await asyncio.sleep(1)    

                logger.error(f"Failed to submit Petri output: {error_text}")
                return {
                    "status": "error",
                    "message": error_text,
                    "run_id": petri_output.get("run_id", "")
                }
        except Exception as e:
            logger.error(f"Error submitting Petri output: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "run_id": petri_output.get("run_id", "")
            }
    
    async def get_weights(self) -> Optional[Dict[str, float]]:
        """
        Get weights from platform API.
        
        Returns:
            Dictionary mapping miner UID (as string) to weight, or None if failed
        """
        try:
            headers = self._build_auth_headers()
            url = f"{self.platform_api_url}/api/v1/validator/weights"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        weights = data.get("weights", {})
                        logger.info(f"Fetched weights for {len(weights)} miners from platform")
                        ## save response to file
                        # os.makedirs("./outputs", exist_ok=True)
                        # with open(f"./outputs/weights_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
                        #     json.dump(weights, f, indent=2)
                        return weights
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get weights: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error getting weights: {str(e)}")
            return None
    
    async def healthcheck(self) -> bool:
        """
        Send healthcheck to platform.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            headers = self._build_auth_headers()
            url = f"{self.platform_api_url}/api/v1/validator/healthcheck"
            
            body = {
                "hotkey": self.wallet.hotkey.ss58_address if self.wallet else ""
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=body) as response:
                    if response.status == 200:
                        logger.debug("Healthcheck successful")
                        return True
                    else:
                        logger.warning(f"Healthcheck failed: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error sending healthcheck: {str(e)}")
            return False

