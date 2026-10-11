
import pandas as pd

from src.log_parser import sort_logs_by_timestamp


def test_logs_are_sorted_and_missing_timestamps_go_last():
    df = pd.DataFrame([
        {"timestamp": "2026-10-10T10:03:00Z", "message": "third"},
        {"timestamp": "", "message": "missing"},
        {"timestamp": "2026-10-10T10:01:00Z", "message": "first"},
        {"timestamp": "invalid-date", "message": "invalid"},
        {"timestamp": "2026-10-10T10:02:00Z", "message": "second"},
    ])

    result = sort_logs_by_timestamp(df)

    assert result["message"].tolist() == [
        "first",
        "second",
        "third",
        "missing",
        "invalid",
    ]

    # Confirm the original DataFrame was not modified.
    assert df["message"].tolist() == [
        "third",
        "missing",
        "first",
        "invalid",
        "second",
    ]
