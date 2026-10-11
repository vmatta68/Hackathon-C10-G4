from __future__ import annotations

from typing import Any, TypedDict


class IncidentState(TypedDict, total=False):
    incident_id: str
    log_summary: dict[str, Any]
    rag_context: list[dict[str, str]]
    extra_context: str
    classified_logs: dict[str, Any]
    diagnosis: dict[str, Any]
    remediation: dict[str, Any]
    runbook: dict[str, Any]
    notification: dict[str, Any]
    ticket: dict[str, Any]
    severity: str
    service: str
    errors: list[str]
    result: dict[str, Any]
