<div align="center">
  <img src="creditbot-wordmark-dark.png" alt="CreditBot" width="600"/>

  # Credits Automation Bot

  [![Status](https://img.shields.io/badge/status-ready%20for%20testing-success)]()
  [![Python](https://img.shields.io/badge/python-3.9+-blue)]()

  **Automated SMS toll fraud credit processing for Twilio**

  [Quick Start](#-quick-start) • [Setup Guide](SETUP_GUIDE.md) • [Features](#-features)
</div>

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

✨ **Fully automated end-to-end** - Bot handles everything from detection to posting results.

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

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Slack Bot Token with permissions: `channels:history`, `channels:read`, `chat:write`, `im:write`
- Looker API credentials (client ID and secret)
- Jupyter notebook with parameters cell

### Installation

```bash
# 1. Clone repository
cd /Users/amorris/Documents/credits-automation

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your credentials (see Setup Guide)

# 4. Run the bot
python3 run_bot.py
```

### First Run
The bot will:
1. ✅ Test Slack connection
2. ✅ Test Looker authentication
3. ✅ Find #credit_memo_testing channel
4. 📥 Check for new messages
5. 💬 Post credit amounts to Slack threads

**📖 Full Setup Instructions:** [SETUP_GUIDE.md](SETUP_GUIDE.md)

---

## 📁 Project Structure

```
credits-automation/
├── run_bot.py                          # 🎯 Main entry point
├── requirements.txt                    # Python dependencies
├── .env.example                        # Config template
├── SETUP_GUIDE.md                      # Complete setup instructions
├── PROTOTYPE_SUMMARY.md                # Implementation details
│
├── src/                                # Bot source code
│   ├── credit_bot.py                   # Main orchestrator
│   ├── slack_client.py                 # Slack API wrapper
│   ├── looker_client.py                # Looker API wrapper
│   ├── notebook_executor.py            # Papermill runner + summary extraction
│   ├── state_manager.py                # Message tracking
│   └── config.py                       # Configuration management
│
├── data/                               # Runtime data
│   ├── processed_messages.json         # Tracks processed messages
│   └── outputs/                        # Summary JSON files (not full notebooks)
│
└── logs/                               # Application logs
    └── credit_bot.log
```

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

| Document | Description |
|----------|-------------|
| [SETUP_GUIDE.md](SETUP_GUIDE.md) | ⭐ Complete setup and configuration instructions |
| [PROTOTYPE_SUMMARY.md](PROTOTYPE_SUMMARY.md) | Implementation details and current status |
| `.env.example` | Environment variable template |

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
1. Verify notebook path is correct (note space in "credit memos")
2. Check notebook has parameters cell with `looker = ""`
3. Ensure Python kernel is available: `jupyter kernelspec list`

**See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed troubleshooting**

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

**Status:** ✅ Ready for Testing (pending Slack bot approval)

Made with ☕ by the Credit Operations Team

</div>
