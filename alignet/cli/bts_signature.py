from datetime import datetime

import bittensor as bt
from rich.console import Console
import typer
import time
from datetime import datetime, timezone
from typing import Any

# console = Console(log_time_format="[%Y-%m-%d %H:%M:%S]")
## import logger
from alignet.utils.logging import get_logger
logger = get_logger()

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
        logger.info(
            f"[bold red]Missing hotkey files[/] for wallet '{wallet_name}/{wallet_hotkey}'. Import or create the wallet before retrying."
        )
        raise typer.Exit(code=1) from exc
    except Exception as exc:  # pragma: no cover - defensive
        logger.info(f"[bold red]Failed to load wallet[/]: {exc}")
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
        logger.info("[bold red]Unable to verify the ownership signature locally.[/]")
        raise typer.Exit(code=1)

    expires_at = timestamp + CHALLENGE_TTL_SECONDS
    expiry_time = datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat()
    logger.info(
        f"[bold green]Ownership challenge signed[/] (expires in {CHALLENGE_TTL_SECONDS}s at {expiry_time})."
    )

    return {
        "message": message,
        "signature": "0x" + signature_bytes.hex(),
        "expires_at": expires_at,
    }


# def main(args):
#     payload = _build_pair_auth_payload(
#         network="finney",
#         netuid=23,
#         slot="1",
#         wallet_name=args.coldkey_name,
#         wallet_hotkey=args.hotkey_name,
#     )
#     print(payload)

#     # save payload to file
#     with open("payload.json", "w") as f:
#         json.dump(payload, f)


# if __name__ == "__main__":
#     import argparse

#     parser = argparse.ArgumentParser(description="Generate a signature")
#     parser.add_argument("--message", help="The message to sign", type=str)
#     parser.add_argument("--coldkey_name", help="The coldkey name", type=str)
#     parser.add_argument("--hotkey_name", help="The hotkey name", type=str)
#     args = parser.parse_args()

#     main(args)
