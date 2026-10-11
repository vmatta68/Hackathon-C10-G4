# Authentication Errors Runbook

## Triage

Identify the affected application or API, incident start time, authentication endpoint, and relevant HTTP status codes. Determine whether failures affect all users or only a subset. Check for recent identity-provider, token, configuration, or certificate changes.

## Investigate

Review authentication service health, identity-provider availability, token validation errors, token expiration, issuer and audience configuration, clock synchronization, and certificate validity. Compare failure patterns across services and inspect authorized monitoring and audit logs. Do not record or expose actual passwords, access tokens, or secrets.

## Mitigate

Follow the approved identity and access-management incident procedure. Correct configuration problems only after validating the evidence and obtaining the required authorization. Do not disable authentication controls, weaken access policies, or bypass token validation as a shortcut.

## Verify

Confirm that authorized users and services can authenticate successfully, unauthorized requests remain rejected, and authentication error rates return toward baseline. Check for recurrence and confirm that access controls remain effective.

## Communicate

Document the affected service, authentication failure pattern, start time, scope, relevant configuration changes, evidence, remediation status, and remaining uncertainties. Do not declare a security breach solely because authentication failures occurred.