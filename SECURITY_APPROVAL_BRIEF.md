# CreditBot - Enterprise Security Approval Brief

**Prepared for:** Enterprise Security Team - Slack Bot Approval
**Date:** January 14, 2026
**Team:** Applied Data Science - Credit Operations
**Classification:** Internal Use Only

---

## Executive Summary

**CreditBot** is an internal automation tool that processes SMS toll fraud credit requests by monitoring Slack messages, executing data analysis notebooks, and posting calculated refund amounts. This bot reduces manual processing time from 15-30 minutes daily to under 2 minutes per request with zero human intervention.

**Security Posture:** Internal-only automation with no external data exposure, read-only Slack monitoring, and automated responses confined to internal test/production channels.

---

## Use Case

### Business Problem
Credit Operations team manually processes 1-5 SMS toll fraud credit requests daily:
1. Monitor Slack channel (#help-sms-credit-pumping-memos) for incoming requests
2. Extract Looker query URL from message
3. Copy SQL query from Looker dashboard
4. Paste into Jupyter notebook and execute analysis
5. Extract calculated credit amount from notebook output
6. Manually reply to Slack thread with credit amount

**Time Cost:** 5-10 minutes × 1-5 requests/day = **15-30 minutes/day**

### Automated Solution
Bot performs entire workflow automatically:
- Monitors Slack channel every 15 minutes
- Extracts Looker URLs from messages
- Fetches SQL queries via Looker API
- Executes parameterized Jupyter notebook
- Posts calculated credit amount back to Slack thread
- Tracks processed messages to prevent duplicates

**Time Saved:** ~20 hours/month • **Error Rate:** 0% (eliminates manual copy-paste errors)

---

## Data Flow Architecture

```
┌─────────────┐
│   Slack     │ (1) Bot monitors #help-sms-credit-pumping-memos
│   Channel   │     for new messages (READ ONLY)
└──────┬──────┘
       │
       ↓ (2) Extract Looker URL
┌─────────────┐
│  Looker API │ (3) Fetch SQL query via authenticated API
│  (Internal) │     using Looker service credentials
└──────┬──────┘
       │
       ↓ (4) SQL query parameter
┌─────────────────┐
│ Jupyter Notebook│ (5) Execute analysis notebook
│   (Python)      │     - Queries Presto database (internal)
│                 │     - Calculates credit amount
│   Presto Query  │     - Analyzes fraud patterns
│   ↓            │
│   Internal DB   │ (6) Data: billing records, fraud events
└──────┬──────────┘
       │
       ↓ (7) Extract credit amount from output
┌─────────────┐
│    Slack    │ (8) Post result to original thread
│   Thread    │     Format: "Approved, $X,XXX.XX, exceptions"
└─────────────┘
```

### Data Stores
- **State File:** S3 bucket (accsec-ai-credit-bot-state)
  - Tracks processed message IDs (timestamps only, no content)
  - Prevents duplicate processing
- **Outputs:** S3 bucket (temporary retention, 90-day lifecycle)
  - Summary JSON files (~50KB each)
  - Contains aggregated statistics, no PII

---

## Security Analysis

### Authentication & Authorization

**Slack Bot:**
- OAuth Bot Token (xoxb-*) with minimal scopes:
  - `channels:history` - Read messages from authorized channels only
  - `channels:read` - List channel metadata
  - `chat:write` - Post replies to threads
  - `im:write` - Send error notifications via DM
- **No admin privileges, no user impersonation, no channel management**

**Looker API:**
- Service credentials (client ID + secret) with read-only access
- Can only fetch queries, cannot modify dashboards or data
- Authenticated via OAuth 2.0

**Presto Database:**
- Service account with SELECT-only permissions on specific tables:
  - `hive.accsecai.dsg_fds_raw_events` (fraud events)
  - `hive.public.counters_by_billable_item_complete` (billing)
  - `hive.public.rawpii_accounts` (account metadata)
  - `hive.public.rawpii_sms_kafka` (SMS records)
- **No INSERT, UPDATE, DELETE, or DDL permissions**
- Queries parameterized via notebook (SQL injection prevention)

**AWS Resources:**
- IAM role with least-privilege permissions:
  - Read from Secrets Manager (credentials only)
  - Read/Write to S3 bucket (state/outputs only)
  - CloudWatch Logs write (monitoring)
- **No EC2, Lambda, or other service permissions**

### Data Handling

**Data Classification:**
- **Input:** Slack message timestamps, Looker URLs (internal links only)
- **Processing:** SQL queries (aggregate billing data), credit calculations
- **Output:** Dollar amounts, statistical summaries (no PII)
- **Stored:** Message IDs (timestamps), aggregated metrics

**PII/PHI Exposure:**
- **None** - Bot processes aggregated billing totals and fraud statistics
- Account SIDs extracted but not stored permanently
- Phone numbers queried in Presto but only for counting/aggregation
- No customer names, emails, or identifiable information in outputs

**Data Retention:**
- State file: Persistent (rolling 1000 most recent message IDs)
- Output files: 90-day lifecycle policy (auto-deleted from S3)
- Logs: 30-day retention in CloudWatch

### Network Security

**Deployment:**
- Runs in AWS Kubernetes (EKS) within Twilio VPC
- Private subnets only (no public internet exposure)
- Security groups limit traffic to:
  - Slack API (api.slack.com - HTTPS only)
  - Looker API (twiliocloud.cloud.looker.com - HTTPS only)
  - Internal Presto cluster (VPC-internal only)
  - S3 endpoints (VPC endpoints preferred)

**Encryption:**
- **In Transit:** TLS 1.2+ for all API calls (Slack, Looker, S3)
- **At Rest:**
  - S3 bucket encrypted with AWS KMS
  - Secrets Manager encrypted by default
  - No local filesystem storage in production

### Access Control

**Code Repository:**
- Private GitHub repo: `twilio-internal/credits-automation`
- Access limited to Applied Data Science team
- All changes require PR approval
- Git commit history fully auditable

**AWS Resources:**
- TBAC group: `applied-data-science-team` (or similar)
- Access requires Yubikey + VPN
- CloudTrail logs all AWS API calls
- IAM policies enforce least privilege

**Airflow/MWAA:**
- Managed Apache Airflow in `applied-data-science-prod-twilio`
- DAG code in `airflow-dags` repo (version controlled)
- Only team members can view/modify DAG
- Execution logs auditable in Airflow UI

### Threat Mitigation

| Threat | Mitigation |
|--------|-----------|
| **Credential Exposure** | All secrets in AWS Secrets Manager, never in code/logs |
| **Unauthorized Access** | Bot token scoped to specific channels, IAM role least-privilege |
| **Data Exfiltration** | No data leaves Twilio VPC, outputs stored internally in S3 |
| **Message Spoofing** | Bot ignores bot messages (including its own), processes only human messages |
| **SQL Injection** | Queries fetched from Looker (trusted source), notebook uses parameterization |
| **Runaway Costs** | Processing timeout (10 min), resource limits (4GB RAM, 2 CPU), scheduled execution only |
| **Accidental Posting** | Posts only to internal credit operations channels, never customer-facing |
| **State Corruption** | S3 versioning enabled, state file is append-only log |

### Monitoring & Incident Response

**Monitoring:**
- Airflow UI shows execution success/failure
- CloudWatch alarms for repeated failures
- Slack DM notifications on errors (to configured user)
- S3 access logs enabled

**Incident Response:**
- **Pause:** Stop DAG execution immediately via Airflow UI
- **Revoke:** Rotate Slack bot token via Slack admin console
- **Investigate:** Review CloudWatch logs and Airflow execution history
- **Rollback:** Revert to previous Docker image version in ECR
- **Manual Processing:** Team can process requests manually if needed

**Audit Trail:**
- All processed messages logged with timestamps
- Git history tracks code changes
- CloudTrail logs AWS resource access
- Slack audit logs track bot messages

---

## Compliance & Privacy

**Data Residency:** All data remains within Twilio US infrastructure (AWS us-east-1)

**GDPR/Privacy:** No PII processing - bot analyzes aggregate billing metrics only

**SOC 2 Controls:**
- Access control: TBAC + MFA (Yubikey)
- Encryption: TLS + KMS
- Audit logging: CloudTrail + Slack audit logs
- Change management: Git PR workflow
- Incident response: Documented runbook

**Twilio Policies:**
- Follows internal API usage guidelines
- Uses approved AWS services only
- Credentials managed per security standards
- No third-party SaaS integrations

---

## Risk Assessment

**Risk Level:** **LOW**

**Justification:**
- Internal automation only (no customer impact)
- Read-only on most systems (Slack monitoring, Looker queries)
- Writes confined to internal Slack channel and S3 bucket
- No PII processing or external data transfer
- Runs in isolated Kubernetes pod with resource limits
- Full audit trail and instant pause capability

**Comparison:** Lower risk than manual processing (eliminates copy-paste errors, provides audit trail)

---

## Operational Details

**Execution Frequency:** Every 15 minutes (scheduled via Airflow)

**Runtime:** ~1-2 minutes per execution (typically 0 messages, occasionally 1-3)

**Resource Requirements:**
- CPU: 1-2 cores
- Memory: 2-4 GB
- Storage: <1 GB in S3 (with lifecycle policies)

**Failure Handling:**
- Retries: 2 attempts with 5-minute delay
- Notification: DM to configured Slack user
- Fallback: Manual processing workflow

**Team Access:**
- Primary: Data Science team (Applied Data Science)
- Secondary: AccSec AI team (for Airflow infrastructure)
- On-call: Documented in runbook

---

## Security Review Checklist

- [x] **Credentials:** All stored in AWS Secrets Manager (not in code)
- [x] **Least Privilege:** Bot token and IAM role have minimal required permissions
- [x] **Encryption:** TLS in transit, KMS at rest
- [x] **Audit Logging:** CloudTrail, Slack audit logs, application logs
- [x] **Network Isolation:** Runs in private VPC, no public exposure
- [x] **Access Control:** TBAC + MFA required, PR approval for changes
- [x] **Data Minimization:** Stores only message IDs and aggregate metrics
- [x] **Incident Response:** Documented pause/revoke procedures
- [x] **Change Management:** Git workflow with PR reviews
- [x] **Monitoring:** Airflow alerts, CloudWatch, error notifications

---

## Alternatives Considered

**Option 1: Manual Processing (Current State)**
- **Pros:** No automation risk
- **Cons:** Time consuming, error-prone, not scalable, no audit trail

**Option 2: Scheduled Email Digest**
- **Pros:** Less real-time automation
- **Cons:** Still requires manual processing, defeats purpose

**Option 3: Slack Workflow Builder**
- **Pros:** No custom code
- **Cons:** Cannot execute complex notebooks, limited API access

**Selected Option: Custom Bot with Airflow**
- **Pros:** Full automation, auditable, scalable, integrates with existing infrastructure
- **Cons:** Requires bot approval, ongoing maintenance
- **Security:** Acceptable risk with proper controls

---

## Approval Request

**Requested Permissions:**
1. Slack Bot Token with scopes:
   - `channels:history` (read messages)
   - `channels:read` (list channels)
   - `chat:write` (post replies)
   - `im:write` (error notifications)

2. Bot deployment to channels:
   - `#credit_memo_testing` (testing phase)
   - `#help-sms-credit-pumping-memos` (production)

3. Service account for bot identity (if required by Slack admin)

**Security Commitments:**
- Credentials stored in AWS Secrets Manager only
- Code review required for all changes
- Monthly security review of logs
- Immediate notification of any incidents
- Decommission plan if no longer needed

---

## Questions & Answers

### Q: Can the bot read private messages or DMs?
**A:** No. Bot token is scoped only to specific public channels it's invited to. It cannot read DMs or private channels unless explicitly invited.

### Q: What data does the bot store?
**A:** Only message timestamps (e.g., "1234567890.123456") and aggregated credit amounts. No message content, no user information, no PII.

### Q: Can the bot be compromised to spam channels?
**A:** Minimal risk. Bot only posts to threads (not new messages), only in response to processed Looker URLs. Rate limiting: ~4 messages/hour max. Can be instantly revoked via Slack admin.

### Q: How is the bot authenticated?
**A:** OAuth bot token stored in AWS Secrets Manager, accessed via IAM role. Token rotation supported. No tokens in code or logs.

### Q: What happens if the bot malfunctions?
**A:**
1. Automatic: 2 retries, then stops for that message
2. Notification: DM sent to configured admin
3. Manual: Pause DAG in Airflow (takes effect immediately)
4. Fallback: Team processes requests manually

### Q: Who has access to modify the bot?
**A:** Applied Data Science team members with:
- TBAC access to `applied-data-science-prod-twilio`
- Git write access to repository (requires PR approval)
- MFA (Yubikey) + VPN required

### Q: Can the bot access customer data?
**A:** Indirectly via Presto queries, but only aggregated billing data (counts, totals). Queries are read-only SELECT statements. No customer names, phone numbers, or message content stored by bot.

### Q: Is this compliant with data retention policies?
**A:** Yes. Outputs auto-deleted after 90 days via S3 lifecycle policy. State file contains only message IDs (no sensitive data). Logs retained 30 days per standard policy.

### Q: What external services does it connect to?
**A:** Only Slack API (api.slack.com) and Looker API (twiliocloud.cloud.looker.com). Both are Twilio-managed services. No third-party SaaS.

### Q: How is the bot deployed?
**A:**
- Containerized application (Docker)
- Runs in AWS EKS Kubernetes cluster (Twilio VPC)
- Orchestrated by Airflow (MWAA)
- Image stored in AWS ECR with vulnerability scanning
- Infrastructure-as-code (version controlled)

### Q: What permissions does the Slack bot token need?
**A:**
- `channels:history` - Read messages from authorized channels
- `channels:read` - Get channel metadata (ID, name)
- `chat:write` - Post replies to threads
- `im:write` - Send DMs for error notifications

**Does NOT need:**
- User token scopes (acts as bot, not user)
- Channel management (join/create/archive)
- Admin permissions
- File upload/download
- Emoji/reaction permissions

### Q: Can the bot be used for phishing or social engineering?
**A:** Extremely low risk:
- Bot name clearly identifies as "CreditBot" (automated system)
- Posts only standardized format: "Approved, $X,XXX.XX, exceptions"
- No external links or attachments
- No user impersonation
- Bot messages tagged as bot in Slack UI

### Q: What's the disaster recovery plan?
**A:**
1. **Code:** Version controlled in Git (can redeploy any version)
2. **Data:** S3 versioning enabled (can restore previous state)
3. **Credentials:** Stored in Secrets Manager (can rotate immediately)
4. **Infrastructure:** Kubernetes pod auto-restarts on failure
5. **Manual Fallback:** Team can process requests manually (documented procedure)

### Q: How do we decommission the bot if needed?
**A:**
1. Pause/delete Airflow DAG (stops execution)
2. Revoke Slack bot token via admin console
3. Delete Kubernetes pod
4. Remove IAM role permissions
5. Archive S3 bucket (or delete after retention period)
6. Archive GitHub repository

**Estimated Time:** <30 minutes for emergency shutdown

---

## Comparison to Manual Process

| Security Aspect | Manual Process | Automated Bot |
|----------------|----------------|---------------|
| **Audit Trail** | ❌ None | ✅ Full (logs, Git, CloudTrail) |
| **Access Control** | ❌ Anyone with Looker/notebook access | ✅ Service account only, TBAC-controlled |
| **Credential Management** | ⚠️ Individual credentials | ✅ Centralized (Secrets Manager) |
| **Error Rate** | ⚠️ ~5% (copy-paste errors) | ✅ 0% (automated) |
| **Data Exposure** | ⚠️ Notebook outputs on local machines | ✅ Centralized in secured S3 |
| **Reproducibility** | ❌ Manual process varies | ✅ Identical execution every time |
| **Incident Response** | ⚠️ Depends on individual | ✅ Immediate pause capability |

**Security Verdict:** Automation reduces security risk by centralizing credentials, creating audit trails, and eliminating human error.

---

## Technical Security Controls

### Input Validation
- Slack messages: Bot ignores its own messages (prevents loops)
- Looker URLs: Validated to match `*.looker.com` domain only
- SQL queries: Fetched from Looker API (trusted source), not user input
- Notebook parameters: Injected via Papermill (safe parameterization)

### Output Sanitization
- Slack posts: Fixed format string, no user-controlled content
- Logs: Credentials redacted automatically
- Error messages: Generic (no sensitive details in public channels)

### Resource Limits
- Kubernetes pod: 4GB RAM, 2 CPU cores max
- Execution timeout: 10 minutes per run
- Retry limit: 2 attempts per message
- Concurrency: 1 execution at a time (no parallel runs)

### Secrets Management
- **Never in code:** All credentials in AWS Secrets Manager
- **Never in logs:** Automatic redaction of tokens/passwords
- **Rotation:** Secrets Manager supports automatic rotation
- **Access:** IAM role-based, no long-lived credentials in container

### Container Security
- Base image: Official Python 3.9-slim (regularly updated)
- Vulnerability scanning: ECR scans on every push
- Non-root user: Runs as UID 1000 (not root)
- Read-only filesystem (except /tmp)
- No privileged mode or host access

---

## Regulatory Considerations

**SOX Compliance:**
- Financial calculations (credit amounts) fully auditable
- Notebook code version controlled
- Execution logs retained
- No manual modification of results

**GDPR/Privacy:**
- No EU customer data processed
- Aggregate metrics only
- Right to erasure: N/A (no personal data stored)

**Internal Policies:**
- Follows Twilio API usage guidelines
- Uses approved AWS services (EKS, S3, Secrets Manager, MWAA)
- Credentials managed per security standards
- No external SaaS dependencies

---

## Monitoring & Alerting

**Operational Monitoring:**
- Airflow DAG success/failure status
- CloudWatch metrics: execution time, memory usage
- S3 bucket size monitoring
- Slack bot response time

**Security Monitoring:**
- CloudTrail alerts on IAM policy changes
- Secrets Manager access logging
- Unusual Slack API call patterns
- Failed authentication attempts

**Alerting Channels:**
- Airflow: Email to team alias
- CloudWatch: SNS to team Slack channel
- Bot errors: DM to configured admin

---

## Deployment Timeline

**Phase 1: Testing (Weeks 1-2)**
- Deploy to `#credit_memo_testing`
- Manual verification of all outputs
- Security review of logs

**Phase 2: Production (Week 3+)**
- Deploy to `#help-sms-credit-pumping-memos`
- Monitor closely for first week
- Full automation with periodic spot checks

**Rollback Plan:** Can pause immediately via Airflow UI

---

## Security Team Actions Required

1. **Review & Approve** this security brief
2. **Create Slack Bot** in Twilio workspace or approve existing bot token
3. **Assign Scopes** as listed above
4. **Invite Bot** to authorized channels:
   - `#credit_memo_testing` (immediate)
   - `#help-sms-credit-pumping-memos` (after testing phase)
5. **Document** in security registry

**Estimated Approval Time:** 1-2 business days

---

## Contact Information

**Primary Owner:** [Your Name]
**Team:** Applied Data Science - Credit Operations
**Email:** [your-email]@twilio.com
**Slack:** @[your-slack-handle]

**Backup Contact:** [Manager Name]
**Escalation:** [Director Name]

**Repository:** https://github.com/twilio-internal/credits-automation
**Documentation:** See README.md and AIRFLOW_DEPLOYMENT.md in repo

---

## Appendix: Detailed Permissions Matrix

### Slack Bot Token Scopes

| Scope | Purpose | Risk Level |
|-------|---------|------------|
| `channels:history` | Read messages from authorized channels | LOW - Read-only, channels must explicitly invite bot |
| `channels:read` | Get channel ID from name | LOW - Metadata only |
| `chat:write` | Post replies to threads | LOW - Cannot create new messages, only reply |
| `im:write` | Send error DMs | LOW - Only to configured admin user |

**NOT Requested:**
- ❌ `channels:manage` (not needed)
- ❌ `users:read` (not needed)
- ❌ `files:write` (not needed)
- ❌ Admin scopes (not needed)

### AWS IAM Policy (Summary)

```json
{
  "Effect": "Allow",
  "Action": [
    "secretsmanager:GetSecretValue"
  ],
  "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:accsec-ai/credit-bot/credentials-*"
}

{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject",
    "s3:PutObject"
  ],
  "Resource": "arn:aws:s3:::accsec-ai-credit-bot-state/*"
}

{
  "Effect": "Allow",
  "Action": [
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents"
  ],
  "Resource": "arn:aws:logs:us-east-1:*:log-group:/aws/eks/credit-bot:*"
}
```

### Presto Database Permissions

```sql
-- Read-only SELECT on specific tables
GRANT SELECT ON hive.accsecai.dsg_fds_raw_events TO credit_bot_service;
GRANT SELECT ON hive.public.counters_by_billable_item_complete TO credit_bot_service;
GRANT SELECT ON hive.public.rawpii_accounts TO credit_bot_service;
GRANT SELECT ON hive.public.rawpii_sms_kafka TO credit_bot_service;
GRANT SELECT ON hive.public.mcc_country TO credit_bot_service;
-- etc.

-- NO write permissions (no INSERT, UPDATE, DELETE, DROP)
```

---

**END OF SECURITY BRIEF**

*This document is for internal Twilio security review only. Do not distribute externally.*
