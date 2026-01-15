# Pre-SageMaker Documentation Archive

This directory contains documentation from the original architecture before the SageMaker migration.

**Archived on**: 2026-01-15

**Reason**: These documents describe the local Papermill execution architecture that will be replaced with SageMaker Processing Jobs and direct Presto database access.

---

## Archived Documents

### PROTOTYPE_SUMMARY.md
**Original Purpose**: Project summary and implementation details for the local Papermill architecture.

**Key Topics Covered**:
- Phase 1 & 2 evolution (prototype → production)
- Original production architecture (Airflow → K8s → Docker with local Papermill)
- Component descriptions (Slack, Looker, NotebookExecutor, StateManager)
- Notebook execution with Papermill locally
- Summary extraction from executed notebooks

**Why Archived**: Describes `notebook_executor.py` and local execution which will be replaced by `sagemaker_executor.py` and SageMaker Processing Jobs.

---

### LOCAL_DEVELOPMENT.md
**Original Purpose**: Guide for setting up local development environment with Papermill execution.

**Key Topics Covered**:
- Local virtual environment setup
- Installing Papermill and notebook dependencies
- Running notebooks locally for testing
- Debugging local Papermill execution
- Testing with local `.env` file

**Why Archived**: Local Papermill setup instructions will be replaced with SageMaker-focused development workflow.

---

### SETUP_GUIDE.md
**Original Purpose**: Complete setup instructions for configuring the bot with local Papermill execution.

**Key Topics Covered**:
- Slack bot token setup
- Looker API credentials
- Local Presto database connection via `.env`
- Papermill installation and configuration
- Notebook path configuration

**Why Archived**: Setup instructions reference local Presto credentials in `.env` file, which will be replaced with AWS Secrets Manager for service account credentials.

---

## What Replaces These Documents

| Old Document | New Reference |
|--------------|---------------|
| PROTOTYPE_SUMMARY.md | `SAGEMAKER_MIGRATION_PLAN.md` - New architecture details |
| LOCAL_DEVELOPMENT.md | Will be rewritten post-migration for SageMaker development |
| SETUP_GUIDE.md | Will be rewritten post-migration for SageMaker setup |

---

## Architecture Changes

### Old Architecture (Archived)
```
Airflow → K8s Pod → Docker Container
  ├─ Papermill executes notebook locally in container
  ├─ Credentials from .env file
  ├─ Synchronous execution
  └─ Summary extraction from executed notebook
```

### New Architecture (Planned)
```
Airflow → K8s Pod → Docker Container (Bot)
  └─ Triggers SageMaker Processing Job
       ├─ Notebook executes in dedicated SageMaker container
       ├─ Credentials from AWS Secrets Manager
       ├─ Direct Presto database access via service account
       ├─ Asynchronous execution with polling
       └─ Results written to S3, bot reads them
```

---

## Migration Timeline

**Current Status**: Bot operational with local Papermill execution (archived architecture)

**Next Steps**:
1. Receive approval for Presto service account credentials
2. Implement SageMaker migration per `SAGEMAKER_MIGRATION_PLAN.md`
3. Update/rewrite documentation for new architecture
4. Archive becomes reference for rollback if needed

---

## Accessing Old Documentation

These archived documents remain available for:
- Understanding the original implementation
- Troubleshooting current pre-migration deployment
- Reference during migration development
- Rollback procedures if needed

To view original architecture documentation, refer to the files in this directory.
