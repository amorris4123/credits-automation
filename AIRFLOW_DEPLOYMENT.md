# CreditBot Airflow Deployment Guide

**Production deployment guide for CreditBot on Twilio's MWAA (Managed Airflow) infrastructure**

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Architecture](#architecture)
4. [Initial Setup](#initial-setup)
5. [Building and Deploying](#building-and-deploying)
6. [Monitoring and Operations](#monitoring-and-operations)
7. [Troubleshooting](#troubleshooting)
8. [Updating the Bot](#updating-the-bot)
9. [Rollback Procedures](#rollback-procedures)

---

## Overview

CreditBot runs as a scheduled Airflow DAG in the `applied-data-science-prod-twilio` AWS account. The bot is containerized and runs every 15 minutes on Kubernetes via Airflow's KubernetesPodOperator.

### Key Information

- **AWS Account**: `applied-data-science-prod-twilio`
- **Airflow Environment**: MWAA (verify environment name with data science team)
- **Schedule**: Every 15 minutes (`*/15 * * * *`)
- **DAG Name**: `credit_bot_automation`
- **Execution Time**: ~2-5 minutes per run
- **Resources**: 2Gi memory, 1 CPU (request), 4Gi memory, 2 CPU (limit)

---

## Prerequisites

### Required Access

Before deploying, ensure you have:

- ✅ **TBAC Access**: Member of proper TBAC group for `applied-data-science-prod-twilio`
- ✅ **AWS Console**: Can access AWS console for the account
- ✅ **Yubikey**: Configured for MFA
- ✅ **VPN**: OnCall VPN access (if required for deployment)
- ⏳ **Presto Credentials**: Service account approval pending (see [Presto Access](#presto-access-strategy))
- 📝 **GitHub**: Write access to `airflow-dags` repository
- 📝 **ECR**: Push permissions to ECR registry

### Required Tools

Local development machine needs:

```bash
# Check if tools are installed
docker --version        # Docker 20.10+
aws --version          # AWS CLI v2
git --version          # Git 2.x+
```

If not installed:
- **Docker Desktop**: https://www.docker.com/products/docker-desktop
- **AWS CLI**: `brew install awscli` (macOS) or https://aws.amazon.com/cli/
- **Git**: `brew install git` (macOS) or https://git-scm.com/

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Airflow MWAA (applied-data-science-prod-twilio)            │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ DAG: credit_bot_automation (every 15 min)            │   │
│  │                                                        │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ KubernetesPodOperator                          │  │   │
│  │  │   - Pulls image from ECR                       │  │   │
│  │  │   - Creates pod in K8s namespace               │  │   │
│  │  │   - Injects secrets from Secrets Manager       │  │   │
│  │  │   - Runs: python3 run_bot.py                   │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
    ┌──────────────────────────────────────────────┐
    │         Kubernetes (EKS Cluster)              │
    │                                                │
    │  Pod: credit-bot-20260114t1530                │
    │  ┌──────────────────────────────────────┐    │
    │  │ Container: credit-bot:latest         │    │
    │  │                                       │    │
    │  │ 1. Read state from S3                │    │
    │  │ 2. Check Slack for new messages      │────┼──→ Slack API
    │  │ 3. Extract Looker URL                │    │
    │  │ 4. Fetch SQL from Looker API         │────┼──→ Looker API
    │  │ 5. Execute Jupyter notebook          │    │
    │  │    - Query Presto for billing data   │────┼──→ Presto
    │  │    - Calculate credit amount          │    │
    │  │ 6. Post result to Slack thread       │────┼──→ Slack API
    │  │ 7. Update state in S3                │    │
    │  └──────────────────────────────────────┘    │
    └──────────────────────────────────────────────┘
                            │
                            ↓
    ┌──────────────────────────────────────────────┐
    │         AWS Resources                         │
    │                                                │
    │  • ECR: Docker image registry                │
    │  • Secrets Manager: Credentials storage      │
    │  • S3: State and outputs storage             │
    │  • CloudWatch: Logs and metrics              │
    └──────────────────────────────────────────────┘
```

### Data Flow

1. **Airflow Scheduler** triggers DAG every 15 minutes
2. **KubernetesPodOperator** creates a new pod in EKS
3. **Pod** pulls Docker image from ECR
4. **Secrets** are injected as environment variables
5. **Application** runs and checks Slack for new messages
6. **State** is persisted to S3 to track processed messages
7. **Logs** are streamed to CloudWatch and Airflow UI
8. **Pod** is deleted after execution completes

---

## Initial Setup

### Step 1: Coordinate with Data Science Team

Before creating resources, verify naming conventions:

```bash
# Contact data science team to confirm:
# - ECR repository naming pattern
# - S3 bucket naming pattern
# - Secrets Manager path conventions
# - Kubernetes namespace
# - Service account name
```

### Step 2: Create AWS Resources

#### 2.1 Create ECR Repository

```bash
# Set your AWS account ID
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION="us-east-1"
export ECR_REPO="credit-bot"  # Adjust per team conventions

# Create ECR repository
aws ecr create-repository \
    --repository-name $ECR_REPO \
    --region $AWS_REGION \
    --image-scanning-configuration scanOnPush=true

# Set lifecycle policy (keep last 10 images)
cat > /tmp/lifecycle-policy.json <<EOF
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Keep last 10 images",
      "selection": {
        "tagStatus": "any",
        "countType": "imageCountMoreThan",
        "countNumber": 10
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}
EOF

aws ecr put-lifecycle-policy \
    --repository-name $ECR_REPO \
    --lifecycle-policy-text file:///tmp/lifecycle-policy.json
```

#### 2.2 Create S3 Bucket

```bash
# Set bucket name (must be globally unique)
export S3_BUCKET="credit-bot-state-$(date +%s)"  # Adds timestamp for uniqueness

# Create bucket
aws s3 mb s3://$S3_BUCKET --region $AWS_REGION

# Enable versioning
aws s3api put-bucket-versioning \
    --bucket $S3_BUCKET \
    --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
    --bucket $S3_BUCKET \
    --server-side-encryption-configuration '{
      "Rules": [{
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "AES256"
        }
      }]
    }'

# Set lifecycle policy (delete outputs after 90 days)
cat > /tmp/s3-lifecycle.json <<EOF
{
  "Rules": [
    {
      "Id": "DeleteOldOutputs",
      "Status": "Enabled",
      "Prefix": "outputs/",
      "Expiration": {
        "Days": 90
      }
    }
  ]
}
EOF

aws s3api put-bucket-lifecycle-configuration \
    --bucket $S3_BUCKET \
    --lifecycle-configuration file:///tmp/s3-lifecycle.json

echo "S3 Bucket created: s3://$S3_BUCKET"
echo "Remember to update src/config.py with this bucket name!"
```

#### 2.3 Store Secrets in AWS Secrets Manager

```bash
# Prepare credentials JSON
# Replace with your actual credentials
cat > /tmp/credentials.json <<EOF
{
  "SLACK_BOT_TOKEN": "xoxb-your-slack-bot-token",
  "SLACK_USER_ID": "U01234567",
  "LOOKER_CLIENT_ID": "your-looker-client-id",
  "LOOKER_CLIENT_SECRET": "your-looker-client-secret",
  "PRESTO_HOST": "presto.internal.twilio.com",
  "PRESTO_PORT": "8080",
  "PRESTO_USERNAME": "service-account-username",
  "PRESTO_PASSWORD": "service-account-password"
}
EOF

# Create secret
aws secretsmanager create-secret \
    --name "credit-bot/credentials" \
    --description "CreditBot credentials for Slack, Looker, and Presto" \
    --secret-string file:///tmp/credentials.json

# Clean up local file (contains sensitive data)
rm /tmp/credentials.json

echo "✅ Secrets stored in AWS Secrets Manager"
echo "Secret ARN: arn:aws:secretsmanager:$AWS_REGION:$AWS_ACCOUNT_ID:secret:credit-bot/credentials"
```

#### 2.4 Configure IAM Role for Kubernetes Service Account

**Note**: This step typically requires coordination with the platform team. The EKS service account needs permissions for:

- **Secrets Manager**: `secretsmanager:GetSecretValue` on `credit-bot/credentials`
- **S3**: `s3:GetObject`, `s3:PutObject` on the state bucket
- **CloudWatch Logs**: `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

Example IAM policy document:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:credit-bot/credentials*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::credit-bot-state-*",
        "arn:aws:s3:::credit-bot-state-*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:ACCOUNT_ID:log-group:/aws/eks/credit-bot*"
    }
  ]
}
```

### Step 3: Update Configuration Files

Update `src/config.py` with your resource names:

```python
# Update these values in src/config.py
AWS_SECRET_NAME = 'credit-bot/credentials'
S3_BUCKET = 'credit-bot-state-1234567890'  # Your actual bucket name
S3_STATE_KEY = 'state/processed_messages.json'
S3_OUTPUT_PREFIX = 'outputs'
```

### Step 4: Upload Initial State (if migrating)

If you have an existing `processed_messages.json` from local testing:

```bash
# Upload existing state to S3
aws s3 cp data/processed_messages.json s3://$S3_BUCKET/state/processed_messages.json

# Verify upload
aws s3 ls s3://$S3_BUCKET/state/
```

---

## Building and Deploying

### Step 1: Build Docker Image

```bash
# Navigate to project directory
cd /Users/amorris/Documents/credits-automation

# Build image
docker build -t credit-bot:latest .

# Test locally (optional - requires .env file)
docker run --rm --env-file .env credit-bot:latest
```

### Step 2: Push to ECR

Use the provided deployment script:

```bash
# Make script executable
chmod +x deploy.sh

# Set environment variable (if not set)
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Deploy latest version
./deploy.sh

# Or deploy with specific version tag
./deploy.sh v1.0.0
```

The script will:
1. Check prerequisites (Docker, AWS CLI)
2. Authenticate with ECR
3. Build the Docker image
4. Tag for ECR
5. Push to registry

Expected output:
```
===========================================
CreditBot Deployment Script
===========================================

[INFO] Checking prerequisites...
[INFO] Prerequisites check passed ✓
[INFO] AWS Account ID: 123456789012
[INFO] AWS Region: us-east-1
[INFO] Authenticating with ECR...
[INFO] ECR authentication successful ✓
[INFO] Building Docker image...
[INFO] Docker build successful ✓
[INFO] Tagging image for ECR...
[INFO] Pushing image to ECR...
[INFO] Pushed: 123456789012.dkr.ecr.us-east-1.amazonaws.com/credit-bot:latest ✓
===========================================
[INFO] Deployment Complete! ✓
===========================================
```

### Step 3: Update Airflow DAG

Update the image URL in `airflow/credit_bot_dag.py`:

```python
# Line 54 in airflow/credit_bot_dag.py
image='123456789012.dkr.ecr.us-east-1.amazonaws.com/credit-bot:latest',
```

Also verify:
- **namespace**: Correct Kubernetes namespace
- **service_account_name**: Correct service account with IAM permissions
- **env_vars**: S3_BUCKET matches your created bucket

### Step 4: Deploy DAG to Airflow

```bash
# Clone airflow-dags repository
git clone git@github.com:twilio-internal/airflow-dags.git
cd airflow-dags

# Checkout main branch (verify branch name with team)
git checkout mwaa_main

# Create directory for credit bot
mkdir -p dags/credit_bot

# Copy DAG file
cp /Users/amorris/Documents/credits-automation/airflow/credit_bot_dag.py dags/credit_bot/

# Create feature branch
git checkout -b credit-bot-deployment

# Commit changes
git add dags/credit_bot/credit_bot_dag.py
git commit -m "Add CreditBot automation DAG

- Monitors #help-sms-credit-pumping-memos for credit requests
- Runs every 15 minutes via KubernetesPodOperator
- Processes Looker URLs and posts credit amounts
- Stores state in S3 for persistence

Owner: team_accsec-ai
Repo: https://github.com/twilio-internal/credits-automation"

# Push to GitHub
git push origin credit-bot-deployment
```

### Step 5: Create Pull Request

1. Go to https://github.com/twilio-internal/airflow-dags
2. Create pull request from `credit-bot-deployment` to `mwaa_main`
3. Fill in PR description:
   ```markdown
   ## CreditBot Automation DAG

   Deploys automated credit processing bot to Airflow.

   ### What does this do?
   - Monitors Slack channel for credit request messages
   - Extracts SQL from Looker dashboards
   - Calculates credit amounts via Jupyter notebook
   - Posts results back to Slack

   ### Schedule
   - Runs every 15 minutes
   - Max execution time: 10 minutes
   - Retries: 2 with 5-minute delay

   ### Resources
   - Docker image: ECR `credit-bot:latest`
   - Kubernetes namespace: [verify with team]
   - Service account: credit-bot-service-account
   - Memory: 2Gi request, 4Gi limit
   - CPU: 1 core request, 2 core limit

   ### Testing
   - [ ] Locally tested Docker image
   - [ ] Verified IAM permissions
   - [ ] Tested with sample Slack messages

   ### Links
   - Repository: https://github.com/twilio-internal/credits-automation
   - Documentation: See AIRFLOW_DEPLOYMENT.md
   ```

4. Request review from team_accsec-ai or data science team
5. Address any feedback
6. Merge when approved

### Step 6: Verify Deployment

After PR is merged:

1. **Access Airflow UI**
   - Log in to AWS Console for `applied-data-science-prod-twilio`
   - Navigate to MWAA service
   - Click "Open Airflow UI"

2. **Find DAG**
   - Search for `credit_bot_automation`
   - Should appear in DAG list (may take 1-2 minutes)
   - Check that DAG is parseable (no red error indicators)

3. **Initial Test Run**
   - **Pause the DAG first** (toggle switch to OFF)
   - Click on DAG name → Graph view
   - Click "Play" button → Trigger DAG
   - Monitor execution in real-time
   - Check logs by clicking on task → View Logs

4. **Verify Success**
   - Task should turn green (success) or red (failed)
   - Check CloudWatch logs for detailed output
   - Verify S3 state file was updated
   - Check Slack channel for posted messages (if any were processed)

5. **Enable Schedule**
   - Once manual test succeeds, enable the DAG (toggle to ON)
   - Bot will now run automatically every 15 minutes

---

## Presto Access Strategy

⚠️ **Critical**: The bot requires access to Presto database for querying billing data.

### Current Status

Service credentials approval is **pending**. Two paths forward:

#### Path A: Direct Presto Access (Preferred)

- **Status**: Awaiting service account credentials
- **Implementation**: No code changes needed; works with current notebook
- **Timeline**: Ready to deploy once credentials available

#### Path B: AWS Glue Alternative (Fallback)

If Presto credentials are not approved:

1. Create AWS Glue connection to Presto
2. Modify notebook to read query results from S3
3. Update DAG to trigger Glue job before notebook
4. Additional development time: 1-2 days

See the [project plan](/.claude/plans/curried-launching-octopus.md) for detailed Glue migration steps.

---

## Monitoring and Operations

### Accessing Logs

**Airflow UI**:
1. Open Airflow UI (see Step 6 above)
2. Click on `credit_bot_automation` DAG
3. Click on a specific DAG run
4. Click on `process_credit_requests` task
5. Click "Log" button

**CloudWatch**:
1. AWS Console → CloudWatch → Log Groups
2. Find log group: `/aws/eks/credit-bot/...`
3. Filter by pod name or timestamp

**kubectl** (if you have cluster access):
```bash
# List recent pods
kubectl get pods -n <namespace> | grep credit-bot

# View logs
kubectl logs credit-bot-20260114t1530 -n <namespace>
```

### Key Metrics to Monitor

- **Execution Duration**: Should be 2-5 minutes
- **Success Rate**: Should be >95%
- **Messages Processed**: Track via S3 state file
- **Error Rate**: Monitor for repeated failures

### Setting Up Alerts

**Airflow SLA**:

Already configured in DAG (`execution_timeout: 10 minutes`). If exceeded, Airflow will:
- Mark task as failed
- Send email notifications (if configured)
- Trigger retries

**CloudWatch Alarms**:

```bash
# Create alarm for failed executions
aws cloudwatch put-metric-alarm \
    --alarm-name credit-bot-failures \
    --alarm-description "Alert on CreditBot failures" \
    --metric-name ExecutionsFailed \
    --namespace AWS/States \
    --statistic Sum \
    --period 900 \
    --evaluation-periods 1 \
    --threshold 2 \
    --comparison-operator GreaterThanThreshold
```

### Checking Bot Status

**Is the bot running?**

```bash
# Check recent DAG runs via AWS CLI (requires Airflow API access)
# Or check via Airflow UI

# Check S3 state file for last update time
aws s3api head-object --bucket $S3_BUCKET --key state/processed_messages.json

# Check recent CloudWatch logs
aws logs tail /aws/eks/credit-bot --follow
```

---

## Troubleshooting

### Common Issues

#### 1. DAG Not Appearing in Airflow UI

**Symptoms**: `credit_bot_automation` not in DAG list

**Causes**:
- PR not merged yet
- Syntax error in DAG file
- DAG folder not synced to Airflow

**Solutions**:
```bash
# Check DAG parsing errors in Airflow UI
# Browse → Admin → Airflow Configurations → Check for errors

# Verify file in correct location
# dags/credit_bot/credit_bot_dag.py

# Check Airflow logs for import errors
```

#### 2. Pod Fails to Start

**Symptoms**: Task fails immediately with "ImagePullBackOff" or "CrashLoopBackOff"

**Causes**:
- ECR image not found
- Image pull permissions missing
- Container crashes on startup

**Solutions**:
```bash
# Verify image exists
aws ecr describe-images --repository-name credit-bot

# Check ECR permissions for service account
# Contact platform team to verify IRSA configuration

# Test image locally
docker run --rm credit-bot:latest python3 -c "import sys; print('OK')"
```

#### 3. Secrets Not Found

**Symptoms**: Error in logs: "Secret credit-bot/credentials not found"

**Causes**:
- Secret not created in Secrets Manager
- IAM permissions missing
- Wrong secret name in config

**Solutions**:
```bash
# Verify secret exists
aws secretsmanager describe-secret --secret-id credit-bot/credentials

# Check IAM policy on service account
# Ensure GetSecretValue permission

# Verify secret name in src/config.py matches
```

#### 4. S3 Access Denied

**Symptoms**: "Access Denied" errors when reading/writing S3

**Causes**:
- S3 permissions missing
- Wrong bucket name
- Bucket not in same region

**Solutions**:
```bash
# Verify bucket exists
aws s3 ls s3://$S3_BUCKET/

# Check service account IAM policy for S3 permissions

# Verify bucket name in src/config.py matches
```

#### 5. Presto Connection Fails

**Symptoms**: "Unable to connect to Presto" or query timeout

**Causes**:
- Presto credentials not approved yet
- Network connectivity issue
- Presto host unreachable from EKS

**Solutions**:
```bash
# Verify credentials in Secrets Manager
aws secretsmanager get-secret-value --secret-id credit-bot/credentials

# Test network connectivity from pod (if you have access)
kubectl exec -it credit-bot-XXX -n <namespace> -- ping presto.internal.twilio.com

# Check with platform team on network policies/security groups

# If credentials not approved, consider Glue alternative (see plan)
```

#### 6. Notebook Execution Fails

**Symptoms**: Papermill errors in logs

**Causes**:
- SQL query failed
- Notebook code error
- Missing Python dependencies

**Solutions**:
```bash
# Check notebook output in S3
aws s3 ls s3://$S3_BUCKET/outputs/

# Test notebook locally
papermill "Verify - Credit Recommendation.ipynb" /tmp/output.ipynb \
    -p sql_query "SELECT 1"

# Check for missing dependencies in docker-requirements.txt
```

#### 7. Slack Posting Fails

**Symptoms**: Bot processes messages but doesn't post to Slack

**Causes**:
- Invalid Slack token
- Missing OAuth scopes
- Bot not in channel

**Solutions**:
```bash
# Verify Slack token in Secrets Manager
aws secretsmanager get-secret-value --secret-id credit-bot/credentials | jq -r '.SecretString' | jq .SLACK_BOT_TOKEN

# Check token scopes at https://api.slack.com/apps/<app-id>/oauth

# Ensure bot is invited to #help-sms-credit-pumping-memos channel
```

### Getting Help

1. **Check Logs**: Always start with CloudWatch/Airflow logs
2. **Review Documentation**: See README.md and RUNBOOK.md
3. **Search Issues**: Check GitHub issues for similar problems
4. **Contact Team**: Reach out to team_accsec-ai or data science team
5. **Escalate**: If production impacting, page on-call

---

## Updating the Bot

### Deploying Code Changes

1. **Make code changes** in your local repo
2. **Test locally**:
   ```bash
   python3 run_bot.py  # With .env file
   docker build -t credit-bot:test .
   docker run --rm --env-file .env credit-bot:test
   ```
3. **Build and push new image**:
   ```bash
   ./deploy.sh v1.1.0  # New version tag
   ```
4. **Update DAG** (if image tag changed):
   - Update `image=` line in `airflow/credit_bot_dag.py`
   - Submit PR to airflow-dags repo
5. **Test in production**:
   - Pause DAG
   - Trigger manual run
   - Verify success
   - Enable DAG

### Updating the DAG

Changes to schedule, resources, or configuration:

1. **Edit** `airflow/credit_bot_dag.py` locally
2. **Test syntax**:
   ```bash
   python3 airflow/credit_bot_dag.py  # Should run without errors
   ```
3. **Submit PR** to airflow-dags repo
4. **Monitor** after merge for parsing errors

### Changing Credentials

To rotate Slack token, Looker credentials, or Presto password:

```bash
# Update secret in Secrets Manager
aws secretsmanager update-secret \
    --secret-id credit-bot/credentials \
    --secret-string '{"SLACK_BOT_TOKEN": "xoxb-new-token", ...}'

# No need to redeploy - changes take effect on next pod startup
```

---

## Rollback Procedures

### Rolling Back Docker Image

If new version has issues:

```bash
# List recent images
aws ecr describe-images \
    --repository-name credit-bot \
    --query 'sort_by(imageDetails,& imagePushedAt)[*].[imageTags[0],imagePushedAt]' \
    --output table

# Update DAG to previous version
# In airflow/credit_bot_dag.py, change:
image='123456789012.dkr.ecr.us-east-1.amazonaws.com/credit-bot:v1.0.0',  # Previous version

# Submit PR with rollback
# Or manually edit in Airflow UI (Admin → DAGs → Edit → Code)
```

### Rolling Back DAG Changes

```bash
# Revert PR in airflow-dags repo
cd airflow-dags
git revert <commit-hash>
git push origin mwaa_main
```

### Emergency: Pause the Bot

If critical issue discovered:

1. **Pause DAG immediately**: Airflow UI → Toggle DAG to OFF
2. **Investigate**: Check logs, identify root cause
3. **Fix**: Deploy hotfix or rollback
4. **Test**: Manual trigger to verify fix
5. **Resume**: Enable DAG schedule

### Fallback: Manual Execution

If Airflow is down or bot is broken:

```bash
# Run locally as stopgap measure
cd /Users/amorris/Documents/credits-automation
source venv/bin/activate
python3 run_bot.py
```

---

## Additional Resources

- **GitHub Repository**: https://github.com/twilio-internal/credits-automation
- **Airflow DAGs Repo**: https://github.com/twilio-internal/airflow-dags
- **Local Development Guide**: [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md)
- **Operations Runbook**: [RUNBOOK.md](RUNBOOK.md)
- **Project Plan**: [/.claude/plans/curried-launching-octopus.md](/.claude/plans/curried-launching-octopus.md)
- **Security Brief**: [SECURITY_APPROVAL_BRIEF.md](SECURITY_APPROVAL_BRIEF.md)

---

## Support

For issues or questions:

- **Team**: team_accsec-ai
- **Repository Issues**: https://github.com/twilio-internal/credits-automation/issues
- **Slack**: #accsec-ai or #help-data-science
- **On-Call**: Page via PagerDuty if production impacting

---

**Last Updated**: 2026-01-14
**Version**: 1.0
**Status**: Production Ready (pending Presto credentials)
