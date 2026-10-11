
from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Callable

from langgraph.graph import StateGraph, START, END

from .agents import (
    classify_logs,
    diagnose_incident,
    recommend_remediation,
    synthesize_runbook,
    draft_notification,
    draft_ticket,
)
from .schemas import IncidentState

from .validation import (
    normalize_classification,
    normalize_diagnosis,
    normalize_remediation,
    normalize_runbook,
    normalize_notification,
    normalize_ticket,
)

from .severity_policy import determine_severity

from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

def _utc_now() -> str:
    """Return a UTC timestamp suitable for trace records."""
    return datetime.now(timezone.utc).isoformat()


def _ticket_route_for_severity(severity: str) -> str:
    """Determine whether the workflow should prepare a Jira ticket."""
    normalized = str(severity or "UNKNOWN").upper()

    if normalized in {"HIGH", "CRITICAL"}:
        return "draft_ticket"

    return "assemble"


def _traced_node(
    node_name: str,
    node_function: Callable[[IncidentState], dict],
    trace_events: list[dict[str, Any]],
) -> Callable[[IncidentState], dict]:
    """Wrap a graph node with timing and failure tracing."""

    def run_node(state: IncidentState) -> dict:
        started = perf_counter()

        event = {
            "node": node_name,
            "status": "running",
            "started_at_utc": _utc_now(),
        }
        trace_events.append(event)

        try:
            result = node_function(state)

            event.update({
                "status": "completed",
                "duration_ms": round(
                    (perf_counter() - started) * 1000, 2
                ),
                "output_keys": sorted(result.keys()),
            })

            return result

        except Exception as exc:
            # Do not include full prompts, log contents, or API responses
            # in the trace. Those may contain sensitive information.
            event.update({
                "status": "failed",
                "duration_ms": round(
                    (perf_counter() - started) * 1000, 2
                ),
                "error_type": type(exc).__name__,
                "error_message": (
                    "Node failed. Inspect the local error details "
                    "securely; do not share unredacted logs or secrets."
                ),
            })
            raise

    return run_node



def _classify(state: IncidentState) -> dict:
    output = normalize_classification(
        classify_logs(
            state["log_summary"],
            state.get("extra_context", ""),
        )
    )

    # Use the original parsed logs as the source of truth.
    log_summary = state.get("log_summary", {})
    source_records = (
        log_summary.get("records_for_analysis")
        if isinstance(log_summary, dict)
        else None
    )

    # Replace the LLM-generated event list with the source records.
    # The normalizer will preserve their fields and sort them by timestamp.
    if isinstance(source_records, list):
        output["events"] = source_records
        output = normalize_classification(output)

    # Preserve the LLM's original assessment for comparison.
    model_severity = output.get("severity", "UNKNOWN")

    # Apply the deterministic policy to the original log summary.
    severity, reason = determine_severity(log_summary)

    # Store both assessments and the explanation.
    output["model_assessed_severity"] = model_severity
    output["severity"] = severity
    output["severity_policy_reason"] = reason

    severity = str(output.get("severity", "UNKNOWN")).upper()

    if severity not in {
        "LOW", "MEDIUM", "HIGH", "CRITICAL", "UNKNOWN"
    }:
        severity = "UNKNOWN"

    return {
        "classified_logs": output,
        "severity": severity,
        "service": output.get("service", "unknown-service"),
    }



def _diagnose(state: IncidentState) -> dict:
    output = diagnose_incident(
        state["classified_logs"],
        state.get("rag_context", []),
        state.get("extra_context", ""),
    )
    return {"diagnosis": normalize_diagnosis(output)}
    

def _remediate(state: IncidentState) -> dict:
    output = recommend_remediation(
        state["classified_logs"],
        state["diagnosis"],
        state.get("rag_context", []),
    )
    return {"remediation": normalize_remediation(output)}



def _runbook(state: IncidentState) -> dict:
    output = synthesize_runbook(
        state["classified_logs"],
        state["diagnosis"],
        state["remediation"],
        state.get("rag_context", []),
    )

    return {
        "runbook": normalize_runbook(
            output,
            classification=state.get("classified_logs", {}),
            diagnosis=state.get("diagnosis", {}),
            remediation=state.get("remediation", {}),
        )
    }



def _notify(state: IncidentState) -> dict:
    output = draft_notification(
        state["classified_logs"],
        state["diagnosis"],
        state["remediation"],
    )
    return {
        "notification": normalize_notification(
            output,
            default_severity=state.get("severity", "UNKNOWN"),
        )
    }


def _ticket(state: IncidentState) -> dict:
    output = draft_ticket(
        state["classified_logs"],
        state["diagnosis"],
        state["remediation"],
        state["runbook"],
    )
    return {"ticket": normalize_ticket(output)}


def _assemble(state: IncidentState) -> dict:
    severity = state.get("severity", "UNKNOWN")

    return {
        "result": {
            # Existing placeholder; unique IDs are a later improvement.
            "incident_id": state.get("incident_id", "INC-UNKNOWN"),
            "service": state.get("service", "unknown-service"),
            "severity": severity,
            "classification": state.get("classified_logs", {}),
            "diagnosis": state.get("diagnosis", {}),
            "remediation": state.get("remediation", {}),
            "runbook": state.get("runbook", {}),
            "notification": state.get("notification", {}),
            "ticket": state.get("ticket", {}),
            "safety_note": (
                "Recommendations are advisory. "
                "No remediation commands were executed."
            ),
        }
    }


def build_graph(
    trace_events: list[dict[str, Any]] | None = None,
):
    """Build the graph and attach tracing to each executable node."""

    events = trace_events if trace_events is not None else []
    graph = StateGraph(IncidentState)

    graph.add_node(
        "classify_logs",
        _traced_node("classify_logs", _classify, events),
    )
    graph.add_node(
        "diagnose",
        _traced_node("diagnose", _diagnose, events),
    )
    graph.add_node(
        "remediate",
        _traced_node("remediate", _remediate, events),
    )
    graph.add_node(
        "synthesize_runbook",
        _traced_node("synthesize_runbook", _runbook, events),
    )
    graph.add_node(
        "draft_notification",
        _traced_node("draft_notification", _notify, events),
    )
    graph.add_node(
        "draft_ticket",
        _traced_node("draft_ticket", _ticket, events),
    )
    graph.add_node(
        "assemble",
        _traced_node("assemble", _assemble, events),
    )

    def route_after_notification(state: IncidentState) -> str:
        severity = state.get("severity", "UNKNOWN")
        destination = _ticket_route_for_severity(severity)

        events.append({
            "node": "severity_router",
            "status": "completed",
            "timestamp_utc": _utc_now(),
            "severity": str(severity).upper(),
            "decision": destination,
        })

        return destination

    graph.add_edge(START, "classify_logs")
    graph.add_edge("classify_logs", "diagnose")
    graph.add_edge("diagnose", "remediate")
    graph.add_edge("remediate", "synthesize_runbook")
    graph.add_edge("synthesize_runbook", "draft_notification")

    graph.add_conditional_edges(
        "draft_notification",
        route_after_notification,
        {
            "draft_ticket": "draft_ticket",
            "assemble": "assemble",
        },
    )

    graph.add_edge("draft_ticket", "assemble")
    graph.add_edge("assemble", END)

    return graph.compile()


def run_incident_workflow(
    log_summary: dict,
    rag_context: list[dict],
    extra_context: str = "",
) -> dict:
    """Run the graph in streaming mode and collect execution traces."""

    trace_events: list[dict[str, Any]] = []

    incident_id = (
        f"INC-{datetime.now(timezone.utc):%Y%m%d}-"
        f"{uuid4().hex[:8].upper()}"
    )

    graph = build_graph(trace_events)

    state: IncidentState = {
        "incident_id": incident_id,
        "log_summary": log_summary,
        "rag_context": rag_context,
        "extra_context": extra_context,
        "errors": [],
    }

    # Streaming returns node updates. Merge these into the accumulated
    # state so the final result has the same shape as the previous invoke().
    output_state: dict[str, Any] = dict(state)

    try:
        for update in graph.stream(state, stream_mode="updates"):
            for _node_name, node_update in update.items():
                if isinstance(node_update, dict):
                    output_state.update(node_update)

    except Exception as exc:
        trace_events.append({
            "node": "workflow",
            "status": "failed",
            "timestamp_utc": _utc_now(),
            "error_type": type(exc).__name__,
        })

        return {
            "workflow_status": "failed",
            "error_type": type(exc).__name__,
            "error_message": (
                "Workflow stopped before completing. "
                "Inspect the execution trace for the failed node."
            ),
            "execution_trace": trace_events,
            "safety_note": "No successful complete report is available.",
        }

    result = output_state.get("result", {})

    if not isinstance(result, dict) or not result:
        return {
            "workflow_status": "failed",
            "error_type": "MissingResult",
            "error_message": "The graph ended without assembling a report.",
            "execution_trace": trace_events,
        }

    result["severity"] = output_state.get(
        "severity", result.get("severity", "UNKNOWN")
    )
    result["service"] = output_state.get(
        "service", result.get("service", "unknown-service")
    )
    result["workflow_status"] = "completed"
    result["execution_trace"] = trace_events

    return result
