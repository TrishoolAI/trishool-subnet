"""
Tests for platform API endpoints
Tests for /upload and /evaluation-agents endpoints
"""
import asyncio
import sys
import json
from pathlib import Path
import aiohttp
from io import BytesIO
from dotenv import load_dotenv
load_dotenv()

sys.path.append("../")
from alignet.cli.bts_signature import load_wallet, build_pair_auth_payload

# Configuration - Update these with your test wallet credentials
COLDKEY_NAME = "ckorintest1"
HOTKEY_NAME = "hk2"
PLATFORM_API_URL = "http://34.59.172.160:8000"
NETWORK = "finney"
NETUID = 35
SLOT = "1"


class PlatformAPITester:
    """Test class for platform API endpoints"""

    def __init__(
        self,
        platform_api_url: str = PLATFORM_API_URL,
        coldkey_name: str = COLDKEY_NAME,
        hotkey_name: str = HOTKEY_NAME,
        network: str = NETWORK,
        netuid: int = NETUID,
        slot: str = SLOT,
    ):
        self.platform_api_url = platform_api_url.rstrip("/")
        self.coldkey_name = coldkey_name
        self.hotkey_name = hotkey_name
        self.network = network
        self.netuid = netuid
        self.slot = slot

    def _build_auth_payload(self):
        """Build authentication payload with signature"""
        wallet = load_wallet(self.coldkey_name, self.hotkey_name)
        payload = build_pair_auth_payload(
            network=self.network,
            netuid=self.netuid,
            slot=self.slot,
            wallet_name=self.coldkey_name,
            wallet_hotkey=self.hotkey_name,
        )
        return {
            "hotkey": wallet.hotkey.ss58_address,
            "message": payload["message"],
            "signature": payload["signature"],
            "expires_at": payload["expires_at"],
        }

    async def test_upload_agent(
        self, agent_content: str = None, filename: str = "agent.txt"
    ):
        """
        Test uploading a miner agent to the platform.

        Args:
            agent_content: Content of the agent file (default: sample agent code)
            filename: Name of the file to upload (must be .txt)

        Returns:
            Response JSON from the API
        """
        if agent_content is None:
            agent_content = "# Sample agent code\nclass Agent:\n    def run(self):\n        return 'Hello from agent'\n"

        print(f"\n{'='*60}")
        print("Testing /api/v1/miner/upload endpoint")
        print(f"{'='*60}")

        # Build authentication payload
        auth_data = self._build_auth_payload()
        print(f"Hotkey: {auth_data['hotkey']}")
        print(f"Message: {auth_data['message']}")
        print(f"Signature: {auth_data['signature'][:50]}...")
        print(f"Expires at: {auth_data['expires_at']}")

        # Prepare multipart form data
        form_data = aiohttp.FormData()
        form_data.add_field(
            "agent_file",
            agent_content.encode("utf-8"),
            filename=filename,
            content_type="text/plain",
        )
        form_data.add_field("message", auth_data["message"])
        form_data.add_field("expires_at", str(int(auth_data["expires_at"])))
        form_data.add_field("signature", auth_data["signature"])

        print(f"\nUploading agent file: {filename}")
        print(f"Agent content length: {len(agent_content)} bytes")

        # Send request
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.platform_api_url}/api/v1/miner/upload",
                data=form_data,
            ) as response:
                response_json = await response.json()
                print(f"\nResponse status: {response.status}")
                print(f"Response: {json.dumps(response_json, indent=2)}")

                if response.status == 201:
                    print("\n✅ Upload successful!")
                else:
                    print(f"\n❌ Upload failed with status {response.status}")

                return response_json

    async def test_get_evaluation_agents(self):
        """
        Test getting evaluation agents (Petri config) from the platform.

        Returns:
            Response JSON from the API (PetriConfigResponse or None)
        """
        print(f"\n{'='*60}")
        print("Testing /api/v1/validator/evaluation-agents endpoint")
        print(f"{'='*60}")

        # Build authentication payload
        auth_data = self._build_auth_payload()
        print(f"Hotkey: {auth_data['hotkey']}")
        print(f"Message: {auth_data['message']}")
        print(f"Signature: {auth_data['signature'][:50]}...")

        # Prepare headers with signature information
        headers = {
            "X-Sign-Message": auth_data["message"],
            "X-Signature": auth_data["signature"],
            "Content-Type": "application/json",
        }

        print(f"\nRequesting evaluation agents...")

        # Send request
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.platform_api_url}/api/v1/validator/evaluation-agents",
                headers=headers,
            ) as response:
                response_json = await response.json()
                print(f"\nResponse status: {response.status}")
                print(f"Response: {json.dumps(response_json, indent=2)}")

                if response.status == 200:
                    if response_json:
                        print("\n✅ Evaluation agents retrieved successfully!")
                        print(f"   Submission ID: {response_json.get('submission_id')}")
                        print(f"   Run ID: {response_json.get('run_id')}")
                    else:
                        print("\n⚠️  No evaluation agents available (returned None)")
                else:
                    print(f"\n❌ Request failed with status {response.status}")

                return response_json

    async def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*60)
        print("Platform API Test Suite")
        print("="*60)
        print(f"Platform URL: {self.platform_api_url}")
        print(f"Coldkey: {self.coldkey_name}")
        print(f"Hotkey: {self.hotkey_name}")
        print(f"Network: {self.network}, NetUID: {self.netuid}, Slot: {self.slot}")

        try:
            # Test 1: Upload agent
            print("\n" + "-"*60)
            print("TEST 1: Upload Agent")
            print("-"*60)
            upload_result = await self.test_upload_agent()

            # Wait a bit between requests
            await asyncio.sleep(1)

            # Test 2: Get evaluation agents
            print("\n" + "-"*60)
            print("TEST 2: Get Evaluation Agents")
            print("-"*60)
            evaluation_result = await self.test_get_evaluation_agents()

            print("\n" + "="*60)
            print("Test Suite Completed")
            print("="*60)
            print(f"Upload test: {'✅ PASSED' if upload_result.get('status') == 'success' else '❌ FAILED'}")
            print(f"Evaluation agents test: {'✅ PASSED' if evaluation_result is not None or evaluation_result == {} else '⚠️  NO DATA'}")

        except Exception as e:
            print(f"\n❌ Error running tests: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Main function to run tests"""
    import argparse

    parser = argparse.ArgumentParser(description="Test platform API endpoints")
    parser.add_argument(
        "--api-url",
        type=str,
        default=PLATFORM_API_URL,
        help=f"Platform API URL (default: {PLATFORM_API_URL})",
    )
    parser.add_argument(
        "--coldkey",
        type=str,
        default=COLDKEY_NAME,
        help=f"Coldkey name (default: {COLDKEY_NAME})",
    )
    parser.add_argument(
        "--hotkey",
        type=str,
        default=HOTKEY_NAME,
        help=f"Hotkey name (default: {HOTKEY_NAME})",
    )
    parser.add_argument(
        "--network",
        type=str,
        default=NETWORK,
        help=f"Network name (default: {NETWORK})",
    )
    parser.add_argument(
        "--netuid",
        type=int,
        default=NETUID,
        help=f"Network UID (default: {NETUID})",
    )
    parser.add_argument(
        "--slot",
        type=str,
        default=SLOT,
        help=f"Slot number (default: {SLOT})",
    )
    parser.add_argument(
        "--test",
        type=str,
        choices=["upload", "evaluation", "all"],
        default="all",
        help="Which test to run (default: all)",
    )

    args = parser.parse_args()

    tester = PlatformAPITester(
        platform_api_url=args.api_url,
        coldkey_name=args.coldkey,
        hotkey_name=args.hotkey,
        network=args.network,
        netuid=args.netuid,
        slot=args.slot,
    )

    if args.test == "upload":
        await tester.test_upload_agent()
    elif args.test == "evaluation":
        await tester.test_get_evaluation_agents()
    else:
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())

