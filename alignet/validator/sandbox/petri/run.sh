#!/bin/bash
set -e

cd /sandbox

# Read config.json
if [ ! -f /sandbox/config.json ]; then
    echo "Error: config.json not found"
    exit 1
fi

echo "Running Petri agent with config.json..."
echo "Config file: /sandbox/config.json"

# Run Petri with config file
# Using astro-petri run --config config.json
# Output will be written to the path specified in json_output field of config
# According to PETRI_README.md, results are saved to outputs/output.json
astro-petri run --config /sandbox/config.json

# Get run_id and output_dir from config.json
RUN_ID=$(python3 -c "import json; f=open('/sandbox/config.json'); c=json.load(f); print(c.get('run_id', 'unknown')); f.close()")
OUTPUT_DIR=$(python3 -c "import json; f=open('/sandbox/config.json'); c=json.load(f); print(c.get('output_dir', './outputs')); f.close()")

# Petri saves results to outputs/output.json
OUTPUT_PATH="/sandbox/${OUTPUT_DIR}/output.json"

# Check if output file exists
if [ ! -f "${OUTPUT_PATH}" ]; then
    echo "Error: Output file not found at ${OUTPUT_PATH}"
    exit 1
fi
