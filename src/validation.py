
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


VALID_SEVERITIES = {
    "LOW", "MEDIUM", "HIGH", "CRITICAL", "UNKNOWN"
}


def as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def as_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return default
    return str(value)


def normalize_severity(value: Any) -> str:
    severity = as_text(value, "UNKNOWN").strip().upper()
    return severity if severity in VALID_SEVERITIES else "UNKNOWN"


def _timestamp_sort_key(event: dict, index: int) -> tuple:
    """Valid timestamps first; missing/invalid timestamps last."""
    raw = as_text(event.get("timestamp")).strip()

    if not raw:
        return (1, float("inf"), index)

    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return (0, parsed.timestamp(), index)

    except (ValueError, TypeError, OverflowError):
        return (1, float("inf"), index)


def normalize_classification(value: Any) -> dict:
    out = dict(as_dict(value))

    out["service"] = as_text(
        out.get("service"), "unknown-service"
    ) or "unknown-service"

    out["severity"] = normalize_severity(out.get("severity"))

    for field in (
        "error_patterns",
        "affected_components",
        "missing_information",
    ):
        out[field] = [
            as_text(item)
            for item in as_list(out.get(field))
            if as_text(item).strip()
        ]

    events = [
        dict(as_dict(event))
        for event in as_list(out.get("events"))
        if isinstance(event, dict)
    ]

    for event in events:
        event["timestamp"] = as_text(event.get("timestamp"))
        event["level"] = as_text(event.get("level"), "UNKNOWN")
        event["message"] = as_text(event.get("message"))

    out["events"] = [
        event
        for _, event in sorted(
            enumerate(events),
            key=lambda pair: _timestamp_sort_key(
                pair[1], pair[0]
            ),
        )
    ]

    return out


def normalize_diagnosis(value: Any) -> dict:
    out = dict(as_dict(value))

    hypotheses = as_list(out.get("root_cause_hypotheses"))

    # Support the older/simpler single-hypothesis response.
    if not hypotheses and out.get("cause"):
        hypotheses = [{
            "cause": out.get("cause"),
            "confidence": out.get("confidence", 0),
            "evidence": out.get("evidence", []),
            "confirmed": out.get("confirmed", False),
        }]

    normalized = []

    for item in hypotheses:
        hypothesis = as_dict(item)

        try:
            confidence = float(hypothesis.get("confidence", 0))
        except (TypeError, ValueError):
            confidence = 0.0

        confidence = max(0.0, min(1.0, confidence))

        normalized.append({
            "cause": as_text(hypothesis.get("cause")),
            "confidence": confidence,
            "evidence": [
                as_text(x)
                for x in as_list(hypothesis.get("evidence"))
            ],
            "confirmed": (
                hypothesis.get("confirmed", False) is True
            ),
        })

    out["summary"] = as_text(out.get("summary"))
    out["impact"] = as_text(out.get("impact"))
    out["root_cause_hypotheses"] = normalized

    for field in ("additional_checks", "missing_information"):
        out[field] = [
            as_text(x)
            for x in as_list(out.get(field))
        ]

    return out


def normalize_remediation(value: Any) -> dict:
    out = dict(as_dict(value))
    actions = as_list(out.get("actions"))

    # Support responses that return one action at the top level.
    if not actions and out.get("action"):
        actions = [{
            "step": out.get("step", 1),
            "action": out.get("action"),
            "rationale": out.get("rationale", ""),
            "risk": out.get("risk", "UNKNOWN"),
            "verification": out.get("verification", ""),
        }]

    normalized_actions = []

    for index, item in enumerate(actions, start=1):
        action = as_dict(item)

        normalized_actions.append({
            "step": index,
            "action": as_text(action.get("action")),
            "rationale": as_text(action.get("rationale")),
            "risk": as_text(action.get("risk"), "UNKNOWN").upper(),
            "verification": as_text(action.get("verification")),
        })

    out["actions"] = normalized_actions
    out["avoid"] = [
        as_text(x) for x in as_list(out.get("avoid"))
    ]
    out["human_approval_required"] = (
        out.get("human_approval_required") is not False
    )

    return out



def normalize_runbook(
    value: Any,
    *,
    classification: Any = None,
    diagnosis: Any = None,
    remediation: Any = None,
) -> dict:
    out = dict(as_dict(value))

    phases = [
        "Triage",
        "Investigate",
        "Mitigate",
        "Verify",
        "Communicate",
    ]

    # Safe generic fallbacks are used if the model omits a phase.
    defaults = {
        "Triage": {
            "phase": "Triage",
            "task": (
                "Confirm the incident time window, affected service "
                "and operations, current status, and known impact."
            ),
            "done_when": (
                "The incident scope, current status, and known "
                "unknowns are recorded."
            ),
        },
        "Investigate": {
            "phase": "Investigate",
            "task": (
                "Review relevant logs, service and dependency metrics, "
                "and recent changes. Do not treat a suspected cause "
                "as confirmed without supporting evidence."
            ),
            "done_when": (
                "Available evidence and unresolved hypotheses "
                "are documented."
            ),
        },
        "Mitigate": {
            "phase": "Mitigate",
            "task": (
                "Choose an evidence-based mitigation or escalate "
                "through the approved incident process. Obtain "
                "required approval before state-changing actions."
            ),
            "done_when": (
                "An approved mitigation plan or escalation is "
                "documented before action."
            ),
        },
        "Verify": {
            "phase": "Verify",
            "task": (
                "Compare relevant error rates, latency, service "
                "health, and affected business operations with "
                "the pre-incident baseline."
            ),
            "done_when": (
                "Recovery evidence is recorded and monitored "
                "for recurrence over the agreed observation period."
            ),
        },
        "Communicate": {
            "phase": "Communicate",
            "task": (
                "Communicate severity, known symptoms and impact, "
                "uncertainties, current status, and next steps "
                "to the appropriate stakeholders."
            ),
            "done_when": (
                "Responders and stakeholders have a status update "
                "with the known impact, unresolved questions, "
                "and next steps."
            ),
        },
    }
    
    # Build incident-specific fallback tasks from existing workflow evidence.
    cls = as_dict(classification)
    diag = as_dict(diagnosis)
    rem = as_dict(remediation)

    service = (
        as_text(cls.get("service"), "affected service").strip()
        or "affected service"
    )
    severity = (
        as_text(cls.get("severity"), "UNKNOWN").strip().upper()
        or "UNKNOWN"
    )

    events = [
        as_dict(item)
        for item in as_list(cls.get("events"))
        if isinstance(item, dict)
    ]

    symptoms = []
    for event in events:
        level = as_text(event.get("level"), "UNKNOWN").strip().upper()
        message = as_text(event.get("message")).strip()

        if message and level not in {"INFO", "DEBUG", "TRACE"}:
            symptoms.append(f"{level}: {message}")

    if not symptoms:
        symptoms = [
            as_text(item).strip()
            for item in as_list(cls.get("error_patterns"))
            if as_text(item).strip()
        ]

    symptom_text = (
        "; ".join(symptoms[:4])
        or "the symptoms recorded in the available incident evidence"
    )

    impact = (
        as_text(diag.get("impact")).strip()
        or "not yet established from the available evidence"
    )


    remediation_actions = [
        as_text(as_dict(item).get("action")).strip().rstrip(". ")
        for item in as_list(rem.get("actions"))
        if as_text(as_dict(item).get("action")).strip()
    ]


    # Prefer actual mitigation proposals over diagnostic or verification tasks.
    mitigation_markers = (
        "candidate mitigation",
        "candidate mitigations",
        "mitigation option",
        "mitigation plan",
        "traffic adjustment",
        "concurrency adjustment",
        "dependency recovery",
        "deployment rollback",
        "rollback",
        "roll back",
        "revert",
        "failover",
        "restore service",
        "escalate",
        "escalation",
        "approved mitigation",
    )

    verification_markers = (
        "after an authorized mitigation",
        "after mitigation",
        "after the mitigation",
        "monitor ",
        "observe for recurrence",
        "verify recovery",
        "compare metrics",
        "check current",
        "inspect read-only",
        "collect read-only",
    )

    scored_actions = []

    for index, action in enumerate(remediation_actions):
        text = action.lower()

        positive_score = sum(
            3 for marker in mitigation_markers if marker in text
        )
        negative_score = sum(
            4 for marker in verification_markers if marker in text
        )

        score = positive_score - negative_score

        scored_actions.append((score, index, action))

    best_action = max(
        scored_actions,
        key=lambda item: (item[0], -item[1]),
        default=(0, 0, ""),
    )

    if best_action[0] > 0:
        first_action = best_action[2]
        mitigation_review = (
            f" Review this proposed mitigation candidate: "
            f"{first_action}."
        )
    elif remediation_actions:
        first_action = remediation_actions[0]
        mitigation_review = (
            " Review the available remediation recommendations "
            "and determine whether an evidence-based mitigation "
            "or escalation is appropriate. The first available "
            f"recommendation is: {first_action}."
        )
    else:
        mitigation_review = (
            " Select an evidence-based mitigation or escalate "
            "through the approved incident process."
        )

    defaults["Triage"]["task"] = (
        f"Confirm the current status and scope of {service}. "
        f"Review the incident time window, affected operations, and impact. "
        f"Observed source-log indicators include: {symptom_text}."
    )

    defaults["Investigate"]["task"] = (
        f"Correlate the observed source-log indicators for {service} "
        f"({symptom_text}) with relevant service and dependency metrics "
        f"and recent changes. Keep root-cause hypotheses unconfirmed "
        f"until supported by evidence."
    )

    defaults["Mitigate"]["task"] = (
        f"Assess the appropriate next step for {service} using the "
        f"available evidence.{mitigation_review} Obtain required human "
        f"approval before state-changing actions."
    )

    defaults["Verify"]["task"] = (
        f"Monitor relevant error rates, latency, health signals, and "
        f"affected operations for {service}. Check whether the observed "
        f"symptoms ({symptom_text}) return toward the pre-incident "
        f"baseline and whether errors recur."
    )

    defaults["Communicate"]["task"] = (
        f"Update the appropriate responders and stakeholders on "
        f"{service} and its {severity} severity, including observed "
        f"symptoms, known impact ({impact}), unresolved questions, "
        f"current status, and investigation or verification next steps."
    )

    # These are generic templates, not incident-specific tasks.
    generic_tasks = {
        "Confirm the incident time window, affected service and "
        "operations, current status, and known impact.",
        "Review relevant logs, service and dependency metrics, and "
        "recent changes. Do not treat a suspected cause as confirmed "
        "without supporting evidence.",
        "Choose an evidence-based mitigation or escalate through the "
        "approved incident process. Obtain required approval before "
        "state-changing actions.",
        "Compare relevant error rates, latency, service health, and "
        "affected business operations with the pre-incident baseline.",
        "Communicate severity, known symptoms and impact, uncertainties, "
        "current status, and next steps to the appropriate stakeholders.",
    }

    checklist = as_list(out.get("checklist"))

    # Support the older single-task response format.
    if not checklist and out.get("task"):
        checklist = [{
            "phase": out.get("phase", "Triage"),
            "task": out.get("task"),
            "done_when": out.get("done_when", ""),
        }]

    # Keep at most one valid entry for each recognized phase.
    by_phase = {}

    for raw in checklist:
        if not isinstance(raw, dict):
            continue

        item = as_dict(raw)
        phase_text = as_text(item.get("phase")).strip().lower()

        phase = next(
            (name for name in phases if name.lower() == phase_text),
            None,
        )

        task = as_text(item.get("task")).strip()
        if task in generic_tasks:
            continue        

        if phase and task and phase not in by_phase:
            by_phase[phase] = {
                "phase": phase,
                "task": task,
                "done_when": (
                    as_text(item.get("done_when")).strip()
                    or defaults[phase]["done_when"]
                ),
            }

    # Emit all phases in a fixed order, filling any missing phase
    # with a safe generic fallback.
    out["checklist"] = [
        by_phase.get(phase, defaults[phase].copy())
        for phase in phases
    ]

    # Remove duplicate legacy fields from the top-level runbook.
    out.pop("phase", None)
    out.pop("task", None)
    out.pop("done_when", None)

    out["rollback_considerations"] = [
        as_text(item)
        for item in as_list(out.get("rollback_considerations"))
        if as_text(item).strip()
    ]

    out["communications_summary"] = (
        as_text(out.get("communications_summary")).strip()
        or (
            f"Communicate {severity} severity for {service}. "
            f"Observed source-log indicators: {symptom_text}. "
            f"Known impact: {impact}. The root cause remains unconfirmed "
            f"unless supported by evidence. Share current status, "
            f"approved actions or escalation, and next steps."
        )
    )

    return out



def normalize_notification(
    value: Any,
    default_severity: str = "UNKNOWN",
) -> dict:
    out = dict(as_dict(value))

    return {
        "title": as_text(out.get("title")),
        "message": as_text(out.get("message")),
        "severity": normalize_severity(
            out.get("severity", default_severity)
        ),
    }


def normalize_ticket(value: Any) -> dict:
    out = dict(as_dict(value))

    allowed_priorities = {
        "Highest", "High", "Medium", "Low", "Lowest"
    }
    priority = as_text(out.get("priority"), "Medium")

    if priority not in allowed_priorities:
        priority = "Medium"

    return {
        "summary": as_text(out.get("summary")),
        "description": as_text(out.get("description")),
        "priority": priority,
        "labels": [
            as_text(x)
            for x in as_list(out.get("labels"))
        ][:5],
        "verification_criteria": [
            as_text(x)
            for x in as_list(out.get("verification_criteria"))
        ][:5],
    }
