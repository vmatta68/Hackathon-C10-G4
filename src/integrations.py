from __future__ import annotations

import json
import requests
from requests.auth import HTTPBasicAuth

from .config import Settings


def post_slack_notification(webhook_url: str, result: dict) -> str:
    if not webhook_url.startswith("https://"):
        raise ValueError("Slack webhook URL must use HTTPS.")
    notification = result.get("notification", {})
    severity = result.get("severity", "UNKNOWN")
    service = result.get("service", "unknown-service")
    text = (
        f"*DevOps incident analysis — {severity}*\n"
        f"*Service:* {service}\n"
        f"*Summary:* {notification.get('title', 'Incident analysis available')}\n"
        f"{notification.get('message', 'See the incident report for details.')}\n"
        "_AI-generated recommendations; validate before acting._"
    )
    response = requests.post(webhook_url, json={"text": text}, timeout=15)
    response.raise_for_status()
    return f"sent (HTTP {response.status_code})"


def create_jira_issue(settings: Settings, result: dict) -> dict:
    if not settings.jira_is_configured:
        raise RuntimeError("Jira configuration is incomplete.")
    if not settings.jira_base_url.startswith("https://"):
        raise ValueError("JIRA_BASE_URL must use HTTPS.")
    ticket = result.get("ticket", {})
    description_text = ticket.get("description", "")
    criteria = ticket.get("verification_criteria", [])
    if criteria:
        description_text += "\n\nVerification criteria:\n" + "\n".join(f"- {x}" for x in criteria)
    description_text += "\n\nAI-generated draft. Validate diagnosis and remediation before acting."
    # Jira Cloud REST API v3 uses Atlassian Document Format for description.
    payload = {
        "fields": {
            "project": {"key": settings.jira_project_key},
            "summary": str(ticket.get("summary", "AI-assisted incident analysis"))[:250],
            "issuetype": {"name": settings.jira_issue_type},
            "priority": {"name": ticket.get("priority", "Medium")},
            "labels": ticket.get("labels", ["incident-analysis"]),
            "description": {
                "type": "doc",
                "version": 1,
                "content": [{
                    "type": "paragraph",
                    "content": [{"type": "text", "text": description_text[:12000]}]
                }]
            },
        }
    }
    url = f"{settings.jira_base_url}/rest/api/3/issue"
    response = requests.post(
        url,
        auth=HTTPBasicAuth(settings.jira_email, settings.jira_api_token),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=20,
    )
    if not response.ok:
        raise RuntimeError(f"Jira API returned HTTP {response.status_code}: {response.text[:1000]}")
    return response.json()
