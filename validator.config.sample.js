/**
 * PM2 Ecosystem Configuration for Trishool Subnet
 * 
 * Usage:
 *   pm2 start validator.config.js
 *   pm2 restart trishool-subnet
 *   pm2 stop trishool-subnet
 *   pm2 logs trishool-subnet
 *   pm2 monit
 */

module.exports = {
  apps: [
    {
      name: "trishool-subnet",
      script: "neurons/validator.py",
      interpreter: "/Users/user_name/miniconda3/envs/alignnet/bin/python", // Change to your python environment
      autorestart: true,
      
      // Environment variables
      env: {
        CHUTES_API_KEY: "",
        CHUTES_BASE_URL: "https://llm.chutes.ai/v1",
        OPENAI_API_BASE: "https://llm.chutes.ai/v1",
        PLATFORM_API_URL: "https://api.trishool.ai",
        MAX_TURNS: 3,
        MAX_CONCURRENT_SANDBOXES: 3,
        EVALUATION_INTERVAL: 30,  // Interval to fetch submissions 
        SCORE_SUBMISSION_INTERVAL: 60,  // Interval to submit scores (seconds)
        RANDOM_SELECTION_COUNT: 3,
        SKIP_BUILD_IMAGE: false,
        PETRI_COMMIT_CHECK_INTERVAL: 300,  // Interval to check commits (seconds, default 5 minutes)
        GITHUB_TOKEN: "", // Your GitHub token for higher rate limits
        TELEGRAM_BOT_TOKEN: "", // Telegram bot token for sending errors to Telegram
        TELEGRAM_CHANNEL_ID: "", // Telegram channel ID for sending errors to Telegram
      },
      args: ["--netuid", "23", "--subtensor.network", "finney", "--wallet.name", "your_wallet_name", "--wallet.hotkey", "your_hotkey_name"],
    }
  ]
};

