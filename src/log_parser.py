from __future__ import annotations

from pathlib import Path
import re
import pandas as pd

from .config import get_settings

ALIASES = {
    "timestamp": ["timestamp", "time", "datetime", "date"],
    "service": ["service", "component", "application", "app", "host"],
    "level": ["level", "severity", "log_level", "loglevel", "status"],
    "message": ["message", "msg", "error", "event", "details", "description"],
}


def _canonicalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lower().replace(" ", "_") for c in out.columns]
    rename = {}
    for canonical, aliases in ALIASES.items():
        for col in out.columns:
            if col in aliases:
                rename[col] = canonical
                break
    out = out.rename(columns=rename)
    if "message" not in out.columns:
        # If no recognized message field exists, combine available columns into a text field.
        out["message"] = out.astype(str).agg(" | ".join, axis=1)
    if "timestamp" not in out.columns:
        out["timestamp"] = ""
    if "service" not in out.columns:
        out["service"] = "unknown-service"
    if "level" not in out.columns:
        out["level"] = "UNKNOWN"
    return out


def load_and_normalize_csv(path: str | Path) -> pd.DataFrame:
    settings = get_settings()
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV file not found: {p}")
    if p.stat().st_size > settings.max_upload_mb * 1024 * 1024:
        raise ValueError(f"File exceeds MAX_UPLOAD_MB={settings.max_upload_mb}.")
    # Read as strings to avoid surprising type conversions in log fields.
    df = pd.read_csv(p, dtype=str, keep_default_na=False, on_bad_lines="error")
    if df.empty:
        raise ValueError("CSV contains no data rows.")
    if len(df) > settings.max_log_rows:
        raise ValueError(f"CSV has {len(df)} rows; maximum allowed is {settings.max_log_rows}.")
    df = _canonicalize_columns(df)
    df["level"] = df["level"].astype(str).str.upper().str.strip()
    df["service"] = df["service"].astype(str).str.strip().replace("", "unknown-service")
    df["message"] = df["message"].astype(str).str.strip()
    # Avoid propagating obvious credential-like values into prompts or reports.
    secret_patterns = [
        (re.compile(r"(?i)(password|passwd|token|api[_-]?key|secret)\s*[:=]\s*[^,\s;]+"), r"\1=[REDACTED]"),
        (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
        (re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+"), "Bearer [REDACTED]"),
    ]
    for pattern, replacement in secret_patterns:
        df["message"] = df["message"].apply(lambda x: pattern.sub(replacement, x))
    return df


def sort_logs_by_timestamp(df: pd.DataFrame) -> pd.DataFrame:
    """Sort log records chronologically; place missing or invalid timestamps last."""
    if df.empty or "timestamp" not in df.columns:
        return df.copy()

    out = df.copy()
    out["_source_order"] = range(len(out))

    out["_parsed_timestamp"] = pd.to_datetime(
        out["timestamp"],
        errors="coerce",
        utc=True,
    )

    out = out.sort_values(
        by=["_parsed_timestamp", "_source_order"],
        na_position="last",
    )

    return (
        out.drop(columns=["_source_order", "_parsed_timestamp"])
        .reset_index(drop=True)
    )


def summarize_logs(df: pd.DataFrame) -> dict:
    df = sort_logs_by_timestamp(df)
    settings = get_settings()
    records = df.head(settings.max_log_rows).to_dict(orient="records")
    levels = df["level"].value_counts().to_dict()
    services = df["service"].value_counts().to_dict()
    error_rows = df[df["level"].isin(["ERROR", "CRITICAL", "FATAL", "WARN", "WARNING"])]
    examples = error_rows.head(100).to_dict(orient="records")
    text = "\n".join(
        f"{r.get('timestamp','')} | {r.get('service','')} | {r.get('level','')} | {r.get('message','')}"
        for r in records[:250]
    )
    query = "Operational incident errors " + text[:8000]
    return {
        "row_count": len(df),
        "level_counts": levels,
        "service_counts": services,
        "error_examples": examples,
        "records_for_analysis": records[:250],
        "query": query,
    }
