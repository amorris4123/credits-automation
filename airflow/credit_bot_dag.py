"""
CreditBot Airflow DAG
Automated credit processing for Slack requests

This DAG runs every 15 minutes to check for new credit requests in Slack,
process them through the Jupyter notebook, and post results back to Slack.

Owner: team_accsec-ai
Repository: https://github.com/twilio-internal/credits-automation
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.kubernetes.secret import Secret

# Default arguments for the DAG
default_args = {
    'owner': 'team_accsec-ai',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 14),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(minutes=10),
}

# Define the DAG
dag = DAG(
    'credit_bot_automation',
    default_args=default_args,
    description='Automated SMS toll fraud credit processing bot',
    schedule_interval='*/15 * * * *',  # Every 15 minutes
    catchup=False,  # Don't backfill missed runs
    max_active_runs=1,  # Only one run at a time
    tags=['accsec-ai', 'credit-bot', 'automation'],
)

# Configure AWS Secrets Manager secret
# This will be injected as environment variables into the pod
aws_secret = Secret(
    deploy_type='env',
    deploy_target=None,  # Will use keys from secret as env var names
    secret='accsec-ai-credit-bot-credentials',  # Name in Kubernetes secrets
    key=None,  # Use all keys from the secret
)

# Define the Kubernetes Pod Operator
process_credit_requests = KubernetesPodOperator(
    task_id='process_credit_requests',
    name='credit-bot-{{ ts_nodash | lower }}',  # Pod name with timestamp
    namespace='accsec-ai',  # Kubernetes namespace (adjust as needed)
    image='<ECR_REPOSITORY_URL>/accsec-ai/credit-bot:latest',  # Replace with actual ECR URL
    image_pull_policy='Always',  # Always pull latest image

    # Secrets and environment variables
    secrets=[aws_secret],
    env_vars={
        'AWS_REGION': 'us-east-1',
        'AWS_SECRET_NAME': 'accsec-ai/credit-bot/credentials',
        'S3_BUCKET': 'accsec-ai-credit-bot-state',
        'LOG_LEVEL': 'INFO',
    },

    # Resource limits
    resources={
        'request_memory': '2Gi',
        'request_cpu': '1000m',
        'limit_memory': '4Gi',
        'limit_cpu': '2000m',
    },

    # Pod configuration
    is_delete_operator_pod=True,  # Clean up pod after completion
    get_logs=True,  # Stream logs to Airflow
    log_events_on_failure=True,  # Log events on failure

    # Startup and liveness probes
    startup_timeout_seconds=300,  # 5 minutes to start

    # Service account (needs permissions for Secrets Manager and S3)
    service_account_name='credit-bot-service-account',  # Adjust as needed

    # Affinity and tolerations (optional - adjust based on cluster config)
    # affinity={},
    # tolerations=[],

    dag=dag,
)

# Task dependencies (only one task, but you can add more)
# Example: add a task to send notification on failure
# send_failure_notification >> process_credit_requests

# DAG documentation
dag.doc_md = """
# CreditBot Automation

Automatically processes SMS toll fraud credit requests from Slack.

## What it does:
1. Monitors Slack channel for messages with Looker URLs
2. Extracts SQL queries from Looker API
3. Executes Jupyter notebook to calculate credit amounts
4. Posts results back to Slack thread
5. Tracks processed messages in S3 to avoid duplicates

## Monitoring:
- Check Airflow UI for execution status
- View pod logs for detailed execution trace
- Check S3 bucket for state and outputs:
  - State: `s3://accsec-ai-credit-bot-state/state/processed_messages.json`
  - Outputs: `s3://accsec-ai-credit-bot-state/outputs/`

## On Failure:
1. Check pod logs in Airflow UI
2. Verify AWS credentials are configured
3. Check Slack/Looker connectivity
4. Review recent code changes
5. Contact team_accsec-ai for assistance

## Manual Trigger:
Click the "Play" button in Airflow UI to run immediately.

## Configuration:
- Schedule: Every 15 minutes
- Timeout: 10 minutes
- Retries: 2 with 5-minute delay
- Max concurrent runs: 1

## Links:
- [GitHub Repository](https://github.com/twilio-internal/credits-automation)
- [S3 Bucket](https://s3.console.aws.amazon.com/s3/buckets/accsec-ai-credit-bot-state)
- [ECR Repository](https://console.aws.amazon.com/ecr/repositories/accsec-ai/credit-bot)

"""

# You can add additional tasks here, such as:
# - Pre-execution health checks
# - Post-execution notifications
# - Metric collection
# - Data quality checks

# Example of adding a Slack notification on failure (optional):
# from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator
#
# send_failure_notification = SlackWebhookOperator(
#     task_id='send_failure_notification',
#     http_conn_id='slack_webhook',
#     message='CreditBot execution failed. Check Airflow logs.',
#     channel='#credit-bot-alerts',
#     trigger_rule='one_failed',
#     dag=dag,
# )
#
# process_credit_requests >> send_failure_notification
