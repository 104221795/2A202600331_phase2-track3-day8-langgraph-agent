"""Optional Streamlit UI for the LangGraph support-ticket workflow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

try:
    from .graph import build_graph
    from .persistence import build_checkpointer
    from .scenarios import load_scenarios
    from .state import Route, Scenario, initial_state
except ImportError:  # pragma: no cover - Streamlit executes files as scripts
    from langgraph_agent_lab.graph import build_graph
    from langgraph_agent_lab.persistence import build_checkpointer
    from langgraph_agent_lab.scenarios import load_scenarios
    from langgraph_agent_lab.state import Route, Scenario, initial_state

SCENARIOS_PATH = Path("data/sample/scenarios.jsonl")
GRAPH_PATH = Path("docs/graph.mmd")
STATE_HISTORY_PATH = Path("outputs/state_history.json")

ROUTE_HELP = {
    "simple": "Safe direct answer",
    "tool": "Support lookup with evaluation",
    "missing_info": "Clarification instead of guessing",
    "risky": "Human approval required before action",
    "error": "Retry loop with dead-letter fallback",
}


def load_demo_scenarios(path: str | Path = SCENARIOS_PATH) -> list[Scenario]:
    """Load demo scenarios for the UI dropdown."""
    return load_scenarios(path)


def scenario_label(scenario: Scenario) -> str:
    """Return a compact dropdown label."""
    return f"{scenario.id} | {scenario.expected_route.value} | {scenario.query}"


def run_ticket(
    query: str,
    *,
    scenario_id: str = "ui-session",
    expected_route: Route = Route.SIMPLE,
    requires_approval: bool = False,
    should_retry: bool = False,
    max_attempts: int = 3,
    approval_approved: bool = True,
) -> dict[str, Any]:
    """Run one ad-hoc or selected ticket through the graph."""
    scenario = Scenario(
        id=scenario_id,
        query=query,
        expected_route=expected_route,
        requires_approval=requires_approval,
        should_retry=should_retry,
        max_attempts=max_attempts,
    )
    state = initial_state(scenario)
    state["thread_id"] = f"thread-ui-{scenario_id}"
    if requires_approval:
        state["approval_decision"] = {
            "approved": approval_approved,
            "reviewer": "streamlit-reviewer",
            "comment": "approved in demo UI" if approval_approved else "rejected in demo UI",
        }

    graph = build_graph(checkpointer=build_checkpointer("memory"))
    return graph.invoke(state, config={"configurable": {"thread_id": state["thread_id"]}})


def run_scenario(scenario: Scenario, *, approval_approved: bool = True) -> dict[str, Any]:
    """Run a scenario from the sample benchmark file."""
    return run_ticket(
        scenario.query,
        scenario_id=scenario.id,
        expected_route=scenario.expected_route,
        requires_approval=scenario.requires_approval,
        should_retry=scenario.should_retry,
        max_attempts=scenario.max_attempts,
        approval_approved=approval_approved,
    )


def build_hitl_review(
    *,
    query: str,
    scenario_id: str,
    expected_route: Route,
    should_retry: bool,
    max_attempts: int,
) -> dict[str, Any]:
    """Create the pending human-review payload shown before approval."""
    return {
        "query": query,
        "scenario_id": scenario_id,
        "expected_route": expected_route,
        "should_retry": should_retry,
        "max_attempts": max_attempts,
        "proposed_action": f"Stage high-risk support action for review: {query}",
    }


def complete_hitl_review(review: dict[str, Any], *, approved: bool) -> dict[str, Any]:
    """Resume the demo workflow after a human approval decision."""
    return run_ticket(
        str(review["query"]),
        scenario_id=str(review["scenario_id"]),
        expected_route=Route(str(review["expected_route"])),
        requires_approval=True,
        should_retry=bool(review["should_retry"]),
        max_attempts=int(review["max_attempts"]),
        approval_approved=approved,
    )


def summarize_state_for_ui(state: dict[str, Any]) -> dict[str, Any]:
    """Return a compact view model for Streamlit rendering."""
    events = state.get("events", []) or []
    approval = state.get("approval") or {}
    route = str(state.get("route", "unknown"))
    errors = list(state.get("errors", []) or [])
    return {
        "scenario_id": state.get("scenario_id", "custom"),
        "query": state.get("query", ""),
        "route": route,
        "route_help": ROUTE_HELP.get(route, "Custom route"),
        "risk_level": state.get("risk_level", "unknown"),
        "classification_reason": state.get("classification_reason", ""),
        "attempt": int(state.get("attempt", 0)),
        "max_attempts": int(state.get("max_attempts", 3)),
        "requires_approval": bool(state.get("requires_approval")),
        "approval_observed": bool(approval),
        "approval_approved": approval.get("approved"),
        "proposed_action": state.get("proposed_action") or "",
        "final_answer": state.get("final_answer") or state.get("pending_question") or "",
        "tool_results": list(state.get("tool_results", []) or []),
        "errors": errors,
        "is_dead_letter": any("dead_letter" in error for error in errors),
        "decision_label": "approved" if approval.get("approved") else "rejected"
        if approval
        else "not required",
        "events": [
            {
                "step": index,
                "node": event.get("node"),
                "type": event.get("event_type"),
                "message": event.get("message"),
            }
            for index, event in enumerate(events, start=1)
        ],
    }


def _status_text(summary: dict[str, Any]) -> str:
    if summary["is_dead_letter"]:
        return "Manual review"
    if summary["requires_approval"] and summary["approval_approved"] is False:
        return "Rejected safely"
    if summary["errors"]:
        return "Recovered"
    return "Completed"


def _route_badge(summary: dict[str, Any]) -> str:
    return f"{summary['route'].upper()} - {summary['route_help']}"


def resolve_hitl_button_decision(*, approve_clicked: bool, reject_clicked: bool) -> bool | None:
    """Map explicit UI buttons to an approval decision."""
    if approve_clicked:
        return True
    if reject_clicked:
        return False
    return None


def _clear_review_state() -> None:
    import streamlit as st

    st.session_state.pop("pending_review", None)


def load_text_artifact(path: str | Path) -> str:
    """Read a text artifact if it exists."""
    artifact_path = Path(path)
    if not artifact_path.exists():
        return ""
    return artifact_path.read_text(encoding="utf-8")


def load_json_artifact(path: str | Path) -> dict[str, Any]:
    """Read a JSON artifact if it exists."""
    text = load_text_artifact(path)
    if not text:
        return {}
    return cast(dict[str, Any], json.loads(text))


def summarize_history_artifact(payload: dict[str, Any]) -> dict[str, Any]:
    """Return compact checkpoint-history evidence for display."""
    history = payload.get("history", []) or []
    retry_steps = [
        item
        for item in history
        if item.get("evaluation_result") == "needs_retry"
        or item.get("next") == ["retry"]
    ]
    return {
        "scenario_id": payload.get("scenario_id", ""),
        "thread_id": payload.get("thread_id", ""),
        "expected_route": payload.get("expected_route", ""),
        "actual_route": payload.get("actual_route", ""),
        "history_length": payload.get("history_length", len(history)),
        "retry_evidence_count": len(retry_steps),
        "final_answer_present": payload.get("final_answer_present", False),
    }


def _render_evidence_tab() -> None:
    import streamlit as st

    st.subheader("Graph diagram")
    graph_source = load_text_artifact(GRAPH_PATH)
    if graph_source:
        st.code(graph_source, language="markdown")
    else:
        st.warning("Graph diagram not found. Run `export-graph` from RUNNING.md.")

    st.subheader("Checkpoint history / time travel")
    history_payload = load_json_artifact(STATE_HISTORY_PATH)
    if not history_payload:
        st.warning("State history not found. Run `demo-history` from RUNNING.md.")
        return

    summary = summarize_history_artifact(history_payload)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Scenario", str(summary["scenario_id"]))
    c2.metric("Thread", str(summary["thread_id"]))
    c3.metric("Snapshots", str(summary["history_length"]))
    c4.metric("Retry evidence", str(summary["retry_evidence_count"]))

    st.json(
        {
            "expected_route": summary["expected_route"],
            "actual_route": summary["actual_route"],
            "final_answer_present": summary["final_answer_present"],
        }
    )

    history = history_payload.get("history", []) or []
    st.dataframe(history, use_container_width=True, hide_index=True)

    with st.expander("Raw checkpoint history JSON"):
        st.json(history_payload)


def main() -> None:
    """Launch the Streamlit review UI."""
    try:
        import streamlit as st
    except ImportError as exc:  # pragma: no cover - only hit outside test env
        raise RuntimeError("Install the UI extra first: pip install -e '.[ui]'") from exc

    st.set_page_config(page_title="LangGraph Support Agent", layout="wide")
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.25rem; padding-bottom: 2rem; }
        div[data-testid="stMetric"] {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 14px 16px;
        }
        div[data-testid="stAlert"] { border-radius: 8px; }
        .demo-header {
            border-bottom: 1px solid #e5e7eb;
            padding-bottom: 0.75rem;
            margin-bottom: 1rem;
        }
        .demo-kicker {
            color: #475569;
            font-size: 0.92rem;
            margin-top: -0.6rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    scenarios = load_demo_scenarios()
    labels = [scenario_label(scenario) for scenario in scenarios]

    st.markdown('<div class="demo-header">', unsafe_allow_html=True)
    st.title("LangGraph Support Agent Demo")
    st.markdown(
        '<div class="demo-kicker">Scenario runner with routing, retry, HITL, '
        "checkpoint-ready metrics, and audit visibility.</div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    workflow_tab, evidence_tab = st.tabs(["Workflow demo", "Bonus evidence"])

    with evidence_tab:
        _render_evidence_tab()

    with workflow_tab:
        with st.sidebar:
            mode = st.radio("Input mode", ["Scenario benchmark", "Custom ticket"])

            selected = scenarios[0]
            if mode == "Scenario benchmark":
                label = cast(str, st.selectbox("Testing scenario", labels, index=0))
                selected = scenarios[labels.index(label)]
                query = st.text_area("Ticket text", selected.query, height=120)
                max_attempts = selected.max_attempts
                should_retry = selected.should_retry
                requires_approval = selected.requires_approval
                expected_route = selected.expected_route
                scenario_id = selected.id
            else:
                query = st.text_area(
                    "Ticket text",
                    "Refund this customer and send confirmation email",
                    height=120,
                )
                expected_route = Route.SIMPLE
                requires_approval = st.checkbox("Requires approval", value=True)
                should_retry = st.checkbox("Simulate transient tool failure", value=False)
                max_attempts = st.slider("Max attempts", min_value=1, max_value=5, value=3)
                scenario_id = "custom"

            run_clicked = st.button("Run workflow", type="primary", use_container_width=True)

        if run_clicked and requires_approval:
            st.session_state.pending_review = build_hitl_review(
                query=query,
                scenario_id=scenario_id,
                expected_route=expected_route,
                should_retry=should_retry,
                max_attempts=max_attempts,
            )
            st.session_state.pop("last_state", None)
        elif run_clicked or (
            "last_state" not in st.session_state
            and "pending_review" not in st.session_state
        ):
            _clear_review_state()
            st.session_state.last_state = run_ticket(
                query,
                scenario_id=scenario_id,
                expected_route=expected_route,
                requires_approval=requires_approval,
                should_retry=should_retry,
                max_attempts=max_attempts,
                approval_approved=True,
            )

        if "pending_review" in st.session_state:
            review = st.session_state.pending_review
            st.warning("Workflow paused: human approval is required before this action continues.")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Scenario", review["scenario_id"])
            c2.metric("Route", "risky")
            c3.metric("Status", "Awaiting human review")
            c4.metric("Decision", "pending")

            left, right = st.columns([1.15, 0.85])
            with left:
                st.subheader("Ticket")
                st.write(review["query"])
                st.subheader("Proposed high-risk action")
                st.write(review["proposed_action"])
            with right:
                st.subheader("Human decision")
                approve_col, reject_col = st.columns(2)
                with approve_col:
                    approve_clicked = st.button("Approve", type="primary", use_container_width=True)
                with reject_col:
                    reject_clicked = st.button("Reject", use_container_width=True)

                decision = resolve_hitl_button_decision(
                    approve_clicked=approve_clicked,
                    reject_clicked=reject_clicked,
                )
                if decision is not None:
                    st.session_state.last_state = complete_hitl_review(review, approved=decision)
                    _clear_review_state()
                    st.rerun()

                st.json({"approval_observed": False, "approved": None, "status": "pending"})
            return

        summary = summarize_state_for_ui(st.session_state.last_state)

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Scenario", summary["scenario_id"])
        c2.metric("Route", summary["route"])
        c3.metric("Status", _status_text(summary))
        c4.metric("Attempts", f"{summary['attempt']}/{summary['max_attempts']}")
        if summary["approval_observed"]:
            approval_text = "approved" if summary["approval_approved"] else "not approved"
        else:
            approval_text = "not required"
        c5.metric("Approval", approval_text)

        if summary["is_dead_letter"]:
            st.error("This run exhausted retries and was sent to manual review.")
        elif summary["requires_approval"] and summary["approval_approved"] is False:
            st.warning("The risky action was rejected and routed to clarification.")
        elif summary["errors"]:
            st.warning("Transient failures were observed, then the workflow recovered.")
        else:
            st.success("Workflow completed successfully.")

        left, right = st.columns([1.15, 0.85])
        with left:
            st.subheader("Ticket")
            st.write(summary["query"])

            st.subheader("Final response")
            st.write(summary["final_answer"])

            st.subheader("Routing decision")
            st.info(_route_badge(summary))
            st.caption(summary["classification_reason"])

            if summary["proposed_action"]:
                st.subheader("HITL review")
                st.write(summary["proposed_action"])
                st.write(
                    {
                        "approval_observed": summary["approval_observed"],
                        "approved": summary["approval_approved"],
                    }
                )

        with right:
            st.subheader("Tool results")
            st.json(summary["tool_results"])

            st.subheader("Errors and retries")
            st.json(summary["errors"])

        st.subheader("Audit timeline")
        st.dataframe(summary["events"], use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
