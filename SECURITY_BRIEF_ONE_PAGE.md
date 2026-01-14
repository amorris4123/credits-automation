# CreditBot Security Approval - One Page Brief

**Project:** Automated SMS Toll Fraud Credit Processing Bot
**Owner:** team_accsec-ai
**Risk Level:** LOW
**Date:** 2026-01-14

---

## What It Does

Automates credit request processing from Slack by: monitoring channel → extracting Looker URLs → querying Presto → calculating credits → posting results. **Eliminates manual process that wastes 15-30 min/day.**

---

## Security Architecture

| Component | Security Control |
|-----------|------------------|
| **Slack Bot** | OAuth 2.0, minimal scopes (read channels, post messages), bot token stored in AWS Secrets Manager |
| **Credentials** | All secrets in AWS Secrets Manager, IAM role-based access, no credentials in code/logs |
| **Data Storage** | State file in S3 (message IDs only, no PII), outputs auto-deleted after 90 days |
| **Network** | Runs in Twilio VPC, all connections TLS 1.2+, no internet egress |
| **Execution** | Kubernetes pod (isolated, ephemeral), non-root container, resource limits enforced |
| **Access Control** | Least privilege IAM policies, TBAC-controlled deployment, audit logging enabled |

---

## Data Handling

**What We Access:**
- Slack messages (Looker URLs only)
- Presto database (billing records for fraud analysis)
- Looker API (SQL queries)

**What We Store:**
- Message IDs (to prevent duplicates) - **NO MESSAGE CONTENT**
- Credit calculation outputs (account SID + amount) - **NO PII**

**What We DON'T Touch:**
- Customer phone numbers
- Message contents
- Personal identifiable information

**Data Retention:** 90 days (S3 lifecycle policy), then auto-deleted

---

## Threat Mitigation

| Threat | Mitigation |
|--------|------------|
| Credential Exposure | AWS Secrets Manager + IAM roles, secrets never in code/logs |
| Unauthorized Access | OAuth scopes limited, bot only in approved channels, IAM policies enforced |
| Data Exfiltration | No PII stored, VPC network isolation, audit logs track all access |
| SQL Injection | Parameterized queries only, no user input in SQL, Presto read-only access |
| Container Escape | Non-root user, resource limits, ephemeral pods, latest security patches |

---

## Compliance & Monitoring

**Compliance:** SOC 2 controls maintained, GDPR-compliant (no EU data), aligns with Twilio security policies

**Monitoring:**
- CloudWatch logs (all actions logged)
- Airflow execution history
- S3 access logs
- Failed auth attempts alerting

**Incident Response:** Runbook documented, escalation to team_accsec-ai, can disable in <2 minutes via Airflow UI

---

## Risk Assessment: **LOW**

**Why Low Risk:**
✅ No customer-facing access
✅ Read-only Presto access
✅ No PII storage
✅ Fully audited
✅ Isolated execution environment
✅ Automated = fewer human errors than manual process

**Comparison to Manual Process:**
- **Manual:** Credentials in .env files, copy-paste errors, no audit trail, local execution
- **Automated:** Secrets Manager, validated calculations, full audit logs, isolated containers

---

## Deployment Details

**Environment:** `applied-data-science-prod-twilio` AWS account
**Orchestration:** Airflow MWAA (managed by data science team)
**Schedule:** Every 15 minutes
**Team Access:** TBAC-controlled, team_accsec-ai only

**Approvals Needed:**
1. ✅ AWS account access (granted)
2. ⏳ Presto service credentials (pending)
3. ⏳ Slack bot OAuth approval (this request)

---

## Questions?

**Contact:** team_accsec-ai
**Repository:** https://github.com/twilio-internal/credits-automation
**Full Security Brief:** SECURITY_APPROVAL_BRIEF.md (25 pages with technical details)
