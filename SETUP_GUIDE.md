# Credits Automation - Setup Guide

Complete setup instructions for CreditBot - both production deployment and local development.

---

## 🎯 Setup Type

Choose your setup path:

- **🚀 [Production Deployment](#-production-deployment-setup)**: Deploy to Airflow on AWS (automated, runs every 15 minutes)
- **💻 [Local Development](#-local-development-setup)**: Run locally for testing and development

---

## 📋 Common Prerequisites

### For Production Deployment
- AWS access to `applied-data-science-prod-twilio` account
- TBAC access (already granted)
- Docker installed locally
- AWS CLI configured
- Access to `airflow-dags` GitHub repository

### For Local Development
- Python 3.9 or higher
- Slack app with bot token
- Looker API credentials
- Presto database access
- Jupyter notebook environment
- Git (for version control)

---

## 🚀 Production Deployment Setup

For deploying CreditBot to Airflow/Kubernetes infrastructure.

### Prerequisites Checklist

- [x] AWS console access to `applied-data-science-prod-twilio`
- [ ] Docker Desktop installed and running
- [ ] AWS CLI configured with credentials
- [ ] Slack bot token obtained
- [ ] Looker API credentials obtained
- [ ] Presto service credentials (⏳ approval pending)

### Quick Start

1. **Build Docker Image**
   ```bash
   cd /path/to/credits-automation
   docker build -t credit-bot:latest .
   ```

2. **Deploy to ECR**
   ```bash
   ./deploy.sh
   # Or with version tag:
   # ./deploy.sh v1.0.0
   ```

3. **Set Up AWS Resources**
   - Create ECR repository
   - Create S3 bucket for state
   - Store credentials in AWS Secrets Manager
   - See detailed steps in [AIRFLOW_DEPLOYMENT.md](AIRFLOW_DEPLOYMENT.md)

4. **Deploy DAG to Airflow**
   - Update image URL in `airflow/credit_bot_dag.py`
   - Submit PR to `airflow-dags` repository
   - Verify in Airflow UI

### Detailed Production Setup

**📖 Complete Guide**: See [AIRFLOW_DEPLOYMENT.md](AIRFLOW_DEPLOYMENT.md) for:
- AWS resource creation (ECR, S3, Secrets Manager)
- Docker image building and pushing
- Airflow DAG deployment
- Monitoring and troubleshooting
- Production operations

**📖 Operations Guide**: See [RUNBOOK.md](RUNBOOK.md) for:
- Day-to-day operations
- Monitoring and health checks
- Incident response procedures
- Common issues and solutions

---

## 💻 Local Development Setup

### Step 1: Install Dependencies

```bash
# Navigate to project directory
cd ~/Documents/credits-automation

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

**Required values in `.env`:**

```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-actual-bot-token-here
SLACK_USER_ID=U123456789  # Your Slack user ID (for error DMs)
SLACK_TEST_CHANNEL=credit_memo_testing

# Looker Configuration
LOOKER_CLIENT_ID=x3MzDz9gp3HCJHNzbnwK  # Your actual client ID
LOOKER_CLIENT_SECRET=5kqbXcr8hqq2VdVpQdkbgHvR  # Your actual secret
LOOKER_BASE_URL=https://twilio.cloud.looker.com

# Bot Configuration
BOT_NAME=CreditBot
DRY_RUN=true  # Keep as true for testing!
```

### Step 3: Get Your Slack User ID

```bash
# Run this command to get your Slack user ID
python3 -c "from slack_sdk import WebClient; client = WebClient(token='YOUR_BOT_TOKEN'); print(client.auth_test()['user_id'])"
```

Or visit: https://api.slack.com/methods/auth.test/test

### Step 4: Test the Bot

```bash
# Run in dry-run mode first (safe - won't post anything)
python3 run_bot.py
```

---

## 📝 Detailed Configuration

### Slack Setup

#### Getting Your Bot Token

1. Go to https://api.slack.com/apps
2. Select your app (or create one if needed)
3. Go to "OAuth & Permissions"
4. Copy the "Bot User OAuth Token" (starts with `xoxb-`)

#### Required Slack Permissions

Your bot needs these OAuth scopes:
- `channels:history` - Read channel messages
- `channels:read` - List channels
- `chat:write` - Post messages
- `im:write` - Send DMs

#### Finding Your User ID

Option 1: Using Slack API
```bash
curl -X GET "https://slack.com/api/auth.test" \
  -H "Authorization: Bearer YOUR_BOT_TOKEN"
```

Option 2: From Slack UI
1. Click your profile picture
2. Select "Profile"
3. Click the "..." menu
4. Select "Copy member ID"

### Looker Setup

You already have:
- Client ID: `x3MzDz9gp3HCJHNzbnwK`
- Client Secret: `5kqbXcr8hqq2VdVpQdkbgHvR`

Just add these to your `.env` file.

### Notebook Setup

The notebook is already in place: `Verify - Credit Recommendation.ipynb`

**Important:** Make sure the notebook has a parameter cell with:
```python
# Parameters
looker = ""  # This will be injected by papermill
```

---

## 🧪 Testing

### Test 1: Configuration

```bash
# Test that all configuration is valid
python3 -c "from src.config import Config; Config.validate(); print('✅ Config valid')"
```

### Test 2: Slack Connection

```bash
# Test Slack API connection
python3 -m src.slack_client
```

Expected output:
```
✅ Slack connection successful!
✅ Found channel #credit_memo_testing: C12345678
📨 Retrieved X recent messages
```

### Test 3: Looker Connection

```bash
# Test Looker API authentication
python3 -m src.looker_client
```

Expected output:
```
INFO - Successfully authenticated with Looker API
```

### Test 4: Full Bot Run (Dry Run)

```bash
# Run the bot in dry-run mode
python3 run_bot.py
```

This will:
- ✅ Connect to Slack
- ✅ Connect to Looker
- ✅ Check for messages
- ✅ Process them (but NOT post results)
- ✅ Show what it WOULD do

---

## 🎯 Usage

### Running in Test Mode (Dry Run)

```bash
# Make sure DRY_RUN=true in .env
python3 run_bot.py
```

The bot will:
1. Check #credit_memo_testing for new messages
2. Extract Looker URLs
3. Get SQL queries from Looker
4. Execute the notebook
5. Calculate credit amounts
6. **SHOW** what it would post (but NOT actually post)

### Running in Production

**⚠️ Production runs on Airflow, not locally!**

For production deployment, the bot runs automatically on Airflow infrastructure. See the [Production Deployment Setup](#-production-deployment-setup) section above and [AIRFLOW_DEPLOYMENT.md](AIRFLOW_DEPLOYMENT.md).

**Local "production-like" testing:**
```bash
# Edit .env and change:
DRY_RUN=false
SLACK_TEST_CHANNEL=credit_memo_testing  # Use test channel!

# Run the bot locally
python3 run_bot.py
```

**Note**: This is for testing only. Actual production uses:
- Airflow for scheduling (every 15 minutes)
- Kubernetes for execution
- AWS Secrets Manager for credentials
- S3 for state storage

---

## 📊 Monitoring

### Log Files

Logs are written to: `logs/credit_bot.log`

```bash
# Watch logs in real-time
tail -f logs/credit_bot.log
```

### State File

Processed messages are tracked in: `data/processed_messages.json`

```bash
# View current state
cat data/processed_messages.json | jq .
```

### Output Notebooks

Executed notebooks are saved to: `data/outputs/`

```bash
# List recent executions
ls -lht data/outputs/ | head -10
```

---

## 🐛 Troubleshooting

### Issue: "Missing required configuration"

**Solution:** Make sure `.env` file exists and has all required values:
```bash
# Check if .env exists
ls -la .env

# Verify it has required keys
grep -E "(SLACK_BOT_TOKEN|LOOKER_CLIENT_ID)" .env
```

### Issue: "Channel not found"

**Solution:** Make sure:
1. Channel name in `.env` matches actual channel
2. Bot is invited to the channel
3. No `#` prefix in the .env value

```bash
# Invite bot to channel in Slack:
/invite @CreditBot
```

### Issue: "Looker authentication failed"

**Solution:** Verify credentials:
```bash
# Test Looker API manually
curl -X POST "https://twilio.cloud.looker.com/api/4.0/login" \
  -d "client_id=YOUR_CLIENT_ID&client_secret=YOUR_SECRET"
```

### Issue: "Notebook execution failed"

**Solution:** Check:
1. Notebook has parameters cell
2. Notebook runs manually with test query
3. Check notebook output in `data/outputs/`

```bash
# Test notebook manually
jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=600 \
  "Verify - Credit Recommendation.ipynb"
```

### Issue: "Could not extract credit_amount"

**Solution:** Verify:
1. Notebook completes successfully
2. Last cell outputs `credit_amount` variable
3. Check the output notebook to see what was produced

---

## 🔄 Workflow

### Typical Run

```
1. Bot starts
   ↓
2. Connects to Slack + Looker
   ↓
3. Gets recent messages from channel
   ↓
4. Filters out already-processed messages
   ↓
5. For each new message:
   a. Extract Looker URL
   b. Get SQL from Looker API
   c. Check if Verify query (has "Authy")
   d. Execute notebook with SQL
   e. Extract credit_amount from output
   f. Post result to Slack thread
   g. Mark as processed
   ↓
6. Updates state file
   ↓
7. Exits
```

### Message Processing Logic

```
Message received
    ↓
Has Looker link? ──No──> Post "Please provide Looker link"
    ↓ Yes
Extract SQL from Looker
    ↓
Is Verify query? ──No──> Ignore silently (PSMS)
    ↓ Yes
Execute notebook
    ↓
Success? ──No──> Send DM with error
    ↓ Yes
Extract credit_amount
    ↓
Post to Slack: "Approved, $X, exceptions"
```

---

## 🎬 Next Steps

### After Local Testing

1. **Test locally** with test Slack channel
2. **Review all outputs** manually
3. **Fix any issues** that arise
4. **Test with Docker** (`docker build` + `docker run`)
5. **Deploy to production** Airflow (see [AIRFLOW_DEPLOYMENT.md](AIRFLOW_DEPLOYMENT.md))

### After Production Deployment

1. **Monitor first 24 hours** closely (Airflow UI + CloudWatch logs)
2. **Verify state file** updating in S3
3. **Check Slack posts** are appearing correctly
4. **Review success rate** (target: >95%)
5. **Set up alerts** (SLA monitoring in Airflow)

### Future Enhancements

- ✅ Airflow scheduling (complete)
- ✅ AWS Secrets Manager integration (complete)
- ✅ S3-backed state management (complete)
- 🔮 PSMS notebook integration (planned)
- 🔮 Dashboard for monitoring (planned)
- 🔮 ML-based credit prediction (planned)

---

## 📞 Support

### Check Logs

```bash
# Recent errors
grep ERROR logs/credit_bot.log | tail -20

# Recent successes
grep "Message processing complete" logs/credit_bot.log | tail -10
```

### Reset State

If you need to reprocess messages:
```bash
# Backup current state
cp data/processed_messages.json data/processed_messages.json.backup

# Clear processed messages
echo '{"processed_messages": [], "total_processed": 0}' > data/processed_messages.json
```

### Get Stats

```bash
python3 -c "from src.state_manager import StateManager; m = StateManager(); print(m.get_stats())"
```

---

## 🔒 Security Notes

- Never commit `.env` file to git
- Rotate API tokens regularly
- Keep logs secure (contain sensitive data)
- Review output notebooks before sharing
- Use dry-run mode for all testing

---

**Ready to start?**

```bash
# 1. Setup
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials

# 2. Test
python3 run_bot.py

# 3. Monitor
tail -f logs/credit_bot.log
```

Good luck! 🚀
