# Synthetic DevOps Incident Test Data

All records in this pack are fictional, created for local hackathon testing. Do not treat any model-generated diagnosis as confirmed root cause.

## Files and purpose

1. `01_database_connection_failures.csv` — database connection-pool exhaustion and downstream HTTP 503 responses. Expected focus: inspect pool utilization, database health, transaction/query latency, and service errors.
2. `02_failed_deployment.csv` — readiness-probe failures and a database migration-check error after a deployment. Expected focus: investigate release timing, migration compatibility, health checks, and approved rollback process; do not assume causation solely from timing.
3. `03_authentication_errors.csv` — invalid token signatures, issuer mismatch, expired token and HTTP 401s. Expected focus: investigate authentication configuration and token validation; do not automatically declare a security breach.
4. `04_incomplete_ambiguous_logs.csv` — valid CSV with missing timestamps and vague messages. Expected focus: explicitly state uncertainty and request additional logs/metrics.
5. `05_malformed_csv.csv` — deliberately malformed row with an extra field. Expected result: CSV validation/read error is shown cleanly; analysis should not proceed.
6. `06_empty_csv.csv` — header-only CSV with no records. Expected result: clear no-data validation message.

## How to test

1. Start the app from the project folder: `python app.py`.
2. Upload one CSV at a time.
3. Run each of files 01-04 with the context box left blank, then try an additional context prompt.
4. Files 05 and 06 are negative tests; confirm the application shows a readable validation error instead of crashing.
5. Record whether analysis completed, evidence was relevant, recommendations were safe, and uncertainty was handled correctly.

The LLM's exact wording and severity can vary by model and prompt. Evaluate whether outputs are evidence-based and safe rather than expecting exact text.
