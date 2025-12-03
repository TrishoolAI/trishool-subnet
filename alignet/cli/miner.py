#!/usr/bin/env python3
"""
Miner CLI tool for uploading agent files to the Platform API

This CLI tool allows miners to easily upload their agent text files (.txt)
to the platform with proper authentication and signature verification.

Usage:
    python -m miner upload \
        --agent-file seed_prompt.txt \
        --coldkey ckorintest1 \
        --hotkey hk1 \
        --network finney \
        --netuid 23 \
        --slot 1 \
        --api-url http://localhost:8000
"""

import argparse
import sys
import os
from pathlib import Path
import hashlib
import requests
from requests.exceptions import RequestException
from datetime import datetime

import bittensor as bt
from rich.console import Console
import typer
import time
from datetime import datetime, timezone
from typing import Any

console = Console(log_time_format="[%Y-%m-%d %H:%M:%S]")

CHALLENGE_PREFIX = "pair-auth"
CHALLENGE_TTL_SECONDS = 120


########################################################################################################################
# SIGNATURE GENERATION
########################################################################################################################


def get_wallet(name: str, hotkey: str) -> bt.wallet:
    if bt is None:  # pragma: no cover
        raise RuntimeError("bittensor is not installed")
    return bt.wallet(name=name, hotkey=hotkey)


def load_wallet(wallet_name: str, wallet_hotkey: str) -> bt.wallet:
    try:
        wallet = get_wallet(wallet_name, wallet_hotkey)
    except bt.KeyFileError as exc:
        console.log(
            "[bold red]Missing hotkey files[/] "
            f"for wallet '{wallet_name}/{wallet_hotkey}'. Import or create the wallet before retrying."
        )
        raise typer.Exit(code=1) from exc
    except Exception as exc:  # pragma: no cover - defensive
        console.log(f"[bold red]Failed to load wallet[/]: {exc}")
        raise typer.Exit(code=1) from exc

    return wallet


def build_pair_auth_payload(
    *,
    network: str,
    netuid: int,
    slot: str,
    wallet_name: str,
    wallet_hotkey: str,
) -> dict[str, Any]:
    wallet = load_wallet(wallet_name, wallet_hotkey)
    # _ensure_pair_registered(network=network, netuid=netuid, slot=slot, hotkey=hotkey)

    timestamp = int(time.time())
    message = (
        f"{CHALLENGE_PREFIX}|network:{network}|netuid:{netuid}|slot:{slot}|"
        f"hotkey:{wallet.hotkey.ss58_address}|ts:{timestamp}"
    )
    message_bytes = message.encode("utf-8")
    signature_bytes = wallet.hotkey.sign(message_bytes)

    verifier_keypair = bt.Keypair(ss58_address=wallet.hotkey.ss58_address)
    if not verifier_keypair.verify(message_bytes, signature_bytes):
        console.log("[bold red]Unable to verify the ownership signature locally.[/]")
        raise typer.Exit(code=1)

    expires_at = timestamp + CHALLENGE_TTL_SECONDS
    expiry_time = datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat()
    console.log(
        "[bold green]Ownership challenge signed[/] "
        f"(expires in {CHALLENGE_TTL_SECONDS}s at {expiry_time})."
    )

    return {
        "message": message,
        "signature": "0x" + signature_bytes.hex(),
        "expires_at": expires_at,
    }


class MinerCLI:
    """CLI interface for miner operations"""

    def __init__(self, api_url: str):
        """
        Initialize the Miner CLI

        Args:
            api_url: Base URL of the Platform API
        """
        self.api_url = api_url.rstrip("/")
        self.upload_endpoint = f"{self.api_url}/api/v1/miner/upload"

    def validate_agent_file(self, file_path: Path) -> None:
        """
        Validate the agent file

        Args:
            file_path: Path to the agent file

        Raises:
            ValueError: If validation fails
        """
        if not file_path.exists():
            raise ValueError(f"Agent file not found: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        if file_path.stat().st_size == 0:
            raise ValueError("Agent file is empty")

        # Check if file is .txt file
        if file_path.suffix != ".txt":
            raise ValueError(f"Agent file must be a .txt file, got: {file_path.suffix}")

    def upload_agent(
        self,
        agent_file: Path,
        hotkey: str,
        coldkey: str,
        network: str = "finney",
        netuid: int = 23,
        slot: str = "1",
    ) -> dict:
        """
        Upload agent file to the platform
        """
        # Validate agent file
        self.validate_agent_file(agent_file)

        pair_auth = build_pair_auth_payload(
            network=network,
            netuid=netuid,
            slot=slot,
            wallet_name=coldkey,
            wallet_hotkey=hotkey,
        )
        payload = {
            "message": pair_auth["message"],
            "signature": pair_auth["signature"],
            "expires_at": int(pair_auth["expires_at"]),
        }

        # Read file content
        with open(agent_file, "rb") as f:
            file_content = f.read()

        # Prepare multipart form data (use content, not file handle)
        files = {"agent_file": ("agent.txt", file_content, "text/plain")}

        # Send request
        try:
            response = requests.post(
                self.upload_endpoint,
                files=files,
                data=payload,
                timeout=30,
            )

            # Check response
            response.raise_for_status()

            return response.json()

        except RequestException as e:
            error_msg = f"Upload failed: {e}"
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg = f"Upload failed: {error_detail.get('detail', str(e))}"
                except:
                    error_msg = f"Upload failed: {e.response.text}"
            raise RequestException(error_msg) from e


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for the CLI"""
    parser = argparse.ArgumentParser(
        description="Miner CLI tool for uploading agents to Platform API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload agent with default settings
  python -m alignet.cli.miner upload --agent-file ./agent.txt --hotkey YOUR_HOTKEY --coldkey YOUR_COLDKEY --version 1.0.0 --name "My Agent"
  
  # Upload to custom API URL
  python -m alignet.cli.miner upload --agent-file ./agent.txt --hotkey YOUR_HOTKEY --coldkey YOUR_COLDKEY --version 1.0.0 --name "My Agent" --api-url https://api.example.com
  
  # Disable SSL verification (for development only)
  python -m alignet.cli.miner upload --agent-file ./agent.txt --hotkey YOUR_HOTKEY --coldkey YOUR_COLDKEY --version 1.0.0 --name "My Agent" --no-verify-ssl
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Upload command
    upload_parser = subparsers.add_parser(
        "upload", help="Upload agent file to the platform"
    )

    upload_parser.add_argument(
        "--agent-file",
        type=str,
        required=True,
        help="Path to the agent text file (.txt)",
    )

    upload_parser.add_argument(
        "--hotkey", type=str, required=True, help="Miner hotkey (hot wallet address)"
    )

    upload_parser.add_argument(
        "--coldkey", type=str, required=True, help="Miner coldkey (cold wallet address)"
    )

    upload_parser.add_argument(
        "--network", type=str, required=True, help="Network name"
    )

    upload_parser.add_argument("--netuid", type=int, required=True, help="Network UID")

    upload_parser.add_argument("--slot", type=str, required=True, help="Slot number")

    upload_parser.add_argument(
        "--api-url",
        type=str,
        default="http://localhost:8000",
        help="Platform API base URL (default: http://localhost:8000)",
    )

    return parser


def main():
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "upload":
        try:
            # Initialize CLI
            cli = MinerCLI(api_url=args.api_url)

            # Convert agent file path to Path object
            agent_file = Path(args.agent_file).resolve()

            # Display upload details and ask for confirmation
            print("\n" + "=" * 60)
            print("Upload Details:")
            print("=" * 60)
            print(f"Agent File:  {agent_file}")
            print(f"Hotkey:      {args.hotkey}")
            print(f"Coldkey:     {args.coldkey}")
            print(f"Network:     {args.network}")
            print(f"NetUID:      {args.netuid}")
            print(f"Slot:        {args.slot}")
            print(f"API URL:     {args.api_url}")
            print("=" * 60)

            # Ask for confirmation
            confirmation = (
                input("\nDo you want to proceed with the upload? (y/n): ")
                .strip()
                .lower()
            )

            if confirmation != "y":
                print("\n✗ Upload cancelled by user.\n")
                sys.exit(0)

            # Upload agent
            result = cli.upload_agent(
                agent_file=agent_file,
                hotkey=args.hotkey,
                coldkey=args.coldkey,
                network=args.network,
                netuid=args.netuid,
                slot=args.slot,
            )

            # Print success message
            print("\n" + "=" * 60)
            print("✓ Upload Successful!")
            print("=" * 60)
            print(f"Status:  {result.get('status', 'unknown')}")
            print(f"Message: {result.get('message', 'No message')}")
            print("=" * 60 + "\n")

            sys.exit(0)

        except ValueError as e:
            print(f"\n✗ Validation Error: {e}\n", file=sys.stderr)
            sys.exit(1)

        except RequestException as e:
            print(f"\n✗ Upload Error: {e}\n", file=sys.stderr)
            sys.exit(1)

        except Exception as e:
            print(f"\n✗ Unexpected Error: {e}\n", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
