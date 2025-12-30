#!/usr/bin/env python3
"""
Test script for PlatformAPIClient.upload_log function.

This script tests the upload_log functionality by:
1. Creating test log and transcript files
2. Uploading them to the platform API
3. Verifying the upload results

Usage:
    python tests/test_upload_log.py --coldkey-name <coldkey> --hotkey-name <hotkey> [options]
"""

import argparse
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

from alignet.validator.platform_api_client import PlatformAPIClient
from alignet.utils.logging import get_logger

logger = get_logger()


def create_test_log_file(file_path: Path, content: str = None) -> Path:
    """Create a test log file."""
    if content is None:
        content = f"""Test log file created at {datetime.now().isoformat()}
This is a test log file for upload_log testing.
Line 1: Test log entry
Line 2: Another test log entry
Line 3: Final test log entry
"""
    
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info(f"Created test log file: {file_path}")
    return file_path


def create_test_transcript_file(file_path: Path, content: dict = None) -> Path:
    """Create a test transcript file."""
    if content is None:
        content = {
            "run_id": "test_run_123",
            "timestamp": datetime.now().isoformat(),
            "sample_id": "test_sample_1",
            "transcript": {
                "messages": [
                    {"role": "user", "content": "Test message 1"},
                    {"role": "assistant", "content": "Test response 1"}
                ]
            },
            "metadata": {
                "test": True,
                "created_at": datetime.now().isoformat()
            }
        }
    
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(content, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Created test transcript file: {file_path}")
    return file_path


async def test_upload_log_file(
    client: PlatformAPIClient,
    log_file: Path,
    expected_success: bool = True
) -> bool:
    """
    Test uploading a log file.
    
    Args:
        client: PlatformAPIClient instance
        log_file: Path to log file to upload
        expected_success: Whether upload is expected to succeed
        
    Returns:
        True if test passed, False otherwise
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing upload_log with log file: {log_file.name}")
    logger.info(f"{'='*60}")
    
    try:
        result = await client.upload_log(str(log_file), "log")
        
        if expected_success:
            if result.get("status") == "success":
                logger.info(f"✅ Test PASSED: Log file uploaded successfully")
                logger.info(f"   Response: {result}")
                return True
            else:
                logger.error(f"❌ Test FAILED: Expected success but got: {result}")
                return False
        else:
            if result.get("status") == "error":
                logger.info(f"✅ Test PASSED: Expected error occurred: {result.get('message')}")
                return True
            else:
                logger.error(f"❌ Test FAILED: Expected error but got success: {result}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Test FAILED with exception: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def test_upload_transcript_file(
    client: PlatformAPIClient,
    transcript_file: Path,
    expected_success: bool = True
) -> bool:
    """
    Test uploading a transcript file.
    
    Args:
        client: PlatformAPIClient instance
        transcript_file: Path to transcript file to upload
        expected_success: Whether upload is expected to succeed
        
    Returns:
        True if test passed, False otherwise
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing upload_log with transcript file: {transcript_file.name}")
    logger.info(f"{'='*60}")
    
    try:
        result = await client.upload_log(str(transcript_file), "transcript")
        
        if expected_success:
            if result.get("status") == "success":
                logger.info(f"✅ Test PASSED: Transcript file uploaded successfully")
                logger.info(f"   Response: {result}")
                return True
            else:
                logger.error(f"❌ Test FAILED: Expected success but got: {result}")
                return False
        else:
            if result.get("status") == "error":
                logger.info(f"✅ Test PASSED: Expected error occurred: {result.get('message')}")
                return True
            else:
                logger.error(f"❌ Test FAILED: Expected error but got success: {result}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Test FAILED with exception: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description="Test PlatformAPIClient.upload_log function")
    parser.add_argument(
        "--platform-api-url",
        type=str,
        default=os.getenv("PLATFORM_API_URL", "http://localhost:8000"),
        help="Platform API URL"
    )
    parser.add_argument(
        "--coldkey-name",
        type=str,
        required=True,
        help="Coldkey name for authentication"
    )
    parser.add_argument(
        "--hotkey-name",
        type=str,
        required=True,
        help="Hotkey name for authentication"
    )
    parser.add_argument(
        "--network",
        type=str,
        default=os.getenv("NETWORK", "test"),
        help="Bittensor network"
    )
    parser.add_argument(
        "--netuid",
        type=int,
        default=int(os.getenv("NETUID", "292")),
        help="Subnet UID"
    )
    parser.add_argument(
        "--test-dir",
        type=str,
        default=None,
        help="Directory to create test files (default: temp directory)"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up test files after testing"
    )
    
    args = parser.parse_args()
    
    # Create test directory
    if args.test_dir:
        test_dir = Path(args.test_dir)
        test_dir.mkdir(parents=True, exist_ok=True)
    else:
        test_dir = Path(tempfile.mkdtemp(prefix="test_upload_log_"))
    
    logger.info(f"Test directory: {test_dir}")
    
    # Initialize client
    logger.info("Initializing PlatformAPIClient...")
    client = PlatformAPIClient(
        platform_api_url=args.platform_api_url,
        coldkey_name=args.coldkey_name,
        hotkey_name=args.hotkey_name,
        network=args.network,
        netuid=args.netuid
    )
    
    if not client.wallet:
        logger.error("Failed to load wallet. Cannot proceed with tests.")
        return 1
    
    # Create test files
    logger.info("\nCreating test files...")
    test_log_file = create_test_log_file(test_dir / "test_events.log")
    test_log_file_with_timestamp = create_test_log_file(
        test_dir / "test_events_2025-12-30_14-30-00.log",
        "Test log file with timestamp in filename\n"
    )
    test_transcript_file = create_test_transcript_file(test_dir / "test_transcript.json")
    
    # Run tests
    logger.info("\n" + "="*60)
    logger.info("Starting upload_log tests...")
    logger.info("="*60)
    
    test_results = []
    
    # Test 1: Upload log file
    result1 = await test_upload_log_file(client, test_log_file, expected_success=True)
    test_results.append(("Upload log file", result1))
    
    # Test 2: Upload log file with timestamp
    result2 = await test_upload_log_file(client, test_log_file_with_timestamp, expected_success=True)
    test_results.append(("Upload log file with timestamp", result2))
    
    # Test 3: Upload transcript file
    result3 = await test_upload_transcript_file(client, test_transcript_file, expected_success=True)
    test_results.append(("Upload transcript file", result3))
    
    # Print summary
    logger.info("\n" + "="*60)
    logger.info("Test Summary")
    logger.info("="*60)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    # Cleanup
    if args.cleanup:
        logger.info(f"\nCleaning up test files in {test_dir}...")
        import shutil
        if test_dir.exists() and not args.test_dir:  # Only delete if temp directory
            shutil.rmtree(test_dir)
            logger.info("Test files cleaned up")
    else:
        logger.info(f"\nTest files kept in: {test_dir}")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

