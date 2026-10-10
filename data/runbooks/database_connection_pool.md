# Database Connection Pool Exhaustion Runbook

## Triage
Confirm the affected service, start time, error rate, and whether the issue began after a deployment. Compare application and database timestamps.

## Investigate
Inspect connection-pool active/idle counts, wait time, timeout counts, database connection limits, query latency, and database CPU/memory. Review recent changes and traffic volume. Look for long-running transactions and leaked connections.

## Mitigate
Follow the service team's approved runbook. If a recent deployment is strongly correlated, assess rollback using the normal change process. Do not increase pool limits without checking database capacity. Avoid restarting all instances at once.

## Verify
Confirm pool utilization is recovering, connection timeout counts are falling, HTTP 5xx rates return toward baseline, and health checks remain stable. Observe for recurrence.

## Communicate
Provide affected service, start time, customer impact if known, current evidence, mitigation owner, and next update time. Do not state a root cause as confirmed until validated.
