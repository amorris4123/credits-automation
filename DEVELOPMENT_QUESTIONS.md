# Development Questions & Issues

Questions and considerations that arose during prototype development.

**Status:** Draft - Please review and provide answers
**Date:** 2026-01-08

---

## 🤔 Questions for User

### 1. Notebook Parameter Cell

**Question:** Does the notebook already have a parameters cell tagged for papermill?

**Context:** Papermill needs a cell tagged as "parameters" to inject values. The cell should look like:

```python
# Parameters
looker = ""
```

**Action Needed:**
- [ ] Verify notebook has parameters cell
- [ ] If not, add one and tag it (Edit → Cell Toolbar → Tags → add "parameters" tag)

---

### 2. Looker URL Format

**Question:** What format do Looker URLs typically have in Slack messages?

**Context:** I built support for:
- Full Look URLs: `https://twilio.cloud.looker.com/looks/12345`
- Short links: `https://twilio.cloud.looker.com/x/abc123` (noted as not yet supported)

**Observed Formats:**
- URLs embedded in formatted text: `<https://looker.com/looks/123|$179.73>`

**Action Needed:**
- [ ] Test with real Looker link from Slack
- [ ] Confirm URL extraction works correctly
- [ ] Let me know if short links are commonly used (need additional implementation)

---

### 3. Credit Amount Extraction

**Question:** How exactly does the notebook output `credit_amount`?

**Context:** I implemented several strategies to find credit_amount:
1. Look for cells with `credit_amount =` in source
2. Check cell outputs for the value
3. Look at the last cell's output

**Possible Formats:**
- Just the number: `179.73`
- With dollar sign: `$179.73`
- As string: `"179.73"`
- In a sentence: "Credit amount is 179.73"

**Action Needed:**
- [ ] Test extraction with real notebook output
- [ ] Provide example of how credit_amount appears in output
- [ ] May need to adjust extraction logic

---

### 4. Verify Product Detection

**Question:** Is checking for "Authy" sufficient to identify Verify queries?

**Context:** Current implementation checks if SQL contains:
- "authy" (case-insensitive)
- "billable_item_metadata_alex.product"
- "billable_items.friendly_name"
- "verify"
- "verification"

**Concern:** Might have false positives or miss some Verify queries.

**Action Needed:**
- [ ] Test with real Verify and PSMS queries
- [ ] Confirm detection logic works correctly
- [ ] Provide examples of edge cases if any

---

### 5. Error DM Recipient

**Question:** Should error DMs go to you specifically, or to multiple people?

**Context:** Currently configured to send to `SLACK_USER_ID` in .env (just one person).

**Options:**
1. Single recipient (you)
2. Multiple recipients
3. Post errors to a specific error channel
4. Both DM and channel

**Action Needed:**
- [ ] Confirm single DM is sufficient
- [ ] Or provide list of user IDs if multiple recipients needed

---

### 6. Dry Run Visibility

**Question:** In dry-run mode, where should we show what the bot WOULD do?

**Current Implementation:**
- Logs to console and log file
- Shows: "DRY RUN Would post: ..."

**Alternative Options:**
1. Create a #credit_memo_testing_dry_run channel
2. Post dry-run results to test channel with [DRY RUN] prefix
3. Generate a summary report file
4. Just logs (current)

**Action Needed:**
- [ ] Is logging sufficient, or want Slack visibility?

---

### 7. Looker API Access

**Question:** Do the Looker API credentials have access to all necessary Looks?

**Context:** The bot needs to:
1. Authenticate with Looker API
2. Fetch Look details by ID
3. Extract SQL query from Look

**Potential Issues:**
- Some Looks might be private/restricted
- API might have rate limits
- Need to handle authentication expiry

**Action Needed:**
- [ ] Test with actual Looker URLs from Slack
- [ ] Confirm API access works for production Looks
- [ ] Note any permission issues

---

### 8. State Management

**Question:** How long should we keep processing history?

**Current Implementation:**
- Keeps last 1000 processed messages
- Stores message timestamps to avoid reprocessing

**Considerations:**
- Prevents duplicate processing
- File grows over time
- Cleanup happens automatically at 1000 entries

**Action Needed:**
- [ ] Is 1000 messages sufficient? (at 5/day = 200 days)
- [ ] Or prefer different retention period?

---

### 9. Multiple Looker Links

**Question:** What if a message has multiple Looker links?

**Current Behavior:** Uses the first Looker link found

**Scenarios:**
1. Message has 2+ Looker links
2. Message has Looker link + Zendesk link
3. Message has Looker link in different locations

**Action Needed:**
- [ ] Confirm first-link behavior is correct
- [ ] Or should we process all links?
- [ ] How to handle multiple results?

---

### 10. Notebook Kernel

**Question:** Which Python kernel should the notebook use?

**Current Setting:** `python3`

**Context:** If you use a specific conda environment or virtual environment, might need to specify different kernel.

**Action Needed:**
- [ ] Verify `python3` kernel is correct
- [ ] If custom kernel needed, provide kernel name
- [ ] Check: `jupyter kernelspec list`

---

## 🚧 Known Limitations

### 1. Short Looker Links Not Supported (Yet)

Links like `https://twilio.cloud.looker.com/x/abc123` need additional API call to resolve. Can add if needed.

### 2. Explore Links Not Supported (Yet)

Currently only supports Look links. Explore links have different URL structure. Can add if needed.

### 3. Single Channel Only

Bot monitors one channel at a time. Could be extended to multiple channels if needed.

### 4. No Real-Time Monitoring

Bot runs once and exits. Need to schedule it (cron/Airflow) for continuous monitoring.

### 5. No Retry Logic (Yet)

If notebook fails, marks as processed and moves on. Could add retry logic if needed.

---

## 💡 Future Enhancements

### High Priority
1. Add PSMS notebook integration
2. Set up scheduled runs (Airflow DAG)
3. Add desktop alerts for monitoring
4. Better error recovery and retry logic

### Medium Priority
1. Support for Explore links
2. Support for short Looker links
3. Multi-channel support
4. Dashboard for monitoring

### Low Priority
1. Machine learning for credit prediction
2. Historical data analysis
3. Advanced reporting
4. Slack commands (e.g., `/credit status`)

---

## ✅ Resolved During Development

### Slack Link Format
**Resolved:** Slack sends links as `<url|text>` format. Implemented regex to extract URL portion.

### Looker Authentication
**Resolved:** Using OAuth2 with client credentials flow. Access tokens refreshed automatically.

### Notebook Execution Blocking
**Resolved:** Notebook runs in subprocess, doesn't block main thread.

### State Persistence
**Resolved:** Using JSON file for simplicity. Can migrate to database later if needed.

---

## 📝 Testing Checklist

Before going to production, test:

- [ ] Slack connection and message retrieval
- [ ] Looker API authentication
- [ ] Looker URL extraction from real messages
- [ ] SQL extraction from real Looker links
- [ ] Verify vs PSMS detection
- [ ] Notebook execution with real query
- [ ] Credit amount extraction from output
- [ ] Slack posting (dry-run first!)
- [ ] Error DM functionality
- [ ] State file persistence
- [ ] Missing link request message
- [ ] Full end-to-end with test message

---

## 🔍 Code Review Notes

### Architecture Decisions

1. **Modular Design:** Separated concerns into distinct modules (slack, looker, notebook, state)
2. **Configuration:** Environment-based config for flexibility
3. **Logging:** Comprehensive logging for debugging
4. **State Management:** Simple JSON file (can upgrade to DB later)
5. **Error Handling:** DM notifications for failures

### Code Quality

- All modules have docstrings
- Functions have type hints where applicable
- Error handling in all external API calls
- Dry-run mode for safe testing
- Logging at appropriate levels

### Security

- Credentials in .env (not in code)
- .env in .gitignore
- No secrets logged
- API tokens never printed

---

**Next Steps:**

1. Review these questions
2. Provide answers where needed
3. Test the prototype
4. Report any issues or edge cases found
5. Iterate and improve!
