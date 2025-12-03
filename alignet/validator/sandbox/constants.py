"""
Constants for sandbox management.
"""

# Docker image tag
PETRI_SANDBOX_IMAGE = "petri_sandbox:latest"

# Container paths
SANDBOX_MOUNT_PATH = "/sandbox"
CONFIG_FILE_NAME = "config.json"
OUTPUT_FILE_NAME = "output.json"
RUN_SCRIPT_NAME = "run.sh"

# Container commands
RUN_SCRIPT_COMMAND = f"/bin/bash {SANDBOX_MOUNT_PATH}/{RUN_SCRIPT_NAME} 2>&1"

# Config file paths
CONFIG_FILE_PATH = f"{SANDBOX_MOUNT_PATH}/{CONFIG_FILE_NAME}"
OUTPUT_FILE_PATH = f"{SANDBOX_MOUNT_PATH}/outputs/{OUTPUT_FILE_NAME}"

# Default values
DEFAULT_OUTPUT_DIR = "outputs"
DEFAULT_RUN_ID = "unknown"

# Container environment variables
PYTHONUNBUFFERED = "1"

