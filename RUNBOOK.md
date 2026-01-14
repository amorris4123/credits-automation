# CreditBot Production Runbook

**Operations guide for managing CreditBot in production**

---

## Quick Reference

| Item | Value |
|------|-------|
| **Service Name** | CreditBot |
| **AWS Account** | applied-data-science-prod-twilio |
| **Airflow DAG** | `credit_bot_automation` |
| **Schedule** | Every 15 minutes |
| **Owner Team** | team_accsec-ai |
| **Repository** | https://github.com/twilio-internal/credits-automation |
| **Slack Channel** | #help-sms-credit-pumping-memos (monitored), #accsec-ai (team) |

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Health Checks](#health-checks)
3. [Common Operations](#common-operations)
4. [Incident Response](#incident-response)
5. [Common Issues and Solutions](#common-issues-and-solutions)
6. [Escalation](#escalation)
7. [Maintenance Tasks](#maintenance-tasks)

---

## System Overview

### What CreditBot Does

Automatically processes SMS toll fraud credit requests from Slack:

1. Monitors `#help-sms-credit-pumping-memos` channel every 15 minutes
2. Looks for messages containing Looker dashboard URLs
3. Extracts SQL queries from Looker
4. Executes Jupyter notebook to calculate credit amounts
5. Posts results back to Slack thread
6. Tracks processed messages to avoid duplicates

### Architecture Components

- **Airflow MWAA**: Orchestrates scheduled execution
- **EKS/Kubernetes**: Runs containerized bot
- **ECR**: Stores Docker images
- **Secrets Manager**: Stores credentials (Slack, Looker, Presto)
- **S3**: Stores state and output files
- **CloudWatch**: Logs and metrics

### Normal Behavior

- **Execution Frequency**: Every 15 minutes
- **Execution Duration**: 2-5 minutes (typical)
- **Success Rate**: >95% expected
- **Messages Processed**: 0-5 per run (varies by workload)

---

## Health Checks

### Is the Bot Running?

**Method 1: Airflow UI**

1. Access Airflow UI:
   - AWS Console → MWAA → Open Airflow UI
2. Find `credit_bot_automation` DAG
3. Check indicators:
   - ✅ Green circle = Enabled and scheduled
   - 🟢 Green run = Recent success
   - 🔴 Red run = Recent failure
   - ⏸️ Gray = Paused

**Method 2: Check Recent Executions**

```bash
# View last 10 DAG runs (requires AWS CLI and Airflow API access)
# Or check via Airflow UI: DAG → Grid view
```

**Method 3: Check S3 State File**

```bash
# Check when state was last updated
aws s3api head-object \
    --bucket credit-bot-state-XXXXX \
    --key state/processed_messages.json \
    --query 'LastModified' \
    --output text

# Should be within last 15-20 minutes if bot is healthy
```

**Method 4: Check CloudWatch Logs**

```bash
# Get recent logs
aws logs tail /aws/eks/credit-bot --follow --since 30m

# Look for recent "Bot execution completed" messages
```

### What to Look For

✅ **Healthy Indicators**:
- DAG enabled in Airflow
- Last run successful (green)
- Last run within 15 minutes
- S3 state file updated recently
- No error logs in CloudWatch

🚨 **Unhealthy Indicators**:
- DAG paused or disabled
- Last run failed (red)
- Last run >30 minutes ago
- Repeated errors in logs
- S3 state not updating

---

## Common Operations

### View Recent Logs

**Via Airflow UI**:
1. Airflow UI → DAGs → `credit_bot_automation`
2. Click on recent run (date/time)
3. Click `process_credit_requests` task
4. Click "Log" button
5. Logs display in real-time

**Via CloudWatch**:
```bash
# Tail live logs
aws logs tail /aws/eks/credit-bot --follow

# Get last hour of logs
aws logs tail /aws/eks/credit-bot --since 1h

# Search for errors
aws logs tail /aws/eks/credit-bot --since 1h --filter-pattern "ERROR"
```

### Manually Trigger Execution

**Use Case**: Want to process messages immediately without waiting for schedule

**Steps**:
1. Airflow UI → DAGs → `credit_bot_automation`
2. Click "Play" button (▶️) in top-right
3. Click "Trigger DAG"
4. Confirm
5. Monitor execution in Graph view

### Pause the Bot

**Use Case**: Need to stop bot temporarily (e.g., during incident, maintenance)

**Steps**:
1. Airflow UI → DAGs → `credit_bot_automation`
2. Toggle switch to **OFF** (left side of DAG name)
3. Confirm DAG is paused (gray indicator)

**Resume**: Toggle switch back to **ON**

### Check Processed Messages

```bash
# Download current state
aws s3 cp s3://credit-bot-state-XXXXX/state/processed_messages.json /tmp/state.json

# View processed message count
cat /tmp/state.json | jq '.processed_messages | length'

# View recent messages
cat /tmp/state.json | jq '.processed_messages[-10:]'

# Check specific message
cat /tmp/state.json | jq '.processed_messages[] | select(.message_id=="1234567890.123456")'
```

### View Notebook Outputs

```bash
# List recent outputs
aws s3 ls s3://credit-bot-state-XXXXX/outputs/ --recursive | tail -20

# Download specific output
aws s3 cp s3://credit-bot-state-XXXXX/outputs/summary_20260114_153045.json /tmp/

# View summary
cat /tmp/summary_20260114_153045.json | jq .
```

### Restart a Failed Task

**Use Case**: Task failed due to transient issue, want to retry

**Steps**:
1. Airflow UI → DAGs → `credit_bot_automation`
2. Click on failed run
3. Click on failed task (`process_credit_requests`)
4. Click "Clear" button
5. Confirm - task will retry immediately

### Force Refresh DAG

**Use Case**: Updated DAG code but not reflected in UI

**Steps**:
1. Wait 1-2 minutes for auto-refresh
2. Or refresh browser page
3. Or click "Refresh" button in Airflow UI

### Check Resource Usage

**Via Kubernetes** (if you have access):
```bash
# List pods
kubectl get pods -n <namespace> | grep credit-bot

# Check pod resource usage
kubectl top pod -n <namespace> | grep credit-bot

# Describe pod for events
kubectl describe pod credit-bot-20260114 -n <namespace>
```

**Via CloudWatch**:
- Metrics → Container Insights → EKS → Pods
- Filter by pod name: `credit-bot-*`
- Check: CPU %, Memory %, Network I/O

---

## Incident Response

### Incident Severity Levels

| Severity | Description | Response Time | Example |
|----------|-------------|---------------|---------|
| **P0 - Critical** | Bot down, blocking critical business process | Immediate | Bot hasn't run in 2+ hours, backlog building |
| **P1 - High** | Degraded performance, some failures | 30 minutes | 50% failure rate, some messages not processed |
| **P2 - Medium** | Minor issues, workaround available | 4 hours | Individual message failures, can process manually |
| **P3 - Low** | Cosmetic or non-blocking | Next business day | Logging issues, minor UI problems |

### P0 Incident Response

**Symptoms**: Bot not running for >1 hour, DAG failing repeatedly

**Immediate Actions**:

1. **Acknowledge incident**
   ```bash
   # Post in #accsec-ai Slack
   "🚨 CreditBot is down. Investigating..."
   ```

2. **Check Airflow UI**
   - Is DAG paused? → Enable it
   - Is DAG failing? → Check logs

3. **Check CloudWatch logs**
   ```bash
   aws logs tail /aws/eks/credit-bot --since 2h --filter-pattern "ERROR"
   ```

4. **Quick fixes to try**:
   - Manually trigger DAG run
   - Clear failed task and retry
   - Restart DAG (pause → enable)

5. **If not resolved in 15 minutes**: Escalate (see [Escalation](#escalation))

6. **Workaround**: Process messages manually
   ```bash
   # On local machine with access
   cd /Users/amorris/Documents/credits-automation
   source venv/bin/activate
   python3 run_bot.py
   ```

7. **Update status**
   ```bash
   # Post in Slack every 30 minutes
   "Update: CreditBot still down. Investigating [issue]. Manual processing in place."
   ```

### P1/P2 Incident Response

**Symptoms**: Some failures, degraded performance

**Actions**:

1. **Investigate logs** for error patterns
2. **Check recent changes**: Was DAG or code updated?
3. **Check dependencies**: Are Slack/Looker/Presto accessible?
4. **Try fixes**:
   - Retry failed tasks
   - Rollback recent deployment if suspicious
5. **Document in GitHub issue**
6. **Fix during business hours**

---

## Common Issues and Solutions

### 1. DAG Not Running

**Symptoms**: No recent executions, last run >1 hour ago

**Causes**:
- DAG is paused
- Schedule is disabled
- Airflow scheduler issue

**Solutions**:
```bash
# Check if paused
# Airflow UI → Enable DAG

# Check schedule
# Airflow UI → DAG → Details → Schedule

# Check Airflow scheduler status (platform team)
```

### 2. All Tasks Failing with "ImagePullBackOff"

**Symptoms**: Tasks fail immediately, logs show "ImagePullBackOff"

**Causes**:
- ECR image not found
- ECR permissions missing
- Image tag doesn't exist

**Solutions**:
```bash
# Check if image exists
aws ecr describe-images \
    --repository-name credit-bot \
    --image-ids imageTag=latest

# If not found, rebuild and push
cd /Users/amorris/Documents/credits-automation
./deploy.sh

# Check ECR permissions (platform team)
```

### 3. Tasks Fail with "Secrets Not Found"

**Symptoms**: Logs show "Secret credit-bot/credentials not found" or "Access Denied"

**Causes**:
- Secret doesn't exist
- IAM permissions missing
- Wrong secret name

**Solutions**:
```bash
# Verify secret exists
aws secretsmanager describe-secret --secret-id credit-bot/credentials

# Check IAM policy on service account (platform team)

# Verify secret name in DAG matches Secrets Manager
```

### 4. Tasks Timeout

**Symptoms**: Task runs for 10 minutes then fails with "Timeout"

**Causes**:
- Presto query taking too long
- Network issues
- Notebook execution hung

**Solutions**:
```bash
# Check recent notebook execution times in logs

# Increase timeout in DAG (if justified):
# execution_timeout=timedelta(minutes=15)

# Check Presto query performance
# Optimize SQL if needed

# Check network connectivity to Presto (platform team)
```

### 5. Bot Processes Message Multiple Times

**Symptoms**: Same Slack message gets duplicate responses

**Causes**:
- S3 state file not updating
- State file corrupted
- Race condition (multiple pods running)

**Solutions**:
```bash
# Check S3 state file
aws s3 cp s3://credit-bot-state-XXXXX/state/processed_messages.json /tmp/state.json
cat /tmp/state.json | jq .

# Verify DAG has max_active_runs=1 (should prevent race conditions)

# Check S3 write permissions

# If corrupted, restore from S3 version history
aws s3api list-object-versions --bucket credit-bot-state-XXXXX --prefix state/
```

### 6. Slack Posting Fails

**Symptoms**: Messages processed but no Slack posts, or "Invalid token" errors

**Causes**:
- Slack token expired or revoked
- Bot not in channel
- Missing OAuth scopes

**Solutions**:
```bash
# Verify token in Secrets Manager
aws secretsmanager get-secret-value --secret-id credit-bot/credentials | jq -r '.SecretString' | jq .SLACK_BOT_TOKEN

# Test token manually (from local machine)
python3 -c "
from slack_sdk import WebClient
client = WebClient(token='xoxb-...')
response = client.auth_test()
print(response)
"

# Check bot is in #help-sms-credit-pumping-memos
# Reinvite: @creditbot in channel

# Check OAuth scopes:
# https://api.slack.com/apps/<app-id>/oauth
# Required: channels:history, channels:read, chat:write, im:write
```

### 7. Looker API Errors

**Symptoms**: "Unauthorized" or "Not found" errors from Looker

**Causes**:
- Looker credentials expired
- Look ID invalid
- Looker API down

**Solutions**:
```bash
# Verify Looker credentials
aws secretsmanager get-secret-value --secret-id credit-bot/credentials | jq -r '.SecretString' | jq .LOOKER_CLIENT_ID

# Test Looker API (from local machine)
python3 -c "
from src.looker_client import LookerClient
client = LookerClient('https://twilio.looker.com', 'client_id', 'client_secret')
# ... test connection
"

# Check Looker status page (if exists)

# Verify Look ID is valid (try accessing in browser)
```

### 8. Presto Connection Fails

**Symptoms**: "Unable to connect to Presto" errors

**Causes**:
- Presto credentials wrong/expired
- Network connectivity issue
- Presto service down

**Solutions**:
```bash
# Verify Presto credentials
aws secretsmanager get-secret-value --secret-id credit-bot/credentials | jq -r '.SecretString' | jq .PRESTO_USERNAME

# Check network connectivity from pod (if access)
kubectl exec -it credit-bot-XXXXX -n <namespace> -- ping presto.internal.twilio.com

# Check Presto service status (data team)

# Check if service credentials approval still pending
# → Implement Glue alternative if needed
```

### 9. High Error Rate (Multiple Failures)

**Symptoms**: 20-50% of messages failing to process

**Causes**:
- Invalid SQL queries in Looker
- Notebook code errors
- Data issues in Presto

**Solutions**:
```bash
# Check logs for error patterns
aws logs tail /aws/eks/credit-bot --since 24h --filter-pattern "ERROR"

# Identify common SQL errors
# Fix in Looker or add error handling

# Check notebook execution outputs
aws s3 ls s3://credit-bot-state-XXXXX/outputs/ | tail -20

# May need code fix → Deploy updated version
```

---

## Escalation

### When to Escalate

Escalate if:
- P0 incident not resolved in 15 minutes
- Root cause unclear after 30 minutes investigation
- Requires access you don't have (IAM, networking, etc.)
- Affects other services
- Data loss or corruption suspected

### Escalation Path

1. **Primary Contact**: team_accsec-ai Slack channel `#accsec-ai`
2. **On-Call**: Page via PagerDuty (if configured)
3. **Platform Team**: For EKS, MWAA, networking issues
4. **Data Team**: For Presto, Looker issues
5. **Security Team**: For credential/access issues

### Information to Provide

When escalating, include:

```
**Issue**: CreditBot not processing messages
**Severity**: P0
**Started**: 2026-01-14 15:30 UTC
**Symptoms**: All DAG runs failing with "ImagePullBackOff"
**Impact**: ~15 messages pending, backlog building
**Investigation**:
  - Checked ECR: Image exists
  - Checked IAM: Permissions look correct
  - Attempted: Retry task, rebuild image
  - Logs: [link to CloudWatch logs]
**Next Steps**: Need platform team to check EKS image pull permissions
```

---

## Maintenance Tasks

### Weekly Tasks

**Check bot health**:
- [ ] Verify DAG running on schedule
- [ ] Check success rate >95%
- [ ] Review error logs for patterns
- [ ] Verify S3 state file growing appropriately

**Review metrics**:
```bash
# Count processed messages this week
aws s3 cp s3://credit-bot-state-XXXXX/state/processed_messages.json - | \
  jq '[.processed_messages[] | select(.timestamp > "2026-01-07")] | length'

# Check execution duration trend (via Airflow UI metrics)
```

### Monthly Tasks

**Review resource usage**:
- [ ] Check CloudWatch metrics for CPU/memory trends
- [ ] Adjust resource limits in DAG if needed
- [ ] Review S3 storage usage and costs

**Dependency updates**:
- [ ] Check for Python package updates
- [ ] Update `docker-requirements.txt` if needed
- [ ] Test and deploy updated image

**Documentation review**:
- [ ] Update runbook if processes changed
- [ ] Review and update troubleshooting steps
- [ ] Archive old logs/outputs from S3 (if needed)

### Quarterly Tasks

**Access review**:
- [ ] Review AWS IAM permissions
- [ ] Rotate Slack bot token (if policy requires)
- [ ] Review Looker API credentials
- [ ] Audit who has access to modify DAG

**Disaster recovery test**:
- [ ] Simulate bot failure
- [ ] Test manual processing workflow
- [ ] Verify state file restore from S3 versions
- [ ] Test rollback procedure

**Capacity planning**:
- [ ] Review message volume trends
- [ ] Estimate future resource needs
- [ ] Plan for scaling if needed

---

## Useful Commands Reference

### Airflow/AWS

```bash
# List ECR images
aws ecr list-images --repository-name credit-bot

# Get secret value
aws secretsmanager get-secret-value --secret-id credit-bot/credentials

# List S3 bucket contents
aws s3 ls s3://credit-bot-state-XXXXX/ --recursive

# Tail CloudWatch logs
aws logs tail /aws/eks/credit-bot --follow

# Get pod status (if kubectl access)
kubectl get pods -n <namespace> | grep credit-bot
```

### Local Testing

```bash
# Run bot locally (for manual processing)
cd /Users/amorris/Documents/credits-automation
source venv/bin/activate
python3 run_bot.py

# Deploy new version
./deploy.sh v1.2.0
```

### Debugging

```bash
# Check message in state file
aws s3 cp s3://credit-bot-state-XXXXX/state/processed_messages.json - | \
  jq '.processed_messages[] | select(.message_id=="XXX")'

# Search logs for specific error
aws logs tail /aws/eks/credit-bot --since 24h --filter-pattern "ERROR.*Presto"

# Download notebook output
aws s3 cp s3://credit-bot-state-XXXXX/outputs/summary_TIMESTAMP.json /tmp/
```

---

## Related Documentation

- **Deployment Guide**: [AIRFLOW_DEPLOYMENT.md](AIRFLOW_DEPLOYMENT.md)
- **Local Development**: [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md)
- **Setup Guide**: [SETUP_GUIDE.md](SETUP_GUIDE.md)
- **Repository**: https://github.com/twilio-internal/credits-automation

---

## Contact Information

- **Team Slack**: #accsec-ai
- **Email**: team_accsec-ai@twilio.com
- **GitHub**: https://github.com/twilio-internal/credits-automation/issues
- **On-Call**: [PagerDuty info if configured]

---

**Last Updated**: 2026-01-14
**Maintained By**: team_accsec-ai
**Version**: 1.0
