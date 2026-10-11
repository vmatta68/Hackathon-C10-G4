import src.graph as graph


def test_classification_restores_all_source_events_and_sorts_them(
    monkeypatch,
):
    log_summary = {
        "records_for_analysis": [
            {
                "timestamp": "2026-10-11T10:03:00Z",
                "level": "ERROR",
                "message": "Later error",
                "service": "payment-service",
            },
            {
                "timestamp": "2026-10-11T10:01:00Z",
                "level": "WARN",
                "message": "Earlier warning",
                "service": "payment-service",
            },
            {
                "timestamp": "",
                "level": "INFO",
                "message": "Missing timestamp",
                "service": "payment-service",
            },
        ]
    }

    # Simulate an LLM that returns only one of the three source events.
    def fake_classify_logs(_summary, _extra_context):
        return {
            "service": "payment-service",
            "severity": "MEDIUM",
            "events": [
                {
                    "timestamp": "2026-10-11T10:03:00Z",
                    "level": "ERROR",
                    "message": "Later error",
                }
            ],
        }

    # Isolate classification from API calls and test the policy integration.
    monkeypatch.setattr(
        graph, "classify_logs", fake_classify_logs
    )
    monkeypatch.setattr(
        graph,
        "determine_severity",
        lambda _summary: (
            "HIGH",
            "Test policy detected a high-severity incident.",
        ),
    )

    result = graph._classify({
        "log_summary": log_summary,
        "extra_context": "",
    })

    classified = result["classified_logs"]
    events = classified["events"]

    # All original source events must be present.
    assert len(events) == 3

    # Events must be chronologically ordered; missing timestamps go last.
    assert [event["message"] for event in events] == [
        "Earlier warning",
        "Later error",
        "Missing timestamp",
    ]

    # Preserve the model assessment while using the policy's severity.
    assert classified["model_assessed_severity"] == "MEDIUM"
    assert classified["severity"] == "HIGH"
    assert result["severity"] == "HIGH"

    # Verify the original records retain their service information.
    assert all(
        event["service"] == "payment-service"
        for event in events
    )