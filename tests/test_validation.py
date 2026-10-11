
from src.validation import (
    normalize_classification,
    normalize_diagnosis,
    normalize_remediation,
    normalize_runbook,
    normalize_ticket,
)


def test_flat_diagnosis_becomes_hypothesis_list():
    result = normalize_diagnosis({
        "cause": "Possible database issue",
        "confidence": 0.7,
        "evidence": ["Connection timeout"],
        "confirmed": False,
    })

    assert len(result["root_cause_hypotheses"]) == 1
    assert result["root_cause_hypotheses"][0]["cause"] == (
        "Possible database issue"
    )


def test_single_action_becomes_actions_list():
    result = normalize_remediation({
        "step": 1,
        "action": "Inspect pool metrics",
        "risk": "LOW",
        "verification": "Metrics recorded",
    })

    assert len(result["actions"]) == 1
    assert result["actions"][0]["action"] == "Inspect pool metrics"



def test_single_runbook_task_is_preserved_and_missing_phases_filled():
    result = normalize_runbook({
        "phase": "Triage",
        "task": "Check current service health",
        "done_when": "Health is recorded",
    })

    checklist = result["checklist"]

    # Every normalized runbook must have five ordered phases.
    assert len(checklist) == 5
    assert [item["phase"] for item in checklist] == [
        "Triage",
        "Investigate",
        "Mitigate",
        "Verify",
        "Communicate",
    ]

    # Preserve the original task and its completion criterion.
    assert checklist[0]["task"] == "Check current service health"
    assert checklist[0]["done_when"] == "Health is recorded"

    # Every phase must have a task and completion criterion.
    assert all(item["task"].strip() for item in checklist)
    assert all(item["done_when"].strip() for item in checklist)



def test_classification_sorts_events_and_missing_timestamp_last():
    result = normalize_classification({
        "severity": "HIGH",
        "events": [
            {"timestamp": "2026-10-10T10:02:00Z", "message": "Later"},
            {"timestamp": "", "message": "Unknown time"},
            {"timestamp": "2026-10-10T10:01:00Z", "message": "Earlier"},
        ],
    })

    events = result["events"]
    assert events[0]["message"] == "Earlier"
    assert events[1]["message"] == "Later"
    assert events[2]["message"] == "Unknown time"


def test_ticket_normalization_limits_list_lengths():
    result = normalize_ticket({
        "summary": "Incident",
        "priority": "InvalidPriority",
        "labels": ["a", "b", "c", "d", "e", "f"],
        "verification_criteria": ["one", "two", "three", "four", "five", "six"],
    })

    assert result["priority"] == "Medium"
    assert len(result["labels"]) == 5
    assert len(result["verification_criteria"]) == 5


def test_runbook_duplicate_phases_keep_first_valid_item():
    result = normalize_runbook({
        "checklist": [
            {
                "phase": "Triage",
                "task": "First triage task",
                "done_when": "Scope recorded",
            },
            {
                "phase": "Triage",
                "task": "Duplicate triage task",
                "done_when": "Duplicate recorded",
            },
            {
                "phase": "Investigate",
                "task": "Inspect pool metrics",
                "done_when": "Metrics recorded",
            },
        ]
    })

    checklist = result["checklist"]

    assert len(checklist) == 5
    assert [item["phase"] for item in checklist] == [
        "Triage",
        "Investigate",
        "Mitigate",
        "Verify",
        "Communicate",
    ]

    # The first valid Triage entry should be retained.
    assert checklist[0]["task"] == "First triage task"


def test_runbook_missing_done_when_gets_default():
    result = normalize_runbook({
        "checklist": [
            {
                "phase": "Triage",
                "task": "Check current service health",
            }
        ]
    })

    checklist = result["checklist"]

    assert len(checklist) == 5
    assert checklist[0]["task"] == "Check current service health"
    assert checklist[0]["done_when"].strip()

    # All phases must have a completion criterion.
    assert all(item["done_when"].strip() for item in checklist)


def test_runbook_missing_phases_are_filled():
    result = normalize_runbook({
        "checklist": [
            {
                "phase": "Investigate",
                "task": "Inspect pool metrics",
                "done_when": "Metrics captured",
            }
        ]
    })

    checklist = result["checklist"]
    by_phase = {item["phase"]: item for item in checklist}

    assert len(checklist) == 5
    assert by_phase["Investigate"]["task"] == "Inspect pool metrics"
    assert by_phase["Investigate"]["done_when"] == "Metrics captured"

    for phase in ("Triage", "Mitigate", "Verify", "Communicate"):
        assert by_phase[phase]["task"].strip()
        assert by_phase[phase]["done_when"].strip()

def test_runbook_generic_tasks_use_incident_context():
    result = normalize_runbook(
        {
            "checklist": [
                {
                    "phase": "Triage",
                    "task": (
                        "Confirm the incident time window, affected "
                        "service and operations, current status, and "
                        "known impact."
                    ),
                    "done_when": "Incident details recorded",
                }
            ],
            "communications_summary": "",
        },
        classification={
            "service": "payment-service",
            "severity": "HIGH",
            "events": [
                {
                    "timestamp": "2026-10-11T10:03:00Z",
                    "level": "ERROR",
                    "message": "Connection pool exhausted",
                }
            ],
        },
        diagnosis={
            "impact": "Payment requests may fail or be delayed."
        },
        remediation={
            "actions": [
                {
                    "action": "Inspect pool utilization and wait-time metrics."
                }
            ]
        },
    )

    checklist = result["checklist"]
    by_phase = {item["phase"]: item for item in checklist}

    assert len(checklist) == 5

    # The generic Triage template should have been replaced.
    assert "payment-service" in by_phase["Triage"]["task"]
    assert "Connection pool exhausted" in by_phase["Triage"]["task"]

    # The mitigation fallback should use the available recommendation.
    assert (
        "Inspect pool utilization and wait-time metrics."
        in by_phase["Mitigate"]["task"]
    )

    # The communications summary should be populated from context.
    summary = result["communications_summary"]
    assert summary
    assert "HIGH" in summary
    assert "payment-service" in summary

def test_runbook_prefers_mitigation_action_over_diagnostic_action():
    result = normalize_runbook(
        {
            "checklist": [
                {
                    "phase": "Mitigate",
                    "task": (
                        "Choose an evidence-based mitigation or escalate "
                        "through the approved incident process. Obtain "
                        "required approval before state-changing actions."
                    ),
                    "done_when": (
                        "An approved mitigation plan or escalation "
                        "is documented before action."
                    ),
                }
            ]
        },
        classification={
            "service": "payment-service",
            "severity": "HIGH",
            "events": [
                {
                    "level": "ERROR",
                    "message": "Connection pool exhausted",
                }
            ],
        },
        diagnosis={
            "impact": "Payment requests may fail or be delayed."
        },
        remediation={
            "actions": [
                {
                    "step": 1,
                    "action": (
                        "Inspect current connection-pool utilization "
                        "and timeout metrics."
                    ),
                },
                {
                    "step": 2,
                    "action": (
                        "If the incident is ongoing, propose an "
                        "approved traffic adjustment for human review "
                        "before applying any change."
                    ),
                },
            ]
        },
    )

    checklist = result["checklist"]
    mitigation = next(
        item for item in checklist
        if item["phase"] == "Mitigate"
    )

    assert "approved traffic adjustment" in mitigation["task"]
    assert "Inspect current connection-pool utilization" not in (
        mitigation["task"]
    )
    assert "human approval" in mitigation["task"].lower()

def test_runbook_does_not_select_post_mitigation_monitoring_as_mitigation():
    result = normalize_runbook(
        {},
        classification={
            "service": "payment-service",
            "severity": "HIGH",
            "events": [
                {
                    "level": "ERROR",
                    "message": "Connection pool exhausted",
                }
            ],
        },
        diagnosis={
            "impact": "Payment requests may fail or be delayed."
        },
        remediation={
            "actions": [
                {
                    "action": (
                        "Confirm incident start time and affected "
                        "payment operations."
                    )
                },
                {
                    "action": (
                        "After an authorized mitigation, monitor pool "
                        "utilization, timeout counts, payment success "
                        "and latency, and gateway 5xx rates."
                    )
                },
                {
                    "action": (
                        "If evidence indicates an ongoing incident, "
                        "present candidate mitigations such as an "
                        "approved traffic adjustment or deployment "
                        "rollback for human review before applying "
                        "any change."
                    )
                },
            ]
        },
    )

    mitigation = next(
        item for item in result["checklist"]
        if item["phase"] == "Mitigate"
    )

    assert "candidate mitigations" in mitigation["task"].lower()
    assert "traffic adjustment" in mitigation["task"].lower()
    assert "monitor pool utilization" not in mitigation["task"].lower()
    assert "human approval" in mitigation["task"].lower()
