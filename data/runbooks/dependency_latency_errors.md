
# Dependency Latency and Upstream Errors Runbook

## Triage

Identify the affected service, incident start time, request latency, timeout rate, retry rate, and upstream error rate. Determine whether checkout or other critical user-facing operations are affected. Establish whether the incident is ongoing and compare metrics with the normal baseline.

## Investigate

Review application, proxy, and upstream dependency logs around the incident time window. Identify the specific upstream dependency, error code, request ID, timeout, and latency measurements where available. Compare traces across service boundaries to determine where requests are slowing down or failing.

Review retry behavior, timeout settings, connection pools, dependency health, and recent deployment or configuration changes. Verify that timestamps are aligned across services. Do not assume that a dependency is the root cause merely because an upstream error was reported.

## Mitigate

Follow the approved incident-response procedure and involve the responsible service owner. Consider mitigation only after correlating evidence and assessing the impact of the proposed action. Do not change retry policies, timeout settings, proxy routing, service configuration, or deployment state without appropriate authorization.

## Verify

Compare request success rate, latency, timeout rate, retry volume, and upstream error rate with the pre-incident baseline. Verify the affected business operation, not just the service health endpoint. Check for recurring errors after an approved mitigation.

## Communicate

Record the affected services, incident time window, known symptoms, upstream dependency if identified, impact estimates, current investigation status, and responsible owner. Clearly distinguish observed facts from hypotheses. Mark unavailable timestamps, metrics, and customer-impact information as unknown.

