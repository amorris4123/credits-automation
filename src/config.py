"""
Configuration management for Credits Automation Bot
Loads settings from environment variables and .env file
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
project_root = Path(__file__).parent.parent
env_path = project_root / '.env'
load_dotenv(env_path)


class Config:
    """Configuration settings for the credit automation bot"""

    # Slack Configuration
    SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
    SLACK_APP_TOKEN = os.getenv('SLACK_APP_TOKEN')
    SLACK_USER_ID = os.getenv('SLACK_USER_ID', 'W014QM1DAPN')  # For DMs
    SLACK_TEST_CHANNEL = os.getenv('SLACK_TEST_CHANNEL', 'credit_memo_testing')
    SLACK_PROD_CHANNEL = os.getenv('SLACK_PROD_CHANNEL', 'help-sms-credit-pumping-memos')

    # Looker Configuration
    LOOKER_CLIENT_ID = os.getenv('LOOKER_CLIENT_ID')
    LOOKER_CLIENT_SECRET = os.getenv('LOOKER_CLIENT_SECRET')
    LOOKER_BASE_URL = os.getenv('LOOKER_BASE_URL', 'https://twiliocloud.cloud.looker.com')

    # Bot Configuration
    BOT_NAME = os.getenv('BOT_NAME', 'CreditBot')

    # Notebook Configuration
    NOTEBOOK_PATH = project_root / os.getenv('NOTEBOOK_PATH', 'Verify - Credit Recommendation.ipynb')
    OUTPUT_DIR = project_root / os.getenv('OUTPUT_DIR', 'data/outputs')
    STATE_FILE = project_root / os.getenv('STATE_FILE', 'data/processed_messages.json')

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = project_root / os.getenv('LOG_FILE', 'logs/credit_bot.log')

    # Ensure directories exist
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate(cls):
        """Validate that required configuration is present"""
        required = {
            'SLACK_BOT_TOKEN': cls.SLACK_BOT_TOKEN,
            'LOOKER_CLIENT_ID': cls.LOOKER_CLIENT_ID,
            'LOOKER_CLIENT_SECRET': cls.LOOKER_CLIENT_SECRET,
        }

        missing = [key for key, value in required.items() if not value]

        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

        return True

    @classmethod
    def get_channel(cls):
        """Get the Slack channel for posting (always test channel)"""
        return cls.SLACK_TEST_CHANNEL


# Validate configuration on import
try:
    Config.validate()
except ValueError as e:
    print(f"⚠️  Configuration Error: {e}")
    print(f"Please copy .env.example to .env and fill in your credentials")
