# Deployment Failure Runbook

## Triage

Identify the affected service, deployment version, start time, current deployment status, and error rate. Check whether errors began after a recent deployment. Review application logs, deployment events, readiness probes, and health checks.

## Investigate

Review the application release notes, configuration changes, deployment logs, database migration history, and application startup errors. Compare the expected application schema with the actual database schema. Determine whether a migration failed, remains incomplete, or introduced a compatibility problem.

## Mitigate

Follow the service team's approved incident runbook and change-management process. If the problem is strongly correlated with a recent deployment, ask the responsible service owner to assess whether rollback or another mitigation is appropriate. Verify database and application compatibility before acting. Do not perform an unapproved rollback or repeat database migrations without authorization.

## Verify

Confirm that the application starts successfully, readiness probes pass, affected instances are healthy, and HTTP 5xx error rates return toward baseline. Check that request processing works and that the problem does not recur.

## Communicate

Document the affected service, release version, incident start time, observed symptoms, evidence, customer impact if known, current mitigation status, owner, and next update time. Clearly distinguish confirmed findings from root-cause hypotheses.