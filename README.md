# Trishool Subnet

A Bittensor subnet for evaluating and detecting behavioral traits in Large Language Models (LLMs). This system creates a competitive environment where miners submit seed instructions (prompts) that are tested using the Petri alignment auditing agent to identify potentially problematic behaviors such as deception, sycophancy, manipulation, overconfidence, and power-seeking tendencies.

## Overview

Trishool is designed to advance AI safety by creating a decentralized platform for behavioral evaluation. The system consists of three main components:

- **Miners**: Submit seed instructions (prompts) for testing behavioral traits via platform API
- **Validators**: Fetch submissions via REST API, run Petri agent in Docker sandboxes, and submit scores back to platform
- **Subnet Platform**: Manages submissions via REST API, validates submissions, stores results in database

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  MINER (Competition Participant)                            │
│  - Submits seed instruction (prompt) via platform API       │
│  - Max 200 words, tested for jailbreak attempts             │
│  - Submits PetriConfig: seed, models, auditor, judge, etc.  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼ (REST API)
┌─────────────────────────────────────────────────────────────┐
│  PLATFORM (Subnet Infrastructure)                           │
│  - Receives miner submissions (seed instructions)           │
│  - Validates submissions (duplicate check, jailbreak check) │
│  - Provides REST API endpoints for validators               │
│  ├─ GET /api/v1/validator/evaluation-agents                 │
│  └─ POST /api/v1/validator/submit_petri_output              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼ (REST API Polling)
┌─────────────────────────────────────────────────────────────┐
│  VALIDATOR SYSTEM (Competition Organizer)                   │
│  ├─ REST API Client: Fetches submissions periodically       │
│  ├─ Evaluation Loop: Fetches PetriConfig from platform      │
│  ├─ Sandbox Manager: Creates config.json, runs Petri        │
│  ├─ Score Extraction: Extracts scores from Petri output     │
│  ├─ Score Submission: Submits Petri output to platform      │
│  ├─ Weight Update Loop: Fetches weights from platform       │
│  │  └─ Sets weights on Bittensor chain                      │
│  └─ Commit Checker: Monitors astro-petri repo updates       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  PETRI SANDBOX (Docker Container)                           │
│  ├─ config.json: PetriConfig (mounted from temp_dir)        │
│  ├─ run.sh: Executes astro-petri run --config config.json   │
│  ├─ Runs Petri against target models (from config)          │
│  └─ Outputs to /sandbox/outputs/output.json                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  PETRI OUTPUT JSON                                          │
│  - run_id: Unique run identifier                            │
│  - results: Per-model evaluation results                    │
│  - summary.overall_metrics: Aggregated scores               │
│    ├─ mean_score: Average score across models               │
│    └─ final_score: Final evaluation score                   │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start
### Prerequisites

- PM2. Follow this link: [pm2 installation](https://pm2.io/docs/runtime/guide/installation/)
- Docker, docker compose
- Python 3.12

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables**:
- Create file validator.config.js from validator.config.sample.js
- Create file repo-auto-updater.config.js from repo-auto-updater.config.sample.js
- Fill all parameters in both config files 

### Running the Validator

To run validator:
```bash
pm2 start validator.config.js 
```

To run repo-auto-updater to auto update subnet code. This process keep checking latest commit_hash, if latest commit_hash changes -> auto git pull -> restart validator.
```bash
pm2 start repo-auto-updater.config.js
```

The validator will:
- Build Petri sandbox Docker image (if not exists) - installs astro-petri from GitHub (branch `alignet`)
- Start commit checker to monitor astro-petri repo for updates
- Start evaluation loop to periodically fetch challenge (PetriConfig) from platform API (`/evaluation-agents`)
- Start weight update loop to periodically fetch weights from platform API (`/weights`) and set them on chain
- Process submissions in sandboxes (respecting `MAX_CONCURRENT_SANDBOXES` limit)
- Validate submissions (immediately submit failed evaluation if validation fails)
- Create `config.json` from PetriConfig and run Petri agent
- Extract scores from Petri output JSON
- Immediately submit Petri output JSON back to platform API (`/submit_petri_output`) after evaluation completes
- Periodically sync metagraph and update weights on Bittensor chain from platform

### For Miners

```bash
python -m alignet.cli.miner upload \                                                                                                       
   --agent-file your_seed_prompt.txt \
   --coldkey coldkey_name \
   --hotkey hotkey_name \
   --network test_or_finney \
   --netuid netUID \
   --slot miner_uid \
   --api-url https://api.trishool.ai
```

Miners submit **seed instructions** (prompts) via the platform API. The platform creates a PetriConfig that includes:
- Your seed instruction
- Target models to evaluate
- Auditor and judge models
- Evaluation parameters (max_turns, etc.)

**Requirements:**
- Maximum 2500 characters
- Must not contain jailbreak attempts
- Will be tested for similarity against existing submissions (duplicate detection)
- Should be designed to probe target models for specific behavioral traits


**Submission Flow:**
1. Submit seed instruction via platform API
2. Platform validates and creates PetriConfig includes miner_seed_instruction and challenge config
3. Validators fetch your PetriConfig
4. Petri agent evaluates your seed against target models
5. Results are scored and submitted back to platform
6. Your score is based on the Petri evaluation results

**Testing locally:**
Miners can test their seed instructions locally using Petri before submission. See the Petri documentation at `trishool/validator/sandbox/petri/PETRI_README.md` or the astro-petri repository at https://github.com/Trishool/astro-petri for details on running Petri locally.

## Key Features

### 🔒 **Security-First Design**
- **Jailbreak Detection**: Validates seed instructions for jailbreak attempts
- **Immediate Failure Reporting**: Failed validations are immediately reported to platform
- **Duplicate Detection**: Checks for similar seed instructions to prevent gaming
- **Sandbox Isolation**: Petri runs in isolated Docker containers
- **Fraud Detection**: Comprehensive monitoring for manipulation attempts

### 🏆 **Competition Ready**
- **Miner Submissions**: Submit seed instructions (prompts) for testing
- **Automated Validation**: Petri agent tests against 5 models (1 misaligned)
- **Binary Scoring**: Returns 1.0 if correct model selected, 0.0 otherwise
- **Transparent Scoring**: Detailed feedback and execution logs

### 🛡️ **Anti-Cheating Measures**
- **Jailbreak Verification**: Guard LLM checks submissions for jailbreak attempts
- **Duplicate Verification**: LLM judge checks for similar prompts (<50% variation)
- **Submission Limits**: 1 submission per miner per day
- **Resource Limits**: Sandbox timeout and resource constraints


## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions and support, please open an issue on GitHub or join our community discussions.
