# Credits Automation

Automated SMS toll fraud credit recommendation system that monitors Slack, extracts Looker queries, processes through Jupyter notebooks, and posts refund amounts back to Slack.

## 📋 Project Overview

**Current Status:** Planning Phase
**Created:** 2025-01-08
**Last Updated:** 2025-01-08

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
├── AUTOMATION_PLAN.md                 # Detailed implementation plan
├── INTERVIEW_QUESTIONS.docx           # Questions to answer before building
├── INTERVIEW_QUESTIONS.md             # Markdown version of questions
├── Verify - Credit Recommendation.ipynb  # Current manual notebook
└── src/                               # (Coming soon) Automation code
    ├── slack_monitor.py
    ├── looker_client.py
    ├── notebook_executor.py
    └── config.py
```

## 🚀 Quick Start

### Current Phase: Requirements Gathering

**Next Steps:**
1. **Answer Questions:** Open `INTERVIEW_QUESTIONS.docx` and fill in your answers
2. **Review Plan:** Read `AUTOMATION_PLAN.md` for detailed implementation strategy
3. **Provide Feedback:** Any concerns or additional requirements

## 📋 Key Documents

### [AUTOMATION_PLAN.md](AUTOMATION_PLAN.md)
Comprehensive 20+ page implementation plan covering:
- Architecture options (Airflow, Local Script, Cloud Functions)
- Technical components (Slack API, Looker integration, Papermill)
- 3-phase implementation timeline
- Risk assessment and mitigation
- Cost estimates ($0-1/month)
- Monitoring and alerting strategy

### [INTERVIEW_QUESTIONS.docx](INTERVIEW_QUESTIONS.docx)
20 critical questions across 6 categories:
- Slack setup and permissions
- Looker API access and authentication
- Notebook details and parameters
- Message format and bot behavior
- Error handling preferences
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

**Status:** 📋 Planning - Awaiting interview question responses

**Next Action:** Fill out `INTERVIEW_QUESTIONS.docx` and provide answers
