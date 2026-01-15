# Credits Automation - SageMaker Integration Plan

## Overview
Migrate the credit calculation notebook execution from local Papermill execution to AWS SageMaker Processing Jobs with direct Presto database access using service account credentials.

## Background

### Current Architecture
- Bot runs every 15 minutes via Airflow MWAA on AWS
- Monitors Slack `#credit_memo_testing` channel for new messages
- Extracts Looker URLs → fetches SQL queries from Looker API
- Executes `Verify - Credit Recommendation.ipynb` locally using Papermill
- Posts credit amount to Slack thread
- Stores summary JSON (~50KB) to S3 for audit

### Current Notebook Behavior
The notebook (`Verify - Credit Recommendation.ipynb`):
1. Accepts `looker` parameter containing SQL query
2. Connects to Presto using credentials from `.env` file
3. Executes multiple Presto queries to gather:
   - MCC codes, FraudGuard settings, parent account info, MRR, provider costs, blocking rates
4. Calculates credit amounts based on FraudGuard configuration and block rates
5. Outputs `credit_amount` variable and `output_df` dataframe with results

### Current Limitations
- Hardcoded paths: `/Users/amorris/Documents/sms-pumping`
- Credentials stored in local `.env` file
- Notebook runs on bot's local environment (limited scalability)

## New Architecture

### Changes
1. **Presto Access**: Service account credentials stored in AWS Secrets Manager
2. **Execution Environment**: SageMaker Processing Jobs (replaces local Papermill)
3. **Notebook Modifications**: Read credentials from Secrets Manager, write JSON output to S3
4. **Bot Integration**: New `SageMakerNotebookExecutor` class to trigger jobs and retrieve results

### Workflow
```
Slack Message → Bot extracts SQL from Looker
  ↓
Bot triggers SageMaker Processing Job with SQL parameter
  ↓
SageMaker runs containerized Papermill execution
  ↓
Notebook reads Presto credentials from Secrets Manager
  ↓
Notebook executes SQL queries and calculations
  ↓
Notebook writes results JSON to S3 (predictable path)
  ↓
Bot waits for job completion
  ↓
Bot reads results from S3
  ↓
Bot posts credit amount to Slack thread
```

## Implementation Plan

### Phase 1: Notebook Modifications

**File**: `Verify - Credit Recommendation.ipynb`

**Changes Required**:

1. **Remove hardcoded paths** (Cell 1)
   - Remove: `os.chdir('/Users/amorris/Documents/sms-pumping')`
   - Make all paths relative or use environment variables

2. **Update Presto connection logic** (Cell 2)
   - Replace `.env` file loading with AWS Secrets Manager integration
   - Add function to retrieve credentials from Secrets Manager
   - Use boto3 to fetch secret `presto-service-account-credentials` (or user-specified name)
   - Secret format: `{"host": "...", "port": ..., "username": "...", "password": "..."}`

3. **Add output JSON generation** (New cell at end)
   - After `credit_amount` calculation, create structured output
   - Write JSON to S3 at path: `s3://{BUCKET}/credits-automation/outputs/{execution_id}/result.json`
   - Output format:
   ```json
   {
     "credit_amount": 4948.80,
     "account_sid": "ACXXX...",
     "fraud_start": "2025-07-01",
     "fraud_end": "2025-09-30",
     "fraud_total": 9218.18,
     "mrr": 3,
     "execution_id": "20260115_123456",
     "timestamp": "2026-01-15T12:34:56Z",
     "output_df": [...],  # Credit breakdown by mode
     "summary": {...}     # Key metrics
   }
   ```

4. **Add parameter cell validation**
   - Ensure `looker` parameter is provided and non-empty
   - Add error handling for failed Presto connections

**Critical Files to Modify**:
- `Verify - Credit Recommendation.ipynb`

---

### Phase 2: Docker Container for SageMaker

**New Directory**: `sagemaker/`

**Files to Create**:

1. **`sagemaker/Dockerfile`**
   - Base: `python:3.11-slim` or `jupyter/minimal-notebook`
   - Install dependencies:
     - `papermill`, `nbformat`, `nbconvert`
     - `prestodb`, `pandas`, `numpy`, `scipy`
     - `boto3` (AWS SDK)
     - `matplotlib`, `looker_sdk` (if needed by notebook)
   - Copy notebook into container at `/opt/notebook/`
   - Set entrypoint script to execute Papermill

2. **`sagemaker/requirements.txt`**
   - Pin all dependencies with versions matching notebook environment
   - Include: `papermill>=2.5.0`, `prestodb>=0.8.0`, `boto3>=1.26.0`, `pandas>=2.1.0`, etc.

3. **`sagemaker/entrypoint.sh`**
   - Script to:
     - Accept parameters: `LOOKER_QUERY`, `EXECUTION_ID`, `S3_OUTPUT_BUCKET`
     - Run Papermill with parameters
     - Handle notebook execution errors
     - Upload result JSON to S3
     - Exit with appropriate codes

4. **`sagemaker/build_and_push.sh`**
   - Script to:
     - Build Docker image
     - Tag with version
     - Push to ECR repository: `applied-data-science-prod-twilio/credits-automation-notebook`
     - Output image URI

**Example Dockerfile structure**:
```dockerfile
FROM python:3.11-slim

WORKDIR /opt/notebook

# Install system dependencies
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy notebook
COPY "Verify - Credit Recommendation.ipynb" .

# Copy entrypoint script
COPY entrypoint.sh /opt/entrypoint.sh
RUN chmod +x /opt/entrypoint.sh

ENTRYPOINT ["/opt/entrypoint.sh"]
```

---

### Phase 3: SageMaker Integration in Bot

**New File**: `src/sagemaker_executor.py`

**Purpose**: Replace `notebook_executor.py` with SageMaker-based execution

**Key Methods**:

1. **`__init__(self)`**
   - Initialize boto3 SageMaker client
   - Load configuration: ECR image URI, IAM role, S3 bucket, instance type

2. **`execute(self, looker_query: str, asid: str = None) -> Dict`**
   - Generate unique `execution_id` (timestamp-based)
   - Define S3 output path
   - Create SageMaker Processing Job with:
     - Job name: `credits-automation-{execution_id}`
     - Image URI: ECR image
     - Instance type: `ml.m5.xlarge` (can be configurable)
     - Instance count: 1
     - Volume size: 30 GB
     - Max runtime: 30 minutes (configurable)
     - Role ARN: SageMaker execution role with Secrets Manager + S3 permissions
     - Environment variables: `LOOKER_QUERY`, `EXECUTION_ID`, `S3_OUTPUT_BUCKET`, `SECRET_NAME`
   - Return job ARN and execution_id

3. **`wait_for_completion(self, job_name: str, timeout: int = 1800) -> Dict`**
   - Poll SageMaker job status every 30 seconds
   - Handle states: `InProgress`, `Completed`, `Failed`, `Stopped`
   - Return final status

4. **`get_results(self, execution_id: str) -> Dict`**
   - Read `s3://{BUCKET}/credits-automation/outputs/{execution_id}/result.json`
   - Parse JSON and return credit_amount
   - Handle missing file errors

5. **`is_verify_query(self, sql_query: str) -> bool`**
   - Keep existing logic from `notebook_executor.py` (checks for "Authy")

**Error Handling**:
- Job timeout → Send DM to Slack user
- Job failure → Extract CloudWatch logs, send DM with error
- Missing output JSON → Treat as execution failure

**Configuration** (in `config.py`):
```python
# SageMaker settings
SAGEMAKER_IMAGE_URI = os.getenv('SAGEMAKER_IMAGE_URI', 'aws-account.dkr.ecr.us-east-1.amazonaws.com/credits-automation-notebook:latest')
SAGEMAKER_ROLE_ARN = os.getenv('SAGEMAKER_ROLE_ARN', 'arn:aws:iam::...:role/SageMakerExecutionRole')
SAGEMAKER_INSTANCE_TYPE = os.getenv('SAGEMAKER_INSTANCE_TYPE', 'ml.m5.xlarge')
SAGEMAKER_MAX_RUNTIME = int(os.getenv('SAGEMAKER_MAX_RUNTIME', '1800'))  # 30 minutes
PRESTO_SECRET_NAME = os.getenv('PRESTO_SECRET_NAME', 'presto-service-account-credentials')
```

---

### Phase 4: Bot Workflow Updates

**File**: `src/credit_bot.py`

**Changes**:

1. **Import update** (Line 14)
   - Replace: `from .notebook_executor import NotebookExecutor`
   - With: `from .sagemaker_executor import SageMakerExecutor`

2. **Initialization** (Line 44)
   - Replace: `self.executor = NotebookExecutor()`
   - With: `self.executor = SageMakerExecutor()`

3. **Processing logic** (Lines 165-184)
   - Current: Synchronous notebook execution with `self.executor.execute(sql_query)`
   - New:
     - Trigger SageMaker job: `job_info = self.executor.execute(sql_query, asid)`
     - Wait for completion: `status = self.executor.wait_for_completion(job_info['job_name'])`
     - Get results: `results = self.executor.get_results(job_info['execution_id'])`
     - Extract credit_amount: `credit_amount = results['credit_amount']`

4. **Error handling** (Lines 169-173)
   - Add specific handling for SageMaker failures (timeout, execution error, missing output)
   - Include job ARN in error messages for debugging

**No changes needed**:
- Slack integration
- Looker integration
- State management
- Message parsing

---

### Phase 5: IAM Permissions & AWS Setup

**Resources to Configure**:

1. **AWS Secrets Manager Secret**
   - Name: `presto-service-account-credentials`
   - Content:
   ```json
   {
     "host": "presto.twilio.com",
     "port": 443,
     "username": "svc-credits-automation",
     "password": "..."
   }
   ```

2. **IAM Role for SageMaker** (ARN to use in processing jobs)
   - Name: `SageMakerCreditsAutomationRole`
   - Trust policy: Allow SageMaker service
   - Permissions:
     - `SecretsManagerReadWrite` → Read Presto credentials
     - `S3FullAccess` (scoped to bucket) → Write output JSON
     - `CloudWatchLogsFullAccess` → Write execution logs

3. **IAM Role/Policy for Bot** (running in Kubernetes via Airflow)
   - Additional permissions needed:
     - `sagemaker:CreateProcessingJob`
     - `sagemaker:DescribeProcessingJob`
     - `sagemaker:StopProcessingJob`
     - `sagemaker:ListProcessingJobs`
     - `iam:PassRole` → Pass SageMaker execution role

4. **ECR Repository**
   - Name: `credits-automation-notebook`
   - Policy: Allow pull from SageMaker service

5. **S3 Bucket Structure**
   ```
   s3://{bucket}/credits-automation/
     ├── outputs/
     │   └── {execution_id}/
     │       ├── result.json         # Output from notebook
     │       └── notebook_output.ipynb  # Full executed notebook (optional)
     └── state/
         └── processed_messages.json  # Existing state file
   ```

---

### Phase 6: Testing & Validation

**Testing Steps**:

1. **Local Docker Testing**
   - Build container locally
   - Run with test SQL query
   - Verify JSON output format
   - Verify Secrets Manager access

2. **SageMaker Processing Job Test**
   - Manually trigger job via AWS Console or boto3 script
   - Monitor CloudWatch logs
   - Verify S3 output
   - Test timeout/failure scenarios

3. **Bot Integration Test**
   - Deploy updated bot to dev/staging
   - Post test message with Looker URL in Slack test channel
   - Verify end-to-end workflow:
     - Message detected
     - SQL extracted
     - SageMaker job triggered
     - Results posted to Slack
     - State saved to S3

4. **Production Validation**
   - Compare credit calculations: old Papermill vs new SageMaker
   - Run parallel executions with same SQL query
   - Verify results match within tolerance (<1% difference)

---

## Critical Files

### Files to Modify
1. `Verify - Credit Recommendation.ipynb` - Notebook modifications
2. `src/credit_bot.py` - Executor import and workflow updates
3. `src/config.py` - Add SageMaker configuration variables
4. `requirements.txt` - Add boto3 sagemaker dependencies
5. `docker-requirements.txt` - Add boto3 sagemaker dependencies
6. `airflow/credit_bot_dag.py` - No changes needed (same container execution)

### Files to Create
1. `sagemaker/Dockerfile` - Container for notebook execution
2. `sagemaker/requirements.txt` - Notebook dependencies
3. `sagemaker/entrypoint.sh` - Papermill execution script
4. `sagemaker/build_and_push.sh` - Container build/deploy script
5. `src/sagemaker_executor.py` - SageMaker integration class
6. `Documentation/SAGEMAKER_SETUP.md` - Setup guide for new architecture

### Files to Delete (optional)
- `src/notebook_executor.py` - Replaced by `sagemaker_executor.py`

---

## Deployment Steps

### Pre-Deployment Checklist
- [ ] Presto service account credentials approved and added to Secrets Manager
- [ ] SageMaker IAM role created with correct permissions
- [ ] ECR repository created
- [ ] Bot IAM role updated with SageMaker permissions
- [ ] S3 bucket structure created

### Deployment Sequence
1. **Build and push Docker image**
   ```bash
   cd sagemaker/
   ./build_and_push.sh
   ```

2. **Update configuration**
   - Set `SAGEMAKER_IMAGE_URI` in bot environment
   - Set `SAGEMAKER_ROLE_ARN` in bot environment
   - Set `PRESTO_SECRET_NAME` in bot environment

3. **Deploy bot updates**
   ```bash
   ./deploy.sh  # Existing deployment script
   ```

4. **Test in staging environment**
   - Post test message to staging Slack channel
   - Verify execution and results

5. **Monitor initial production runs**
   - Watch CloudWatch logs for errors
   - Compare credit amounts with historical data
   - Verify S3 outputs are created correctly

---

## Rollback Plan

If SageMaker integration fails:
1. Revert `src/credit_bot.py` to use `NotebookExecutor`
2. Restore `src/notebook_executor.py` if deleted
3. Redeploy bot with previous configuration
4. Local Papermill execution continues to work as before

---

## Benefits of New Architecture

1. **Scalability**: SageMaker handles compute scaling automatically
2. **Reliability**: Dedicated compute resources, not shared with bot process
3. **Security**: Credentials in Secrets Manager, not in code or environment files
4. **Observability**: CloudWatch logs for notebook execution separate from bot logs
5. **Flexibility**: Easy to update notebook without redeploying bot
6. **Cost**: Pay-per-execution pricing (no always-on notebook instances)

---

## Estimated Timeline

- **Phase 1** (Notebook modifications): 2-3 hours
- **Phase 2** (Docker container): 2-3 hours
- **Phase 3** (SageMaker executor): 3-4 hours
- **Phase 4** (Bot integration): 1-2 hours
- **Phase 5** (AWS setup): 1-2 hours
- **Phase 6** (Testing): 2-3 hours

**Total**: 1-2 days of development + testing

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| SageMaker job timeout | Increase max runtime, optimize SQL queries in notebook |
| Presto credentials invalid | Test connection before deployment, add retry logic |
| S3 output not created | Add explicit error handling and logging in notebook |
| Bot can't access SageMaker | Verify IAM permissions before deployment |
| Credit calculation differences | Run parallel executions and validate results match |
| Cost increase | Monitor SageMaker usage, optimize instance type selection |

---

## Open Questions

1. **Presto Secret Name**: What should the Secrets Manager secret be named? (Default: `presto-service-account-credentials`)
2. **S3 Bucket**: Which S3 bucket should be used for outputs? (Use existing bucket or create new one?)
3. **SageMaker Instance Type**: `ml.m5.xlarge` sufficient, or need larger instance for faster queries?
4. **Execution Timeout**: 30 minutes max runtime acceptable, or should be longer?
5. **Cost Budget**: What's the expected monthly cost tolerance for SageMaker Processing Jobs?

---

## Success Criteria

- [ ] Notebook executes successfully in SageMaker container
- [ ] Bot triggers SageMaker jobs and retrieves results
- [ ] Credit amounts match historical calculations (±1%)
- [ ] Full end-to-end workflow completes in <5 minutes
- [ ] Zero manual intervention required
- [ ] CloudWatch logs provide clear debugging information
- [ ] S3 audit trail maintained for all executions
