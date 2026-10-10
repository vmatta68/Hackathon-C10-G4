from pathlib import Path
import pandas as pd

from src.log_parser import _canonicalize_columns
from src.rag import retrieve_runbook_context


def test_column_aliases_are_normalized():
    df = pd.DataFrame([{"time": "now", "component": "api", "severity": "ERROR", "msg": "timeout"}])
    normalized = _canonicalize_columns(df)
    assert {"timestamp", "service", "level", "message"}.issubset(normalized.columns)
    assert normalized.loc[0, "message"] == "timeout"


def test_rag_retrieves_relevant_runbook(tmp_path: Path):
    (tmp_path / "db.md").write_text("Database connection pool exhaustion and connection timeout investigation.", encoding="utf-8")
    (tmp_path / "ui.md").write_text("CSS layout and button styling.", encoding="utf-8")
    results = retrieve_runbook_context("database connection timeout", tmp_path, top_k=2)
    assert results
    assert results[0]["source"] == "db.md"
