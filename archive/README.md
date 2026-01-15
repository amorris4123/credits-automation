# Archive Directory

This directory is prepared for archiving files during the SageMaker migration.

## old-local-execution/

**Status**: Directory prepared, files to be moved here during migration implementation.

This directory will contain files from the original architecture where notebooks were executed locally using Papermill.

**Migration Scheduled**: When Presto service account credentials are approved

**Reason**: Migrating to SageMaker Processing Jobs with direct Presto database access using service account credentials.

### Files to be Archived During Migration:

- `src/notebook_executor.py` - Original local Papermill-based notebook executor
  - Will be replaced by: `src/sagemaker_executor.py` (to be implemented)
  - Functionality: Executes Jupyter notebooks locally with Papermill, extracts credit amounts, saves outputs to S3
  - **Current Status**: Still in use, will be moved here when SageMaker executor is implemented and tested

## Migration Context

See `SAGEMAKER_MIGRATION_PLAN.md` in the root directory for the full migration plan to the new SageMaker-based architecture.

### Key Architecture Changes:

**Current (to be archived)**:
- Local Papermill execution within bot container
- Credentials from `.env` file
- Synchronous execution in bot process

**New (Planned)**:
- SageMaker Processing Jobs
- Credentials from AWS Secrets Manager
- Asynchronous execution with polling
- Direct Presto database access via service account

## Migration Steps

When implementing the migration:

1. Implement `src/sagemaker_executor.py` per the migration plan
2. Update `src/credit_bot.py` to use `SageMakerExecutor` instead of `NotebookExecutor`
3. Test thoroughly in staging environment
4. Move `src/notebook_executor.py` to `archive/old-local-execution/notebook_executor.py`
5. Update this README with actual archive date

## Rollback

If the SageMaker migration needs to be rolled back, files from this directory can be restored to their original locations.
