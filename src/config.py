"""
Configuration management for Credits Automation Bot
Loads settings from environment variables, .env file, or AWS Secrets Manager
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Import AWS integration (will handle cases where boto3 isn't available)
try:
    from .aws_integration import AWSIntegration, get_execution_environment
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False

# Load .env file from project root (for local development)
project_root = Path(__file__).parent.parent
env_path = project_root / '.env'
load_dotenv(env_path)

logger = logging.getLogger(__name__)


class Config:
    """Configuration settings for the credit automation bot"""

    # Detect execution environment
    EXECUTION_ENV = get_execution_environment() if AWS_AVAILABLE else 'local'
    IS_PRODUCTION = EXECUTION_ENV in ['airflow', 'kubernetes']

    # AWS Configuration
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    AWS_SECRET_NAME = os.getenv('AWS_SECRET_NAME', 'accsec-ai/credit-bot/credentials')
    S3_BUCKET = os.getenv('S3_BUCKET', 'accsec-ai-credit-bot-state')
    S3_STATE_KEY = os.getenv('S3_STATE_KEY', 'state/processed_messages.json')
    S3_OUTPUT_PREFIX = os.getenv('S3_OUTPUT_PREFIX', 'outputs')

    # Initialize AWS integration if in production
    _aws = None
    _secrets_cache = None

    @classmethod
    def _get_aws_client(cls):
        """Get or create AWS integration client"""
        if not AWS_AVAILABLE:
            return None
        if cls._aws is None:
            cls._aws = AWSIntegration(region_name=cls.AWS_REGION)
        return cls._aws

    @classmethod
    def _fetch_aws_secrets(cls):
        """Fetch secrets from AWS Secrets Manager (cached)"""
        if cls._secrets_cache is not None:
            return cls._secrets_cache

        aws = cls._get_aws_client()
        if aws is None:
            logger.warning("AWS not available, using environment variables")
            return {}

        secrets = aws.fetch_secrets(cls.AWS_SECRET_NAME)
        if secrets:
            logger.info("Successfully loaded secrets from AWS Secrets Manager")
            cls._secrets_cache = secrets
            return secrets
        else:
            logger.warning("Could not fetch secrets from AWS, falling back to environment variables")
            return {}

    @classmethod
    def _get_config_value(cls, key: str, default=None):
        """
        Get configuration value with priority:
        1. Environment variable (always checked first)
        2. AWS Secrets Manager (if in production)
        3. Default value
        """
        # Check environment variable first
        env_value = os.getenv(key)
        if env_value is not None:
            return env_value

        # Check AWS Secrets Manager if in production
        if cls.IS_PRODUCTION:
            secrets = cls._fetch_aws_secrets()
            if key in secrets:
                return secrets[key]

        # Return default
        return default

    # Slack Configuration
    SLACK_BOT_TOKEN = property(lambda self: Config._get_config_value('SLACK_BOT_TOKEN'))
    SLACK_APP_TOKEN = property(lambda self: Config._get_config_value('SLACK_APP_TOKEN'))
    SLACK_USER_ID = property(lambda self: Config._get_config_value('SLACK_USER_ID', 'W014QM1DAPN'))
    SLACK_TEST_CHANNEL = property(lambda self: Config._get_config_value('SLACK_TEST_CHANNEL', 'credit_memo_testing'))
    SLACK_PROD_CHANNEL = property(lambda self: Config._get_config_value('SLACK_PROD_CHANNEL', 'help-sms-credit-pumping-memos'))

    # Looker Configuration
    LOOKER_CLIENT_ID = property(lambda self: Config._get_config_value('LOOKER_CLIENT_ID'))
    LOOKER_CLIENT_SECRET = property(lambda self: Config._get_config_value('LOOKER_CLIENT_SECRET'))
    LOOKER_BASE_URL = property(lambda self: Config._get_config_value('LOOKER_BASE_URL', 'https://twiliocloud.cloud.looker.com'))

    # Presto Configuration (from AWS Secrets Manager in production)
    PRESTO_HOST = property(lambda self: Config._get_config_value('PRESTO_HOST'))
    PRESTO_PORT = property(lambda self: Config._get_config_value('PRESTO_PORT'))
    PRESTO_USERNAME = property(lambda self: Config._get_config_value('PRESTO_USERNAME'))
    PRESTO_PASSWORD = property(lambda self: Config._get_config_value('PRESTO_PASSWORD'))

    # Bot Configuration
    BOT_NAME = os.getenv('BOT_NAME', 'CreditBot')

    # Notebook Configuration
    NOTEBOOK_PATH = project_root / os.getenv('NOTEBOOK_PATH', 'Verify - Credit Recommendation.ipynb')
    OUTPUT_DIR = project_root / os.getenv('OUTPUT_DIR', 'data/outputs')
    STATE_FILE = project_root / os.getenv('STATE_FILE', 'data/processed_messages.json')

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = project_root / os.getenv('LOG_FILE', 'logs/credit_bot.log')

    # Storage backend (S3 in production, local files in development)
    USE_S3_STORAGE = IS_PRODUCTION and AWS_AVAILABLE

    # Ensure directories exist (for local development and container temp storage)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate(cls):
        """Validate that required configuration is present"""
        # Create temp instance to access properties
        instance = cls()

        required = {
            'SLACK_BOT_TOKEN': instance.SLACK_BOT_TOKEN,
            'LOOKER_CLIENT_ID': instance.LOOKER_CLIENT_ID,
            'LOOKER_CLIENT_SECRET': instance.LOOKER_CLIENT_SECRET,
        }

        missing = [key for key, value in required.items() if not value]

        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

        logger.info(f"Configuration validated successfully (environment: {cls.EXECUTION_ENV})")
        return True

    @classmethod
    def get_channel(cls):
        """Get the Slack channel for posting (always test channel)"""
        instance = cls()
        return instance.SLACK_TEST_CHANNEL

    @classmethod
    def get_aws_client(cls):
        """Get AWS integration client (public method)"""
        return cls._get_aws_client()


# Validate configuration on import (only log warnings, don't fail)
try:
    Config.validate()
except ValueError as e:
    logger.warning(f"Configuration validation failed: {e}")
    if Config.EXECUTION_ENV == 'local':
        print(f"⚠️  Configuration Error: {e}")
        print(f"Please copy .env.example to .env and fill in your credentials")
except Exception as e:
    logger.warning(f"Configuration error: {e}")
