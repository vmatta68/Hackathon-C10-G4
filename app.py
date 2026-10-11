from __future__ import annotations

import json
import os
from pathlib import Path

import gradio as gr
import pandas as pd

from src.config import get_settings
from src.graph import run_incident_workflow
from src.integrations import post_slack_notification, create_jira_issue
from src.log_parser import load_and_normalize_csv, summarize_logs
from src.rag import retrieve_runbook_context

ROOT = Path(__file__).parent
SAMPLE = ROOT / "data" / "sample_incident_logs.csv"


def _read_upload(file_obj) -> pd.DataFrame:
    if file_obj is None:
        return pd.read_csv(SAMPLE)
    path = getattr(file_obj, "name", None) or str(file_obj)
    return load_and_normalize_csv(path)


def analyze(file_obj, extra_context: str):
    try:
        settings = get_settings()
        df = _read_upload(file_obj)
        
        summary = summarize_logs(df)
        
        # Keep the LLM input manageable for a limited credit balance.
        summary["records_for_analysis"] = (
            summary.get("records_for_analysis", [])[:40]
        )
        summary["error_examples"] = (
            summary.get("error_examples", [])[:20]
        )
        summary["query"] = summary.get("query", "")[:3000]

        rag_context = retrieve_runbook_context(
            query=summary["query"],
            runbook_dir=ROOT / "data" / "runbooks",
            top_k=min(settings.rag_top_k, 2),
        )

        result = run_incident_workflow(
            log_summary=summary,
            rag_context=rag_context,
            extra_context=(extra_context or "").strip(),
        )
        result["input_summary"] = summary
        result["retrieved_runbooks"] = rag_context
        pretty = json.dumps(result, indent=2, ensure_ascii=False)
        headline = (
            f"**Incident analysis complete** · Severity: **{result.get('severity', 'UNKNOWN')}** · "
            f"Service: **{result.get('service', 'unknown')}**"
        )
        return headline, pretty, result
    
    except pd.errors.ParserError as exc:
        return (
            "**CSV validation error:** The uploaded file contains "
            "an invalid CSV row. Please check that every row has "
            "the same number of columns as the header and that "
            "fields containing commas are correctly quoted.\n\n"
            f"**Technical details:** {exc}",
            "No result generated.",
            None,
        )

    except Exception as exc:
        return (
            f"**Analysis failed:** {type(exc).__name__}: {exc}",
            "No result generated.",
            None,
        )


def dispatch_actions(result, approved: bool):
    if not result:
        return "Run an analysis first."
    if not approved:
        return "No external actions taken. Check the approval box before dispatching."
    settings = get_settings()
    outcomes = []

    if settings.slack_webhook_url:
        try:
            response = post_slack_notification(settings.slack_webhook_url, result)
            outcomes.append(f"Slack: {response}")
        except Exception as exc:
            outcomes.append(f"Slack failed: {type(exc).__name__}: {exc}")
    else:
        outcomes.append("Slack: not configured; skipped.")

    if settings.jira_is_configured and result.get("severity") in {"CRITICAL", "HIGH"}:
        try:
            response = create_jira_issue(settings, result)
            outcomes.append(f"Jira: created {response.get('key', 'issue')}")
        except Exception as exc:
            outcomes.append(f"Jira failed: {type(exc).__name__}: {exc}")
    else:
        outcomes.append("Jira: not configured or severity is below HIGH; skipped.")

    return "\n".join(outcomes)


with gr.Blocks(title="Multi-agent DevOps Incident Analysis Suite") as demo:
    gr.Markdown(
        """
        # Multi-agent DevOps Incident Analysis Suite
        Upload operational CSV logs, retrieve relevant runbook guidance, and analyze the incident with a LangGraph workflow.

        **Safety:** Use synthetic/redacted logs. Recommendations are advisory. No production commands are executed.
        """
    )
    with gr.Row():
        upload = gr.File(label="Upload CSV logs (optional; sample used if empty)", file_types=[".csv"], type="filepath")
        extra = gr.Textbox(
            label="Optional incident context",
            placeholder="e.g., deployment occurred shortly before errors began",
            lines=3,
        )
    analyze_btn = gr.Button("Analyze incident", variant="primary")
    status = gr.Markdown()
    report = gr.Code(label="Structured incident report (JSON)", language="json")
    result_state = gr.State(None)

    analyze_btn.click(
        fn=analyze,
        inputs=[upload, extra],
        outputs=[status, report, result_state],
    )

    gr.Markdown("## External actions")
    approval = gr.Checkbox(
        label="I reviewed the report and approve sending a Slack notification and/or creating a Jira issue.",
        value=False,
    )
    dispatch_btn = gr.Button("Dispatch approved actions")
    action_status = gr.Textbox(label="Dispatch results", lines=4, interactive=False)
    dispatch_btn.click(
        fn=dispatch_actions,
        inputs=[result_state, approval],
        outputs=[action_status],
    )

    gr.Markdown(
        """
        ---
        **MVP notes:** Slack/Jira are optional and remain disabled until configured. The RAG component uses local runbook text files and TF-IDF retrieval.
        """
    )

if __name__ == "__main__":
    demo.queue().launch()
