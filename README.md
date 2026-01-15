<div align="center">
  <img src="creditbot-wordmark-dark.png" alt="CreditBot" width="600"/>

  # Credits Automation Bot

  [![Status](https://img.shields.io/badge/status-pending%20migration-yellow)]()
  [![Python](https://img.shields.io/badge/python-3.9+-blue)]()
  [![Deployment](https://img.shields.io/badge/deploy-airflow%20%2B%20kubernetes-blue)]()

  **Automated SMS toll fraud credit processing for Twilio**

  [🔄 Migration Plan](#-sagemaker-migration) • [Current Architecture](#-current-architecture) • [Features](#-features)
</div>

---

## 🔄 SageMaker Migration

> **📋 Current Status:** Bot is operational but **pending migration to SageMaker Processing Jobs** with direct Presto database access.
>
> **🎯 Next Step:** Awaiting approval for Presto service account credentials
>
> **📖 Full Migration Plan:** [SAGEMAKER_MIGRATION_PLAN.md](SAGEMAKER_MIGRATION_PLAN.md)

### Why Migrate?

**Current (Local Papermill)**: Notebook executes locally in bot container with credentials from `.env` file

**Future (SageMaker)**: Notebook executes in dedicated SageMaker container with service account credentials from AWS Secrets Manager

**Benefits**:
- ✅ **Security**: Centralized credential management via Secrets Manager
- ✅ **Scalability**: Dedicated compute resources, not shared with bot process
- ✅ **Reliability**: Isolated execution environment
- ✅ **Direct Database Access**: Presto service account (no Looker dependency for queries)

### Migration Blockers

- [ ] Presto service account credentials approval
- [ ] Slack bot security approval (existing blocker)

**See [SAGEMAKER_MIGRATION_PLAN.md](SAGEMAKER_MIGRATION_PLAN.md) for implementation details**

---

## 📋 Overview

Automated pipeline that monitors Slack for credit requests, extracts Looker queries, executes Jupyter notebooks, and posts calculated refund amounts back to Slack threads.

**Time Saved:** 15-30 minutes daily • **Processing Time:** < 2 minutes per request • **Automation Rate:** 95%+ target

### The Problem

Manual credit processing workflow:
1. 👀 Monitor Slack channel for requests
2. 🔗 Click Looker link in message
3. 📋 Copy SQL query from Looker
4. 📓 Paste into Jupyter notebook
5. ▶️ Execute notebook
6. 💰 Copy credit amount from output
7. 💬 Reply to Slack thread

**Time:** 5-10 minutes per request × 1-5 requests/day = **15-30 min/day wasted**

### The Solution

✨ **Fully automated end-to-end** - Bot handles everything from detection to posting results, deployed on Twilio's Airflow infrastructure.

### Current Architecture (Pre-Migration)

> **Note:** This describes the current operational architecture using local Papermill execution. See [SAGEMAKER_MIGRATION_PLAN.md](SAGEMAKER_MIGRATION_PLAN.md) for planned SageMaker architecture.

```
┌─────────────────────────────────────────────────────┐
│  Airflow (MWAA) - applied-data-science-prod-twilio  │
│  Runs every 15 minutes                               │
└────────────┬────────────────────────────────────────┘
             │
             ↓
    ┌───────────────────────────────┐
    │ Kubernetes (EKS)              │
    │  Docker Container             │
    │    ├─ Bot orchestrator        │
    │    └─ Papermill (local exec)  │
    └─────────┬─────────────────────┘
              │
              ├──→ AWS Secrets Manager (credentials)
              ├──→ S3 (state + outputs)
              ├──→ Slack API
              ├──→ Looker API
              └──→ Presto Database (via credentials)
```

**Deployment:** Containerized on Kubernetes, orchestrated by Airflow, fully automated with no manual intervention required.

---

## ✨ Features

### Core Capabilities
- ✅ **Slack Monitoring** - Automatically detects new credit requests in #credit_memo_testing
- ✅ **Smart URL Handling** - Supports both Looker Look URLs and Explore URLs with query parameters
- ✅ **Multiple Link Processing** - Processes all Looker links in a message and combines totals
- ✅ **Looker Integration** - Extracts SQL queries via Looker API
- ✅ **Notebook Execution** - Runs Jupyter notebooks with Papermill
- ✅ **Product Detection** - Automatically identifies Verify vs PSMS queries
- ✅ **Compact Storage** - Saves summary info as JSON (~50KB) instead of full notebooks (~500KB+)
- ✅ **Error Handling** - Sends DM notifications on failures
- ✅ **State Tracking** - Prevents duplicate processing

### Technical Highlights
- **No dry-run mode** - Posts directly to test channel for immediate feedback
- **Verify-only** - Phase 1 focuses on Verify product (PSMS support planned)
- **Efficient storage** - Extracts and saves only Summary Info section from notebooks
- **Production-ready** - Comprehensive logging, error handling, and state management

---

## 🚀 Production Deployment

CreditBot runs automatically on Twilio's Airflow infrastructure. No manual execution needed!

### Access the Bot

**Airflow UI**: AWS Console → `applied-data-science-prod-twilio` → MWAA → Open Airflow UI

**DAG Name**: `credit_bot_automation`

**Schedule**: Runs every 15 minutes automatically

### Monitor Execution

```bash
# Check recent runs via Airflow UI
# DAGs → credit_bot_automation → Graph View

# View logs in CloudWatch
aws logs tail /aws/eks/credit-bot --follow

# Check processed messages
aws s3 ls s3://credit-bot-state-XXXXX/state/
```

### Deployment Guides

| Guide | Purpose |
|-------|---------|
| **[SAGEMAKER_MIGRATION_PLAN.md](SAGEMAKER_MIGRATION_PLAN.md)** | 🔄 **SageMaker migration plan** (start here!) |
| **[AIRFLOW_DEPLOYMENT.md](AIRFLOW_DEPLOYMENT.md)** | 🚀 Deploy updates, troubleshoot issues (current) |
| **[RUNBOOK.md](RUNBOOK.md)** | 📖 Operations guide for production (current) |

**Archived Pre-Migration Docs:** [archive/pre-sagemaker-docs/](archive/pre-sagemaker-docs/)

---

## 💻 Local Development

> **Note:** These instructions are for the current pre-migration architecture. Will be updated after SageMaker migration.

For testing changes locally before deploying:

### Prerequisites
- Python 3.9+
- Docker (optional, for container testing)
- AWS CLI (for production deployment)
- Slack Bot Token with permissions: `channels:history`, `channels:read`, `chat:write`, `im:write`
- Looker API credentials (client ID and secret)
- Presto database access

### Quick Start

```bash
# 1. Clone repository
git clone git@github.com:twilio-internal/credits-automation.git
cd credits-automation

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your credentials (see LOCAL_DEVELOPMENT.md)

# 5. Run the bot locally
python3 run_bot.py
```

### Test with Docker

```bash
# Build image
docker build -t credit-bot:test .

# Run container
docker run --rm --env-file .env credit-bot:test
```

---

## 📁 Project Structure

```
credits-automation/
├── run_bot.py                          # 🎯 Main entry point
├── requirements.txt                    # Python dependencies
├── docker-requirements.txt             # 🐳 Docker/production dependencies
├── .env.example                        # Config template
│
├── Dockerfile                          # 🐳 Container definition
├── .dockerignore                       # Docker build exclusions
├── deploy.sh                           # 🚀 Deployment script
│
├── airflow/                            # ✈️ Airflow DAG
│   └── credit_bot_dag.py               # DAG definition for MWAA
│
├── src/                                # Bot source code
│   ├── credit_bot.py                   # Main orchestrator
│   ├── slack_client.py                 # Slack API wrapper
│   ├── looker_client.py                # Looker API wrapper
│   ├── notebook_executor.py            # Papermill runner (to be replaced)
│   ├── state_manager.py                # Message tracking (S3-backed)
│   ├── aws_integration.py              # 🔐 AWS Secrets Manager + S3
│   └── config.py                       # Configuration management
│
├── archive/                            # 📦 Archived files
│   ├── pre-sagemaker-docs/             # Pre-migration documentation
│   └── old-local-execution/            # To be populated during migration
│
├── data/                               # Runtime data (local dev only)
│   ├── processed_messages.json         # Tracks processed messages
│   └── outputs/                        # Summary JSON files
│
├── logs/                               # Application logs (local dev only)
│   └── credit_bot.log
│
├── SAGEMAKER_MIGRATION_PLAN.md         # 🔄 Migration plan (READ THIS FIRST)
├── AIRFLOW_DEPLOYMENT.md               # Production deployment guide
├── RUNBOOK.md                          # Operations runbook
├── SECURITY_APPROVAL_BRIEF.md          # Security documentation
└── SECURITY_BRIEF_ONE_PAGE.md          # Security summary
```

**Production**: State and outputs stored in S3, not local files

---

## 🔧 Configuration

### Required Environment Variables

```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_USER_ID=W014QM1DAPN                       # For error DMs
SLACK_TEST_CHANNEL=credit_memo_testing

# Looker Configuration
LOOKER_CLIENT_ID=your-client-id
LOOKER_CLIENT_SECRET=your-client-secret
LOOKER_BASE_URL=https://twiliocloud.cloud.looker.com

# Notebook Configuration
NOTEBOOK_PATH=/Users/amorris/Documents/credit memos/Verify - Credit Recommendation.ipynb
```

**See `.env.example` for complete configuration options**

---

## 🎯 How It Works

```mermaid
graph LR
    A[Slack Message] --> B[Extract Looker URLs]
    B --> C[Get SQL from Looker API]
    C --> D{Verify Query?}
    D -->|Yes| E[Execute Notebook]
    D -->|No| F[Skip PSMS]
    E --> G[Extract Summary]
    G --> H[Save JSON]
    H --> I[Post to Slack]
```

### Workflow
1. **Monitor** - Bot checks #credit_memo_testing for new messages
2. **Extract** - Pulls all Looker URLs from message (supports Look and Explore URLs)
3. **Fetch** - Gets SQL queries from Looker API
4. **Validate** - Checks if query contains "Authy" (Verify product)
5. **Execute** - Runs Jupyter notebook with SQL as parameter
6. **Process** - Extracts credit amount from Summary Info section
7. **Store** - Saves compact JSON summary (~50KB vs ~500KB full notebook)
8. **Reply** - Posts combined credit amount to Slack thread
9. **Track** - Marks message as processed to avoid duplicates

### Multiple URL Handling
If a message contains multiple Looker links:
- Bot processes each URL sequentially
- Skips non-Verify queries (PSMS)
- Combines credit amounts from all Verify queries
- Posts single total to Slack thread

---

## 📊 Output Format

### Slack Thread Reply
```
Approved, $4,948.80, exceptions
```

### Saved Summary (JSON)
```json
{
  "extracted_at": "2026-01-08T14:30:00",
  "credit_amount": 4948.80,
  "summary_outputs": {
    "cell_20": {
      "source": "output_df = ...",
      "outputs": [
        {
          "type": "execute_result",
          "text": "mode  traffic_prop  msg_count  fraud_cost  block_rate  credit\nbasic  1.000  35644  $7,526.30  0.416  $4,948.80"
        }
      ]
    }
  }
}
```

---

## 🔐 Security

- ✅ All credentials in `.env` (never committed to git)
- ✅ Bot token has minimal required permissions
- ✅ Audit trail of all processed messages
- ✅ Error notifications sent via DM (not public channel)
- ✅ `.gitignore` configured to exclude sensitive files

---

## 🚧 Current Limitations

### Phase 1 Scope
- **Verify only** - PSMS queries are skipped (Phase 2 planned)
- **Single channel** - Monitors one channel at a time
- **Polling model** - Runs on schedule, not real-time event-driven
- **No retry logic** - Failed messages must be reprocessed manually

### Planned Enhancements (Phase 2+)
- 🔮 PSMS notebook integration
- 🔮 Multi-channel support
- 🔮 Real-time event-driven processing (Slack Events API)
- 🔮 Retry logic with exponential backoff
- 🔮 Dashboard for monitoring
- 🔮 ML-based credit prediction

---

## 🧪 Testing

### Test Message Format
Post to #credit_memo_testing:
```
Please process this credit request
https://twiliocloud.cloud.looker.com/explore/Revenue/counters_by_billable_item?qid=9TZEymaiGzQzGLcFUsvjpR
```

### Expected Behavior
1. Bot detects new message
2. Extracts Looker URL
3. Fetches SQL query
4. Confirms it's a Verify query (has "Authy")
5. Executes notebook
6. Extracts credit amount
7. Posts reply: `Approved, $XXX.XX, exceptions`
8. Saves summary JSON to `data/outputs/`

### Verify Success
```bash
# Check logs
tail -f logs/credit_bot.log

# Check output
ls -lh data/outputs/summary_*.json

# Check state
cat data/processed_messages.json | jq .
```

---

## 📚 Documentation

### 🔄 Migration (Start Here!)
| Document | Description |
|----------|-------------|
| **[SAGEMAKER_MIGRATION_PLAN.md](SAGEMAKER_MIGRATION_PLAN.md)** | 🎯 **SageMaker migration plan** - implementation phases, AWS setup, testing |

### Current Operations (Pre-Migration)
| Document | Description |
|----------|-------------|
| **[AIRFLOW_DEPLOYMENT.md](AIRFLOW_DEPLOYMENT.md)** | 🚀 Production deployment guide - build, push, deploy |
| **[RUNBOOK.md](RUNBOOK.md)** | 📖 Operations guide - monitoring, troubleshooting, incident response |
| **[SECURITY_APPROVAL_BRIEF.md](SECURITY_APPROVAL_BRIEF.md)** | 🔐 Security documentation and compliance |
| `.env.example` | Environment variable template |

### Archived Documentation
| Document | Description |
|----------|-------------|
| **[archive/pre-sagemaker-docs/](archive/pre-sagemaker-docs/)** | 📦 Pre-migration documentation (LOCAL_DEVELOPMENT, SETUP_GUIDE, PROTOTYPE_SUMMARY) |

---

## 🐛 Troubleshooting

### Bot not responding?
1. Check Slack bot token is valid: `SLACK_BOT_TOKEN=xoxb-...`
2. Verify bot is invited to channel: `/invite @CreditBot`
3. Check logs: `tail -f logs/credit_bot.log`

### SQL extraction failing?
1. Verify Looker credentials are correct
2. Ensure URL format is supported (Look or Explore with qid)
3. Check Looker base URL: `https://twiliocloud.cloud.looker.com`

### Notebook execution errors?
1. Verify notebook path is correct
2. Check notebook has parameters cell with `looker = ""`
3. Ensure Python kernel is available: `jupyter kernelspec list`

**See [RUNBOOK.md](RUNBOOK.md) for detailed troubleshooting**

---

## 📈 Success Metrics

**Target (after 30 days):**
- ✅ 95%+ automation rate
- ✅ < 2 min average processing time
- ✅ Zero incorrect credit amounts
- ✅ 15-30 minutes saved daily

---

## 🤝 Contributing

Internal Twilio automation project. For questions or issues, contact the maintainer.

---

## 📝 License

Internal use only - Twilio proprietary.

---

<div align="center">

**Status:** ⏳ Operational, Pending SageMaker Migration

**Blockers:**
- Presto service account credentials approval
- Slack bot security approval

**Next Steps:** See [SAGEMAKER_MIGRATION_PLAN.md](SAGEMAKER_MIGRATION_PLAN.md)

**Deployment:** Airflow MWAA on `applied-data-science-prod-twilio`

Made with ☕ by the Credit Operations Team

</div>
