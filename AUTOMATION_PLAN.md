# Credit Memo Automation - Implementation Plan

## 📋 Overview

Automate the credit recommendation process for SMS toll fraud cases by monitoring Slack, extracting Looker queries, processing through Jupyter notebook, and posting results back to Slack.

---

## 🎯 Goals

**Current Manual Process:**
1. Monitor #help-sms-credit-pumping-memos for new posts
2. Click Looker link in "Fraud spend" line
3. Copy SQL query from Looker
4. Paste into "Verify - Credit Recommendation.ipynb"
5. Execute notebook
6. Copy credit_amount result
7. Reply to Slack thread with approved refund amount

**Desired Automated Process:**
1. Bot monitors Slack channel continuously
2. Detects new posts → extracts embedded Looker link
3. Fetches SQL query from Looker
4. Executes notebook with query
5. Posts credit_amount to Slack thread automatically

**Volume:** 1-5 requests per day
**User Preference:** Full automation (no manual approval step)

---

## 🏗️ Architecture

### Option A: Airflow DAG (Recommended)
**Pros:**
- You already use Airflow
- Built-in scheduling, retries, logging
- Easy to monitor and debug
- Can reuse existing Airflow infrastructure

**Cons:**
- Minimum 1-minute polling interval (Airflow limitation)
- Requires Airflow access/permissions

**Flow:**
```
Airflow DAG (runs every 1-5 minutes)
  ↓
[Check Slack for new messages]
  ↓
[Extract Looker URL from message]
  ↓
[Fetch SQL from Looker API/scrape]
  ↓
[Execute notebook with papermill]
  ↓
[Extract credit_amount from output]
  ↓
[Post result to Slack thread]
```

### Option B: Local Python Script
**Pros:**
- Simple to set up
- Runs on your machine
- Full control

**Cons:**
- Must be running on your laptop
- No built-in retry/monitoring
- Dies if laptop sleeps/restarts

### Option C: Cloud Function (AWS Lambda / GCP Cloud Function)
**Pros:**
- Serverless (only pay when running)
- Can trigger on Slack events (real-time)
- Always available

**Cons:**
- More complex setup
- Requires cloud account/billing
- Cold start delays

---

## 🔧 Technical Components

### 1. Slack Integration

**Required:**
- Slack API token (Bot or User token)
- Permissions needed:
  - `channels:history` - Read channel messages
  - `chat:write` - Post replies
  - `links:read` - Extract URLs from messages

**API Calls:**
```python
# Get recent messages
conversations.history(channel="help-sms-credit-pumping-memos")

# Post reply to thread
chat.postMessage(channel=channel_id, thread_ts=parent_ts, text=result)
```

**Challenge:** Extracting Looker URL from formatted Slack message
- Slack embeds links as: `<https://looker.url|$179.73>`
- Need to parse this format to get actual URL

### 2. Looker Integration

**Two Approaches:**

#### A. Looker API (Preferred if available)
- Requires: Looker API credentials (client_id, client_secret)
- Can programmatically fetch query from Look/Dashboard
- More reliable than scraping

#### B. Web Scraping (Fallback)
- Use Selenium/Playwright to load Looker page
- Extract SQL from page HTML
- Requires: Browser automation, Looker SSO/auth cookies
- More fragile but works if no API access

**Authentication Challenge:**
- Looker likely uses Okta/SSO
- Need to handle authentication in headless browser OR
- Reuse your existing browser session cookies

### 3. Notebook Execution

**Tool: Papermill**
```bash
pip install papermill
```

**Execution:**
```python
import papermill as pm

pm.execute_notebook(
    'Verify - Credit Recommendation.ipynb',
    'output.ipynb',
    parameters={'sql_query': extracted_query}
)

# Read output notebook to extract credit_amount
import nbformat
nb = nbformat.read('output.ipynb', as_version=4)
# Parse cells to find credit_amount variable
```

**Challenge:** Notebook must be modified to accept parameters
- Add a cell tagged as "parameters"
- Define `sql_query` variable there
- Papermill will inject the actual query

### 4. State Management

**Problem:** How to avoid reprocessing the same Slack messages?

**Solution:** Track processed messages
```python
# Store in simple JSON file or SQLite database
{
    "last_processed_timestamp": "1234567890.123456",
    "processed_message_ids": ["msg1", "msg2", "msg3"]
}
```

**Alternative:** Use Slack reactions
- Bot adds ✅ emoji when processed
- Skip messages that already have ✅
- Visual indicator for humans too

---

## 📝 Implementation Steps

### Phase 1: Setup & Authentication (Week 1)

**Tasks:**
1. ✅ **Slack API Setup**
   - Create Slack app or get bot token
   - Test reading from #help-sms-credit-pumping-memos
   - Test posting replies to threads

2. ✅ **Looker Access Investigation**
   - Check if Looker API is available
   - If yes: Get API credentials
   - If no: Set up Selenium with authentication
   - Test extracting SQL from a sample Looker link

3. ✅ **Notebook Preparation**
   - Modify notebook to accept SQL query as parameter
   - Test papermill execution locally
   - Verify credit_amount can be extracted from output

**Deliverable:** All authentication working, can manually trigger each step

### Phase 2: Core Automation (Week 2)

**Tasks:**
1. ✅ **Build Processing Pipeline**
   ```python
   def process_slack_message(message):
       # 1. Extract Looker URL
       looker_url = extract_looker_url(message['text'])

       # 2. Get SQL from Looker
       sql_query = fetch_sql_from_looker(looker_url)

       # 3. Execute notebook
       output_path = execute_notebook(sql_query)

       # 4. Extract result
       credit_amount = extract_credit_amount(output_path)

       # 5. Post to Slack
       post_result_to_slack(message, credit_amount)
   ```

2. ✅ **State Management**
   - Implement message tracking (JSON or SQLite)
   - Add logic to skip already-processed messages

3. ✅ **Error Handling**
   - Try/except for each step
   - Log errors with context
   - Decide: Should bot post error to Slack or just log?

**Deliverable:** Working end-to-end script that can process one message

### Phase 3: Scheduling & Monitoring (Week 3)

**Tasks:**
1. ✅ **Deploy to Airflow** (if chosen)
   - Create DAG definition
   - Set schedule interval (recommend: 2-5 minutes)
   - Configure alerts for failures

2. ✅ **Add Desktop Alerts** (bonus!)
   - Use your notebook_auto_alert system!
   - Alert when processing succeeds/fails
   - Include ASID and credit amount in alert

3. ✅ **Testing**
   - Test with historical messages
   - Test error cases (invalid Looker link, notebook fails, etc.)
   - Monitor for 1 week before going fully live

**Deliverable:** Production-ready automation

---

## 🚨 Risk Assessment & Mitigation

### High Risk

**1. Looker Authentication Fails**
- **Risk:** Bot can't access Looker links
- **Mitigation:**
  - Test extensively during Phase 1
  - Keep manual process as backup
  - Add fallback: Post message asking human to manually process

**2. Notebook Execution Errors**
- **Risk:** Presto query fails, data issues cause crashes
- **Mitigation:**
  - Extensive error handling in notebook
  - Catch exceptions and post error message to Slack
  - Log all failures for investigation

**3. Wrong Credit Amount Posted**
- **Risk:** Bug causes incorrect refund amount to be posted
- **Mitigation:**
  - Add sanity checks (e.g., credit_amount < fraud_spend)
  - Include debug info in Slack post (ASID, fraud spend, etc.)
  - Monitor first 10-20 automated posts closely

### Medium Risk

**4. Slack Rate Limits**
- **Risk:** Too many API calls, get throttled
- **Mitigation:**
  - Only check once per 2-5 minutes
  - Cache message history

**5. Duplicate Processing**
- **Risk:** Same message processed twice
- **Mitigation:**
  - Robust state tracking
  - Use message timestamps/IDs as unique keys

---

## 📊 Monitoring & Alerting

**What to Track:**
1. Number of messages processed (daily)
2. Success vs failure rate
3. Average processing time
4. Looker fetch failures
5. Notebook execution failures

**Alerts:**
- Airflow email on DAG failure (if using Airflow)
- Desktop alert for each processing (success/failure)
- Slack DM to you on errors (optional)

**Dashboard (Optional):**
- Simple metrics: processed today, success rate, last run time
- Could build small Streamlit dashboard if desired

---

## 💰 Cost Estimate

**Scenario: Airflow Deployment (Recommended)**
- Infrastructure: $0 (using existing Airflow)
- Slack API: Free (standard workspace)
- Looker API: Free (using existing access)
- Papermill: Free (open source)
- **Total: $0/month**

**Scenario: Cloud Function**
- AWS Lambda: ~$0.20/month (1M free requests)
- Slack API: Free
- Storage: < $0.01/month
- **Total: < $1/month**

---

## 🔐 Security Considerations

1. **API Tokens:** Store in environment variables or secrets manager (NOT in code)
2. **Looker Auth:** Use service account if possible (not personal credentials)
3. **Slack Permissions:** Minimal scope (only what's needed)
4. **Audit Trail:** Log all processing with timestamps
5. **Rate Limiting:** Don't overwhelm APIs

---

## 📋 Requirements Checklist

### Must-Have
- [ ] Slack API access to #help-sms-credit-pumping-memos
- [ ] Looker authentication method determined
- [ ] Notebook modified to accept parameters
- [ ] Papermill working locally
- [ ] Can extract credit_amount from notebook output
- [ ] Can post to Slack threads

### Nice-to-Have
- [ ] Desktop alerts for monitoring
- [ ] Metrics dashboard
- [ ] Slack emoji reactions for status
- [ ] Dry-run mode for testing

---

## 🎬 Next Steps

### Immediate Actions (You Need to Answer):

1. **Slack API Access:**
   - Do you have admin rights to create a Slack app?
   - Or do you need to request a bot token from IT?

2. **Looker Authentication:**
   - Can you check if Looker has an API we can use?
   - Or should we plan for web scraping with Selenium?

3. **Deployment Preference:**
   - Do you have access to deploy Airflow DAGs?
   - Or should we start with a local Python script?

4. **Notebook Location:**
   - Is the notebook in a git repo?
   - Where should the automation code live?

### What I'll Build (After Your Answers):

1. **Phase 1 Prototype:** Script that does steps 1-5 manually triggered
2. **Phase 2 Integration:** Add Slack monitoring + auto-posting
3. **Phase 3 Production:** Deploy to Airflow/schedule + monitoring

---

## 🤔 Open Questions

1. **What should happen if the notebook determines credit_amount = $0?**
   - Still post to Slack?
   - Different message format?

2. **What if multiple Looker links appear in one message?**
   - Process all of them?
   - Take the first one?

3. **Should the bot identify itself when posting?**
   - e.g., "🤖 Automated Credit Calculation: $179.73"
   - Or just post the number?

4. **Error handling - what should bot post if something fails?**
   - "⚠️ Automated processing failed. Please review manually."
   - Or just log silently?

5. **How long should we keep the processing history?**
   - 30 days? 90 days? Forever?

---

## 🚀 Success Metrics

After 30 days of automation:
- ✅ 95%+ of messages processed automatically
- ✅ Zero incorrect credit amounts posted
- ✅ Average processing time < 2 minutes
- ✅ You save ~15-30 minutes per day

---

## 📚 Technology Stack (Proposed)

```
Python 3.9+
├── slack-sdk (Slack API client)
├── papermill (Notebook execution)
├── nbformat (Parse notebook output)
├── selenium / playwright (Looker scraping if needed)
├── presto-python-client (if direct DB access)
├── pandas (data processing)
└── requests (HTTP calls)

Deployment:
├── Airflow (DAG scheduling) [Recommended]
└── OR systemd/cron (local scheduling)

Storage:
└── SQLite or JSON (state tracking)
```

---

## 📞 Support & Maintenance

**Ongoing Requirements:**
- Monitor logs weekly
- Update if Slack/Looker changes API/UI
- Adjust notebook if business logic changes
- Keep dependencies updated

**Expected Time Investment:**
- Build: 15-20 hours (over 2-3 weeks)
- Maintenance: 1-2 hours/month

---

**Created:** 2025-01-05
**Author:** Claude Code
**Status:** DRAFT - Awaiting user input on open questions
