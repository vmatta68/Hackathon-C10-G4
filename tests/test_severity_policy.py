
from src.severity_policy import determine_severity


def test_pool_exhaustion_with_http_503_is_high():
    summary = {
        "records_for_analysis": [
            {
                "level": "ERROR",
                "message": "Connection pool exhausted",
            },
            {
                "level": "ERROR",
                "message": "HTTP 503 returned by service",
            },
        ]
    }

    severity, _ = determine_severity(summary)

    assert severity == "HIGH"


def test_readiness_failure_with_http_502_is_high():
    summary = {
        "records_for_analysis": [
            {
                "level": "ERROR",
                "message": "Readiness probe failed",
            },
            {
                "level": "ERROR",
                "message": "HTTP 502 received from upstream",
            },
        ]
    }

    severity, _ = determine_severity(summary)

    assert severity == "HIGH"


def test_authentication_errors_without_5xx_are_medium():
    summary = {
        "records_for_analysis": [
            {
                "level": "ERROR",
                "message": "Authentication failed with HTTP 401",
            },
            {
                "level": "ERROR",
                "message": "Invalid credentials",
            },
        ]
    }

    severity, _ = determine_severity(summary)

    assert severity == "MEDIUM"


def test_ambiguous_timeout_without_5xx_is_medium():
    summary = {
        "records_for_analysis": [
            {
                "level": "WARNING",
                "message": "Upstream request timed out",
            },
        ]
    }

    severity, _ = determine_severity(summary)

    assert severity == "MEDIUM"


def test_explicit_critical_level_is_critical():
    summary = {
        "records_for_analysis": [
            {
                "level": "CRITICAL",
                "message": "Service failure detected",
            },
        ]
    }

    severity, _ = determine_severity(summary)

    assert severity == "CRITICAL"


def test_empty_summary_returns_unknown():
    severity, reason = determine_severity(
        {"records_for_analysis": []}
    )

    assert severity == "UNKNOWN"
    assert reason
