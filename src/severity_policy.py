
import re
from typing import Any


def _get_records(log_summary: dict[str, Any]) -> list[Any]:
    """Get the individual log records from the parsed log summary."""
    for key in ("records_for_analysis", "records", "events", "logs"):
        records = log_summary.get(key)

        if isinstance(records, list):
            return records

    return []


def _record_text(record: Any) -> str:
    """Convert a log record into searchable text."""
    if isinstance(record, dict):
        return " ".join(str(value) for value in record.values())

    return str(record) if record is not None else ""


def _record_level(record: Any) -> str:
    """Extract the log level when the record provides one."""
    if not isinstance(record, dict):
        return ""

    for key in ("level", "log_level", "loglevel", "severity"):
        value = record.get(key)

        if value is not None and str(value).strip():
            return str(value).strip().upper()

    return ""


def determine_severity(
    log_summary: dict[str, Any],
) -> tuple[str, str]:
    """
    Apply deterministic baseline rules to an incident's log records.

    Returns:
        A tuple containing (severity, explanation).
    """
    records = _get_records(log_summary)

    usable_records = [
        record
        for record in records
        if _record_text(record).strip()
    ]

    if not usable_records:
        return "UNKNOWN", "No usable log records were provided."

    record_texts = [_record_text(record) for record in usable_records]
    combined_text = "\n".join(record_texts).lower()

    levels = [_record_level(record) for record in usable_records]

    error_count = sum(
        level in {"ERROR", "ERR", "FATAL", "CRITICAL"}
        for level in levels
    )

    has_critical_level = any(
        level in {"CRITICAL", "FATAL"}
        for level in levels
    )

    # Rule 1: Explicit critical conditions.
    critical_phrases = (
        "complete outage",
        "all requests failing",
        "entire service unavailable",
    )

    if has_critical_level:
        return (
            "CRITICAL",
            "At least one log record has CRITICAL or FATAL severity.",
        )

    if any(phrase in combined_text for phrase in critical_phrases):
        return (
            "CRITICAL",
            "Logs contain an explicit broad-service-outage indicator.",
        )

    # Rule 2: Identify HTTP 5xx responses.
    has_http_5xx = bool(
        re.search(r"\b5\d{2}\b", combined_text)
    )

    # Rule 3: High severity patterns.
    pool_exhausted = bool(
        re.search(
            r"pool\s+exhausted|connection\s+pool\s+exhaustion",
            combined_text,
        )
    )

    readiness_failed = bool(
        re.search(
            r"readiness\s+probe.{0,80}(?:fail|error)"
            r"|(?:fail|error).{0,80}readiness\s+probe",
            combined_text,
        )
    )

    if pool_exhausted and has_http_5xx:
        return (
            "HIGH",
            "Connection-pool exhaustion and HTTP 5xx responses were detected.",
        )

    if readiness_failed and has_http_5xx:
        return (
            "HIGH",
            "A failed readiness probe and HTTP 5xx responses were detected.",
        )

    if has_http_5xx and error_count >= 3:
        return (
            "HIGH",
            "HTTP 5xx responses and at least three ERROR/FATAL records were detected.",
        )

    # Rule 4: Other error, warning, and failure conditions.
    warning_count = sum(level in {"WARN", "WARNING"} for level in levels)

    error_or_warning_text = bool(
        re.search(
            r"\b(error|exception|failed|failure|timeout|warning|warn)\b",
            combined_text,
        )
    )

    if error_count > 0 or warning_count > 0 or error_or_warning_text:
        return (
            "MEDIUM",
            "Errors, warnings, or failure indicators were detected, "
            "but no higher-severity rule matched.",
        )

    # Rule 5: Records exist, but no elevated condition was found.
    return (
        "LOW",
        "Usable log records were found without a detected error or warning condition.",
    )
