# Credits Automation - Interview Questions

**Purpose:** Answer these questions so we can build the automation correctly.
**Status:** PENDING YOUR ANSWERS
**Date:** 2025-01-08

---

## 🔍 Slack Setup

### 1. Slack Bot Permissions
**Question:** Do you have permissions to create Slack apps/bots for your workspace? Or do you need to request this from IT?

**Your Answer:**


---

### 2. Test Channel Setup
**Question:** For the test channel - do you want me to help set it up, or will you create it and just give me the name?

**Your Answer:**


---

### 3. Bot Identity
**Question:** Should the bot have a name/identity like "Credit Bot" or just post as you?

**Your Answer:**


---

## 🔐 Looker Access

### 4. Looker API Access
**Question:** Can you access Looker's API settings? Go to Admin > Users > API3 Keys in Looker - do you see this option?

**Your Answer:**


---

### 5. Looker Authentication
**Question:** If you open a Looker link from Slack in your browser, are you already logged in (SSO), or do you have to authenticate?

**Your Answer:**


---

### 6. SQL Query Location
**Question:** When you open a Looker link, where exactly is the SQL query displayed? Is it in a specific tab/section, or do you have to click something to see it?

**Your Answer:**


---

## 📓 Notebook Details

### 7. SQL Query Parameter Name
**Question:** In your notebook's "Set Parameters" section - what's the current variable name for the SQL query? Is it just `sql_query` or something else?

**Your Answer:**


---

### 8. Verify vs PSMS Detection
**Question:** How does the notebook currently identify if a request is for Verify vs PSMS? Does it check those column names (`billable_item_metadata_alex.product` and `billable_items.friendly_name`) for "Authy"?

**Your Answer:**


---

### 9. Wrong Product Handling
**Question:** What happens if the notebook runs on a PSMS query by mistake? Does it error out, or give wrong results?

**Your Answer:**


---

### 10. Result Variable Name
**Question:** What's the exact variable name for the final result? You said `credit_amount` - is that the exact variable name in the last cell?

**Your Answer:**


---

## 💬 Slack Message Format

### 11. Looker Link Location
**Question:** Looking at the example post - is the Looker link ALWAYS embedded in the "Fraud spend" line? Or could it appear elsewhere?

**Your Answer:**


---

### 12. Bot Reply Format
**Question:** What should the bot's reply look like?

Options:
- Just the amount: "$179.73"
- With context: "Approved refund amount: $179.73"
- With details: "🤖 Automated calculation: $179.73 (ASID: AC42ca...)"
- Something else?

**Your Answer:**


---

### 13. PSMS Request Handling
**Question:** If it's a PSMS request (not Verify), should the bot:
- Post "This is a PSMS request - requires different processing"
- Just ignore it silently
- Something else?

**Your Answer:**


---

## ⚠️ Error Scenarios

### 14. Notebook Execution Failure
**Question:** If the notebook fails to execute (query error, data issue, etc.), should the bot:
- Post to the Slack thread: "⚠️ Automated processing failed - needs manual review"
- DM you privately about the failure
- Both?
- Just log it?

**Your Answer:**


---

### 15. Missing Looker Link
**Question:** If there's no Looker link found in the post, should the bot ignore it or post a message?

**Your Answer:**


---

## 🚀 Deployment

### 16. Airflow Access
**Question:** Do you have Airflow access? Can you create/deploy new DAGs yourself?

**Your Answer:**


---

### 17. Development Approach
**Question:** If Airflow is too complicated to set up quickly, would you be okay starting with a Python script you run manually first, then moving to Airflow once it's working?

**Your Answer:**


---

### 18. Code Location
**Question:** Where should this code live? Same directory as the notebook? A separate repo? In your existing airflow-dags repo?

**Your Answer:**


---

## 🧪 Testing & Safety

### 19. Test Data
**Question:** For the test channel - should I create fake test posts with real-looking Looker links, or do you have some test data already?

**Your Answer:**


---

### 20. Dry Run Mode
**Question:** Before going live on the real channel, do you want a "dry run" mode where it processes but doesn't post results (just shows you what it WOULD post)?

**Your Answer:**


---

## 📝 Additional Notes

**Any other requirements, concerns, or context you want to share:**




---

## ✅ Next Steps After You Answer

Once you complete this, I will:
1. Update the automation plan based on your answers
2. Build the initial prototype
3. Set up the test environment
4. Create documentation for running/deploying

**Estimated timeline:** 1-2 days after receiving your answers
