# Credits Automation

Automated SMS toll fraud credit recommendation system that monitors Slack, extracts Looker queries, processes through Jupyter notebooks, and posts refund amounts back to Slack.

## 📋 Project Overview

**Current Status:** ✅ Prototype Complete - Ready for Testing
**Created:** 2025-01-08
**Last Updated:** 2026-01-08

### Problem Statement

Currently, processing credit memo requests for SMS toll fraud is a manual process:
1. Monitor Slack channel for new requests
2. Click Looker link in message
3. Copy SQL query from Looker
4. Paste into Jupyter notebook
5. Execute notebook
6. Copy credit amount from output
7. Reply to Slack thread with refund amount

**Manual time:** ~5-10 minutes per request
**Volume:** 1-5 requests per day
**Total time saved:** 15-30 minutes daily

### Solution

Fully automated pipeline that handles the entire workflow end-to-end.

## 📁 Repository Structure

```
credits-automation/
├── README.md                          # This file
├── SETUP_GUIDE.md                     # ⭐ Complete setup instructions
├── DEVELOPMENT_QUESTIONS.md           # Questions from development
├── AUTOMATION_PLAN.md                 # Detailed implementation plan
├── INTERVIEW_QUESTIONS.docx           # Answered questions
├── run_bot.py                         # ⭐ Main script to run the bot
├── requirements.txt                   # Python dependencies
├── .env.example                       # Environment config template
├── Verify - Credit Recommendation.ipynb  # Jupyter notebook
├── src/                               # ⭐ Bot source code
│   ├── credit_bot.py                  # Main orchestrator
│   ├── slack_client.py                # Slack API integration
│   ├── looker_client.py               # Looker API integration
│   ├── notebook_executor.py           # Papermill notebook runner
│   ├── state_manager.py               # Tracks processed messages
│   └── config.py                      # Configuration management
├── data/                              # State and outputs
│   ├── processed_messages.json        # Tracking file
│   └── outputs/                       # Executed notebooks
└── logs/                              # Log files
    └── credit_bot.log
```

## 🚀 Quick Start

### Prototype is Ready!

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure credentials
cp .env.example .env
# Edit .env with your Slack/Looker credentials

# 3. Run in dry-run mode (safe - won't post anything)
python3 run_bot.py
```

**📖 See [SETUP_GUIDE.md](SETUP_GUIDE.md) for complete instructions**

## 📋 Key Documents

### [SETUP_GUIDE.md](SETUP_GUIDE.md) ⭐ START HERE
Complete setup and testing instructions:
- Installation steps
- Configuration guide
- Testing procedures
- Troubleshooting
- Usage examples

### [DEVELOPMENT_QUESTIONS.md](DEVELOPMENT_QUESTIONS.md)
Questions and considerations from development:
- Implementation questions needing answers
- Known limitations
- Future enhancement ideas
- Testing checklist

### [AUTOMATION_PLAN.md](AUTOMATION_PLAN.md)
Original implementation plan:
- Architecture analysis
- Technical components
- Risk assessment
- Timeline and phases

### [INTERVIEW_QUESTIONS.docx](INTERVIEW_QUESTIONS.docx)
Answered requirements questions:
- Slack/Looker configuration
- Bot behavior preferences
- Error handling
- Deployment strategy

## 🎯 Scope

### In Scope (Phase 1)
- ✅ Verify product requests only (identified by "Authy" in specific columns)
- ✅ Automated Looker query extraction
- ✅ Notebook execution via Papermill
- ✅ Slack thread replies with credit amounts
- ✅ Error detection and handling

### Out of Scope (Phase 1)
- ❌ PSMS requests (separate notebook - will integrate later)
- ❌ Manual approval steps (full automation preferred)
- ❌ Historical data processing
- ❌ Multi-ASID batch processing

### Future Enhancements (Phase 2+)
- 🔮 PSMS integration
- 🔮 Dashboard for monitoring
- 🔮 Advanced analytics on credit patterns
- 🔮 ML-based credit amount prediction

## 🔧 Technical Stack (Proposed)

```yaml
Language: Python 3.9+

Libraries:
  - slack-sdk: Slack API client
  - papermill: Notebook execution
  - nbformat: Parse notebook outputs
  - selenium/playwright: Looker scraping (if needed)
  - pandas: Data processing
  - requests: HTTP calls

Deployment:
  - Option 1: Airflow DAG (Recommended)
  - Option 2: Local Python script
  - Option 3: Cloud Function (AWS Lambda/GCP)

Storage:
  - SQLite or JSON for state tracking
  - Track processed messages to avoid duplicates
```

## 🎬 Implementation Timeline

### Phase 1: Setup & Auth (Week 1)
- [ ] Slack API setup and testing
- [ ] Looker access investigation (API vs scraping)
- [ ] Notebook parameterization with Papermill
- [ ] Test all authentication flows

### Phase 2: Core Automation (Week 2)
- [ ] Build processing pipeline
- [ ] Implement state management
- [ ] Add error handling
- [ ] End-to-end testing

### Phase 3: Production (Week 3)
- [ ] Deploy to Airflow/schedule
- [ ] Add monitoring and alerts
- [ ] Production testing with test channel
- [ ] Go live on real channel

**Total Estimated Time:** 15-20 hours over 2-3 weeks

## ⚠️ Requirements

### Must Have Before Starting
- [ ] Slack API token with appropriate permissions
- [ ] Looker authentication method determined
- [ ] Airflow access (or alternative deployment plan)
- [ ] Test Slack channel created
- [ ] Interview questions answered

### Nice to Have
- [ ] Desktop alerts integration (already built!)
- [ ] Metrics dashboard
- [ ] Dry-run testing mode

## 🔐 Security Notes

- All API tokens stored in environment variables (not in code)
- Minimal Slack permissions (only what's needed)
- Audit trail of all processed requests
- Rate limiting to avoid API throttling

## 📊 Success Metrics

After 30 days of automation:
- ✅ 95%+ of Verify requests processed automatically
- ✅ Zero incorrect credit amounts posted
- ✅ Average processing time < 2 minutes
- ✅ 15-30 minutes saved daily

## 🤝 Contributing

This is a personal automation project. For questions or issues, contact the maintainer.

## 📝 License

Internal use only - Twilio proprietary.

---

## 🔗 Related Resources

- [Jupyter Notebook Alerts](https://github.com/amorris412/jupyter-notebook-alerts) - Desktop notification system
- Original notebook: `Verify - Credit Recommendation.ipynb`
- Slack channel: `#help-sms-credit-pumping-memos` (production, TBD for test)

---

**Status:** ✅ Prototype Complete - Ready for Testing

**Next Actions:**
1. Review [SETUP_GUIDE.md](SETUP_GUIDE.md)
2. Configure `.env` with credentials
3. Run `python3 run_bot.py` in dry-run mode
4. Test with sample messages in #credit_memo_testing
5. Review [DEVELOPMENT_QUESTIONS.md](DEVELOPMENT_QUESTIONS.md) and provide answers
