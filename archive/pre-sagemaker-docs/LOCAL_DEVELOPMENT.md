# CreditBot Local Development Guide

**Guide for developing and testing CreditBot on your local machine**

---

## Table of Contents

1. [Overview](#overview)
2. [Initial Setup](#initial-setup)
3. [Local Execution](#local-execution)
4. [Testing Changes](#testing-changes)
5. [Docker Testing](#docker-testing)
6. [Debugging](#debugging)
7. [Development Workflow](#development-workflow)

---

## Overview

This guide covers running CreditBot locally for development and testing. The local environment mimics production but uses:

- Local file storage instead of S3
- Environment variables from `.env` file instead of AWS Secrets Manager
- Local state file instead of S3-backed state

---

## Initial Setup

### Prerequisites

Required software:

```bash
# Check versions
python3 --version  # Python 3.9+
docker --version   # Docker 20.10+ (optional for container testing)
git --version      # Git 2.x+
```

Installation:
- **Python 3.9+**: https://www.python.org/downloads/ or `brew install python@3.9`
- **Docker Desktop**: https://www.docker.com/products/docker-desktop (optional)
- **Git**: `brew install git` or https://git-scm.com/

### Clone Repository

```bash
# Clone from GitHub
git clone git@github.com:twilio-internal/credits-automation.git
cd credits-automation
```

### Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate (macOS/Linux)
source venv/bin/activate

# Activate (Windows)
# venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

### Install Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt

# Verify installation
python3 -c "import slack_sdk, looker_sdk, papermill; print('✓ All imports successful')"
```

### Configure Environment Variables

Create `.env` file with your credentials:

```bash
# Copy template
cp .env.example .env

# Edit with your editor
nano .env  # or vim, code, etc.
```

Required variables in `.env`:

```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token-here
SLACK_USER_ID=U01234567  # Your Slack user ID for DMs
SLACK_CHANNEL_ID=C01234567  # #help-sms-credit-pumping-memos channel ID

# Looker Configuration
LOOKER_BASE_URL=https://twilio.looker.com
LOOKER_CLIENT_ID=your-looker-client-id
LOOKER_CLIENT_SECRET=your-looker-client-secret

# Presto Configuration
PRESTO_HOST=presto.internal.twilio.com
PRESTO_PORT=8080
PRESTO_USERNAME=your-username
PRESTO_PASSWORD=your-password
PRESTO_CATALOG=hive
PRESTO_SCHEMA=default

# Local Development Settings
STATE_FILE=data/processed_messages.json
OUTPUT_DIR=data/outputs
LOG_LEVEL=DEBUG  # Use DEBUG for development, INFO for production
```

**Important**: Never commit `.env` file to Git!

### Verify Setup

Test that everything is configured:

```bash
# Test Slack connection
python3 -c "
from src.config import Config
from src.slack_client import SlackClient
client = SlackClient(Config.SLACK_BOT_TOKEN)
print('✓ Slack connection successful')
"

# Test Looker connection
python3 -c "
from src.looker_client import LookerClient
from src.config import Config
client = LookerClient(Config.LOOKER_BASE_URL, Config.LOOKER_CLIENT_ID, Config.LOOKER_CLIENT_SECRET)
print('✓ Looker connection successful')
"
```

---

## Local Execution

### Running the Bot

```bash
# Activate virtual environment
source venv/bin/activate

# Run bot once
python3 run_bot.py
```

Expected output:

```
🤖 Starting CreditBot...
📁 Execution environment: local
📂 State file: data/processed_messages.json
📊 Loaded state: 15 processed messages
🔍 Checking Slack channel for new messages...
✅ Found 2 new messages to process
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📬 Processing message 1/2...
🔗 Looker URL: https://twilio.looker.com/looks/12345
📊 Extracted SQL query
📓 Executing notebook...
✅ Credit amount: $1,234.56
💬 Posted result to Slack thread
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📬 Processing message 2/2...
...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Bot execution completed successfully
   Processed: 2 messages
   Errors: 0
   Duration: 45.2 seconds
```

### Running in a Loop

For continuous monitoring (like production):

```bash
# Run every 15 minutes
while true; do
  python3 run_bot.py
  echo "Sleeping for 15 minutes..."
  sleep 900  # 15 minutes
done
```

Or use `watch` command:

```bash
# Run every 15 minutes (900 seconds)
watch -n 900 python3 run_bot.py
```

### Stopping Execution

```bash
# Press Ctrl+C to stop
# The bot will handle signals gracefully and save state
```

---

## Testing Changes

### Testing Individual Components

Test Slack integration:

```bash
# Test fetching messages
python3 -c "
from src.slack_client import SlackClient
from src.config import Config
client = SlackClient(Config.SLACK_BOT_TOKEN)
messages = client.get_channel_history(Config.SLACK_CHANNEL_ID, limit=5)
print(f'Fetched {len(messages)} messages')
for msg in messages:
    print(f'  - {msg.get(\"text\", \"\")[:50]}...')
"

# Test posting message
python3 -c "
from src.slack_client import SlackClient
from src.config import Config
client = SlackClient(Config.SLACK_BOT_TOKEN)
client.post_message('Test message from CreditBot', channel=Config.SLACK_USER_ID)
print('✓ Message sent to your DMs')
"
```

Test Looker integration:

```bash
# Test extracting SQL from a Looker URL
python3 -c "
from src.looker_client import LookerClient
from src.config import Config
client = LookerClient(Config.LOOKER_BASE_URL, Config.LOOKER_CLIENT_ID, Config.LOOKER_CLIENT_SECRET)
sql = client.get_look_sql('12345')  # Replace with actual Look ID
print(f'Extracted SQL ({len(sql)} chars):\n{sql[:200]}...')
"
```

Test notebook execution:

```bash
# Test with sample SQL query
python3 -c "
from src.notebook_executor import NotebookExecutor
executor = NotebookExecutor('Verify - Credit Recommendation.ipynb')
sql_query = 'SELECT 1 as test'
result = executor.execute_notebook(sql_query)
print(f'Credit amount: ${result[\"credit_amount\"]:,.2f}')
"
```

### Testing State Management

```bash
# Check current state
python3 -c "
from src.state_manager import StateManager
state = StateManager()
print(f'Processed messages: {len(state.get_processed_messages())}')
print(f'Last message: {state.get_last_processed_timestamp()}')
"

# Add test message ID
python3 -c "
from src.state_manager import StateManager
state = StateManager()
state.mark_as_processed('TEST123456', 'test message')
print('✓ Added test message to state')
"

# Check if message is processed
python3 -c "
from src.state_manager import StateManager
state = StateManager()
is_processed = state.is_processed('TEST123456')
print(f'Message TEST123456 processed: {is_processed}')
"
```

### Running Unit Tests

If unit tests exist:

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_slack_client.py

# Run with coverage
pytest --cov=src tests/
```

---

## Docker Testing

Test the Docker image locally before deploying:

### Build Image

```bash
# Build image
docker build -t credit-bot:test .

# Verify image size
docker images credit-bot:test
```

### Run Container Locally

```bash
# Run with .env file
docker run --rm --env-file .env credit-bot:test

# Run interactively (for debugging)
docker run --rm -it --env-file .env credit-bot:test /bin/bash

# Inside container, test imports
python3 -c "import slack_sdk, looker_sdk, papermill; print('OK')"
```

### Test with Volume Mounts

Mount local directories for easier debugging:

```bash
# Mount data directory (for state and outputs)
docker run --rm \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  credit-bot:test

# Mount source code (for live code changes)
docker run --rm \
  --env-file .env \
  -v $(pwd)/src:/app/src \
  -v $(pwd)/data:/app/data \
  credit-bot:test
```

### Inspect Running Container

```bash
# Run container in background
docker run -d --name credit-bot-debug --env-file .env credit-bot:test sleep infinity

# Execute commands inside
docker exec credit-bot-debug python3 --version
docker exec credit-bot-debug ls -la /app/

# View logs
docker logs credit-bot-debug

# Stop and remove
docker stop credit-bot-debug
docker rm credit-bot-debug
```

---

## Debugging

### Enable Debug Logging

Set `LOG_LEVEL=DEBUG` in `.env`:

```bash
LOG_LEVEL=DEBUG
```

Run bot to see detailed logs:

```bash
python3 run_bot.py
```

Output will include:

```
DEBUG - Slack API request: conversations.history
DEBUG - Received 25 messages from channel
DEBUG - Checking message ts=1234567890.123456
DEBUG - Message already processed, skipping
DEBUG - Looker API: Fetching Look 12345
DEBUG - SQL query extracted (1234 characters)
DEBUG - Executing notebook with papermill...
DEBUG - Presto query started
DEBUG - Presto query completed in 3.2s
...
```

### Interactive Python Shell

Use IPython for interactive debugging:

```bash
# Install IPython
pip install ipython

# Start interactive shell
ipython

# Import and test
from src.credit_bot import CreditBot
from src.config import Config
bot = CreditBot(Config.SLACK_BOT_TOKEN, Config.SLACK_USER_ID)
messages = bot.slack_client.get_channel_history(Config.SLACK_CHANNEL_ID, limit=5)
messages
```

### Debugging Notebook Execution

Run notebook manually with papermill:

```bash
# Execute notebook with test SQL
papermill "Verify - Credit Recommendation.ipynb" /tmp/output.ipynb \
  -p sql_query "SELECT 'test' as account_sid, 100.50 as billed_amount"

# Open output notebook to see results
open /tmp/output.ipynb  # macOS
# or use Jupyter: jupyter notebook /tmp/output.ipynb
```

Check for notebook errors:

```bash
# Look for error cells in output
jupyter nbconvert --to script /tmp/output.ipynb
cat /tmp/output.txt | grep -A5 "ERROR"
```

### Using Python Debugger

Add breakpoint in code:

```python
# In src/credit_bot.py or any file
import pdb; pdb.set_trace()  # Breakpoint

# Or use breakpoint() in Python 3.7+
breakpoint()
```

Run bot and debugger will pause:

```bash
python3 run_bot.py

# Debugger commands:
# n - next line
# s - step into function
# c - continue execution
# p variable_name - print variable
# l - list source code
# q - quit debugger
```

### Common Issues

#### Import Errors

```bash
# Issue: ModuleNotFoundError: No module named 'slack_sdk'
# Fix: Ensure virtual environment is activated and dependencies installed
source venv/bin/activate
pip install -r requirements.txt
```

#### Connection Errors

```bash
# Issue: slack_sdk.errors.SlackApiError: The request to the Slack API failed
# Fix: Check SLACK_BOT_TOKEN in .env file

# Issue: looker_sdk.error.SDKError: Unauthorized
# Fix: Check LOOKER_CLIENT_ID and LOOKER_CLIENT_SECRET

# Issue: prestodb.exceptions.OperationalError: Cannot connect to Presto
# Fix: Check PRESTO_HOST, PRESTO_PORT, and network connectivity
```

#### Notebook Execution Errors

```bash
# Issue: papermill.exceptions.PapermillExecutionError
# Fix: Run notebook manually to see full error
papermill "Verify - Credit Recommendation.ipynb" /tmp/debug_output.ipynb -p sql_query "..."

# Check notebook for SQL errors or missing dependencies
```

---

## Development Workflow

### Feature Development

1. **Create feature branch**
   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Make code changes**
   ```bash
   # Edit files in src/
   code src/credit_bot.py
   ```

3. **Test locally**
   ```bash
   python3 run_bot.py
   # Or test specific component
   python3 -c "from src.credit_bot import CreditBot; ..."
   ```

4. **Test with Docker**
   ```bash
   docker build -t credit-bot:test .
   docker run --rm --env-file .env credit-bot:test
   ```

5. **Commit changes**
   ```bash
   git add src/credit_bot.py
   git commit -m "Add new feature for XYZ"
   ```

6. **Push and create PR**
   ```bash
   git push origin feature/my-new-feature
   # Create PR on GitHub
   ```

### Bug Fixes

1. **Reproduce bug locally**
   ```bash
   # Use DEBUG logging
   LOG_LEVEL=DEBUG python3 run_bot.py
   ```

2. **Add test case** (if applicable)
   ```python
   # In tests/test_credit_bot.py
   def test_bug_xyz():
       # Test that reproduces bug
       ...
   ```

3. **Fix bug**
   ```bash
   # Edit code
   code src/credit_bot.py
   ```

4. **Verify fix**
   ```bash
   # Run tests
   pytest tests/test_credit_bot.py::test_bug_xyz

   # Run full bot
   python3 run_bot.py
   ```

5. **Deploy** (see AIRFLOW_DEPLOYMENT.md)

### Testing Against Test Slack Channel

Create a test Slack channel for development:

1. Create `#credit-bot-testing` channel
2. Invite bot to test channel
3. Post test messages with Looker URLs
4. Update `.env` temporarily:
   ```bash
   SLACK_CHANNEL_ID=C_TEST_CHANNEL_ID  # Test channel
   ```
5. Run bot against test channel:
   ```bash
   python3 run_bot.py
   ```

### Simulating Production Environment

Test as close to production as possible:

```bash
# Use production-like settings in .env
LOG_LEVEL=INFO
STATE_FILE=data/processed_messages.json
OUTPUT_DIR=data/outputs

# Run in loop like production
while true; do
  python3 run_bot.py
  sleep 900
done

# Monitor state file growth
watch -n 10 'cat data/processed_messages.json | jq ".processed_messages | length"'
```

### Before Deploying to Production

Checklist:

- [ ] All tests pass locally
- [ ] Docker image builds successfully
- [ ] Docker container runs without errors
- [ ] Tested against test Slack channel
- [ ] Reviewed code changes
- [ ] Updated documentation (if needed)
- [ ] Version bumped (if applicable)
- [ ] PR approved and merged
- [ ] Ready to deploy via `deploy.sh`

---

## Code Style and Best Practices

### Python Style

Follow PEP 8:

```bash
# Install linters
pip install flake8 black isort

# Format code
black src/
isort src/

# Lint code
flake8 src/
```

### Logging

Use structured logging:

```python
import logging
logger = logging.getLogger(__name__)

# Good
logger.info("Processing message", extra={"message_id": msg_id})

# Bad
print(f"Processing {msg_id}")
```

### Error Handling

Always handle exceptions:

```python
# Good
try:
    result = risky_operation()
except SpecificException as e:
    logger.error(f"Operation failed: {e}")
    # Handle or re-raise

# Bad
result = risky_operation()  # Unhandled exception
```

### Configuration

Use Config class, not hardcoded values:

```python
# Good
from src.config import Config
slack_token = Config.SLACK_BOT_TOKEN

# Bad
slack_token = "xoxb-hardcoded-token"
```

---

## Additional Resources

- **Production Deployment**: [AIRFLOW_DEPLOYMENT.md](AIRFLOW_DEPLOYMENT.md)
- **Operations Guide**: [RUNBOOK.md](RUNBOOK.md)
- **Setup Guide**: [SETUP_GUIDE.md](SETUP_GUIDE.md)
- **Project README**: [README.md](README.md)
- **GitHub Repository**: https://github.com/twilio-internal/credits-automation

---

## Support

For questions or issues:

- **GitHub Issues**: https://github.com/twilio-internal/credits-automation/issues
- **Team Slack**: #accsec-ai
- **Email**: team_accsec-ai@twilio.com

---

**Last Updated**: 2026-01-14
**Version**: 1.0
