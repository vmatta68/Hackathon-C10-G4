from __future__ import annotations

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


def _classify(state: IncidentState) -> dict:
    output = classify_logs(state["log_summary"], state.get("extra_context", ""))
    severity = str(output.get("severity", "UNKNOWN")).upper()
    if severity not in {"LOW", "MEDIUM", "HIGH", "CRITICAL", "UNKNOWN"}:
        severity = "UNKNOWN"
    return {"classified_logs": output, "severity": severity, "service": output.get("service", "unknown-service")}


def _diagnose(state: IncidentState) -> dict:
    return {"diagnosis": diagnose_incident(
        state["classified_logs"], state.get("rag_context", []), state.get("extra_context", "")
    )}


def _remediate(state: IncidentState) -> dict:
    return {"remediation": recommend_remediation(
        state["classified_logs"], state["diagnosis"], state.get("rag_context", [])
    )}


def _runbook(state: IncidentState) -> dict:
    return {"runbook": synthesize_runbook(
        state["classified_logs"], state["diagnosis"], state["remediation"], state.get("rag_context", [])
    )}


def _notify(state: IncidentState) -> dict:
    return {"notification": draft_notification(
        state["classified_logs"], state["diagnosis"], state["remediation"]
    )}


def _ticket(state: IncidentState) -> dict:
    return {"ticket": draft_ticket(
        state["classified_logs"], state["diagnosis"], state["remediation"], state["runbook"]
    )}


def _assemble(state: IncidentState) -> dict:
    severity = state.get("severity", "UNKNOWN")
    return {"result": {
        "incident_id": "INC-DEMO-001",
        "service": state.get("service", "unknown-service"),
        "severity": severity,
        "classification": state.get("classified_logs", {}),
        "diagnosis": state.get("diagnosis", {}),
        "remediation": state.get("remediation", {}),
        "runbook": state.get("runbook", {}),
        "notification": state.get("notification", {}),
        "ticket": state.get("ticket", {}),
        "safety_note": "Recommendations are advisory. No remediation commands were executed.",
    }}


def build_graph():
    graph = StateGraph(IncidentState)
    graph.add_node("classify_logs", _classify)
    graph.add_node("diagnose", _diagnose)
    graph.add_node("remediate", _remediate)
    graph.add_node("synthesize_runbook", _runbook)
    graph.add_node("draft_notification", _notify)
    graph.add_node("draft_ticket", _ticket)
    graph.add_node("assemble", _assemble)

    graph.add_edge(START, "classify_logs")
    graph.add_edge("classify_logs", "diagnose")
    graph.add_edge("diagnose", "remediate")
    graph.add_edge("remediate", "synthesize_runbook")
    graph.add_edge("synthesize_runbook", "draft_notification")
    graph.add_conditional_edges(
        "draft_notification",
        lambda state: "draft_ticket" if state.get("severity") in {"HIGH", "CRITICAL"} else "assemble",
        {"draft_ticket": "draft_ticket", "assemble": "assemble"},
    )
    graph.add_edge("draft_ticket", "assemble")
    graph.add_edge("assemble", END)
    return graph.compile()


def run_incident_workflow(log_summary: dict, rag_context: list[dict], extra_context: str = "") -> dict:
    app = build_graph()
    state: IncidentState = {
        "log_summary": log_summary,
        "rag_context": rag_context,
        "extra_context": extra_context,
        "errors": [],
    }
    output = app.invoke(state)
    result = output.get("result", {})
    # Keep top-level fields convenient for UI dispatch and downstream use.
    result["severity"] = output.get("severity", result.get("severity", "UNKNOWN"))
    result["service"] = output.get("service", result.get("service", "unknown-service"))
    return result
