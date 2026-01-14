"""
AWS Integration Module
Provides utilities for AWS Secrets Manager and S3 operations
"""

import json
import logging
import os
from typing import Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import boto3, but don't fail if not available (for local development)
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.warning("boto3 not available - AWS features disabled")


class AWSIntegration:
    """Handles AWS Secrets Manager and S3 operations"""

    def __init__(self, region_name: str = 'us-east-1'):
        """
        Initialize AWS integration

        Args:
            region_name: AWS region (default: us-east-1 for N. Virginia)
        """
        self.region_name = region_name
        self.secrets_client = None
        self.s3_client = None

        if BOTO3_AVAILABLE:
            try:
                self.secrets_client = boto3.client('secretsmanager', region_name=region_name)
                self.s3_client = boto3.client('s3', region_name=region_name)
                logger.info(f"AWS clients initialized for region {region_name}")
            except Exception as e:
                logger.warning(f"Could not initialize AWS clients: {e}")

    def fetch_secrets(self, secret_name: str) -> Optional[Dict[str, str]]:
        """
        Fetch secrets from AWS Secrets Manager

        Args:
            secret_name: Name of the secret in Secrets Manager

        Returns:
            Dictionary of secrets, or None if not available
        """
        if not self.secrets_client:
            logger.warning("Secrets Manager client not available")
            return None

        try:
            response = self.secrets_client.get_secret_value(SecretId=secret_name)

            # Secrets can be stored as string or binary
            if 'SecretString' in response:
                secret_data = json.loads(response['SecretString'])
                logger.info(f"Successfully fetched secrets from {secret_name}")
                return secret_data
            else:
                logger.error(f"Secret {secret_name} not in expected format")
                return None

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                logger.error(f"Secret {secret_name} not found")
            elif error_code == 'AccessDeniedException':
                logger.error(f"Access denied to secret {secret_name}")
            else:
                logger.error(f"Error fetching secret {secret_name}: {e}")
            return None
        except NoCredentialsError:
            logger.error("AWS credentials not configured")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching secrets: {e}")
            return None

    def read_from_s3(self, bucket: str, key: str) -> Optional[str]:
        """
        Read a file from S3

        Args:
            bucket: S3 bucket name
            key: S3 object key (path)

        Returns:
            File contents as string, or None if not available
        """
        if not self.s3_client:
            logger.warning("S3 client not available")
            return None

        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read().decode('utf-8')
            logger.info(f"Successfully read s3://{bucket}/{key}")
            return content
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.warning(f"File not found in S3: s3://{bucket}/{key}")
            else:
                logger.error(f"Error reading from S3: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error reading from S3: {e}")
            return None

    def write_to_s3(self, bucket: str, key: str, content: str, content_type: str = 'text/plain') -> bool:
        """
        Write a file to S3

        Args:
            bucket: S3 bucket name
            key: S3 object key (path)
            content: Content to write
            content_type: MIME type of content

        Returns:
            True if successful, False otherwise
        """
        if not self.s3_client:
            logger.warning("S3 client not available")
            return False

        try:
            self.s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=content.encode('utf-8'),
                ContentType=content_type
            )
            logger.info(f"Successfully wrote s3://{bucket}/{key}")
            return True
        except ClientError as e:
            logger.error(f"Error writing to S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error writing to S3: {e}")
            return False

    def upload_file_to_s3(self, bucket: str, key: str, file_path: Path) -> bool:
        """
        Upload a local file to S3

        Args:
            bucket: S3 bucket name
            key: S3 object key (path)
            file_path: Local file path to upload

        Returns:
            True if successful, False otherwise
        """
        if not self.s3_client:
            logger.warning("S3 client not available")
            return False

        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False

        try:
            self.s3_client.upload_file(str(file_path), bucket, key)
            logger.info(f"Successfully uploaded {file_path} to s3://{bucket}/{key}")
            return True
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uploading to S3: {e}")
            return False

    def download_file_from_s3(self, bucket: str, key: str, file_path: Path) -> bool:
        """
        Download a file from S3 to local filesystem

        Args:
            bucket: S3 bucket name
            key: S3 object key (path)
            file_path: Local file path to save to

        Returns:
            True if successful, False otherwise
        """
        if not self.s3_client:
            logger.warning("S3 client not available")
            return False

        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            self.s3_client.download_file(bucket, key, str(file_path))
            logger.info(f"Successfully downloaded s3://{bucket}/{key} to {file_path}")
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.warning(f"File not found in S3: s3://{bucket}/{key}")
            else:
                logger.error(f"Error downloading from S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading from S3: {e}")
            return False

    def file_exists_in_s3(self, bucket: str, key: str) -> bool:
        """
        Check if a file exists in S3

        Args:
            bucket: S3 bucket name
            key: S3 object key (path)

        Returns:
            True if file exists, False otherwise
        """
        if not self.s3_client:
            return False

        try:
            self.s3_client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                return False
            logger.error(f"Error checking S3 file existence: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking S3: {e}")
            return False


def is_running_in_airflow() -> bool:
    """
    Detect if code is running in Airflow environment

    Returns:
        True if running in Airflow, False otherwise
    """
    # Check for Airflow-specific environment variables
    airflow_vars = ['AIRFLOW_HOME', 'AIRFLOW__CORE__DAGS_FOLDER', 'AIRFLOW_CTX_DAG_ID']
    return any(os.getenv(var) for var in airflow_vars)


def is_running_in_kubernetes() -> bool:
    """
    Detect if code is running in Kubernetes pod

    Returns:
        True if running in K8s, False otherwise
    """
    # Check for Kubernetes-specific environment variables
    k8s_vars = ['KUBERNETES_SERVICE_HOST', 'KUBERNETES_PORT']
    return all(os.getenv(var) for var in k8s_vars)


def get_execution_environment() -> str:
    """
    Get the current execution environment

    Returns:
        String describing environment: 'airflow', 'kubernetes', 'docker', or 'local'
    """
    if is_running_in_airflow():
        return 'airflow'
    elif is_running_in_kubernetes():
        return 'kubernetes'
    elif os.path.exists('/.dockerenv'):
        return 'docker'
    else:
        return 'local'


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    aws = AWSIntegration()
    env = get_execution_environment()
    print(f"Execution environment: {env}")

    # Test secrets fetch (will fail gracefully if not configured)
    secrets = aws.fetch_secrets('accsec-ai/credit-bot/credentials')
    if secrets:
        print(f"Fetched {len(secrets)} secrets")
    else:
        print("Could not fetch secrets (expected in local environment)")
