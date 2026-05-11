"""Optional Streamlit UI for the LangGraph support-ticket workflow."""

from __future__ import annotations

from typing import Any

from .graph import build_graph
from .persistence import build_checkpointer
from .state import Route, Scenario, initial_state


def run_ticket(
    query: str,
    *,
    max_attempts: int = 3,
    thread_id: str = "ui-session",
) -> dict[str, Any]:
    """Run one ad-hoc ticket through the graph for UI and smoke tests."""
    scenario = Scenario(
        id=thread_id,
        query=query,
        expected_route=Route.SIMPLE,
        max_attempts=max_attempts,
    )
    state = initial_state(scenario)
    state["thread_id"] = f"thread-{thread_id}"
    graph = build_graph(checkpointer=build_checkpointer("memory"))
    return graph.invoke(state, config={"configurable": {"thread_id": state["thread_id"]}})


def summarize_state_for_ui(state: dict[str, Any]) -> dict[str, Any]:
    """Return a compact view model for Streamlit rendering."""
    events = state.get("events", []) or []
    return {
        "route": state.get("route", "unknown"),
        "risk_level": state.get("risk_level", "unknown"),
        "classification_reason": state.get("classification_reason", ""),
        "attempt": int(state.get("attempt", 0)),
        "max_attempts": int(state.get("max_attempts", 3)),
        "approval_observed": state.get("approval") is not None,
        "final_answer": state.get("final_answer") or state.get("pending_question") or "",
        "tool_results": list(state.get("tool_results", []) or []),
        "errors": list(state.get("errors", []) or []),
        "events": [
            {
                "node": event.get("node"),
                "event_type": event.get("event_type"),
                "message": event.get("message"),
            }
            for event in events
        ],
    }


def main() -> None:
    """Launch the Streamlit review UI."""
    try:
        import streamlit as st
    except ImportError as exc:  # pragma: no cover - only hit outside test env
        raise RuntimeError("Install the UI extra first: pip install -e '.[ui]'") from exc

    st.set_page_config(page_title="LangGraph Support Agent", layout="wide")
    st.title("LangGraph Support Agent")

    with st.sidebar:
        query = st.text_area(
            "Ticket",
            "Refund this customer and send confirmation email",
            height=120,
        )
        max_attempts = st.slider("Max attempts", min_value=1, max_value=5, value=3)
        run_clicked = st.button("Run ticket", type="primary")

    if run_clicked or "last_state" not in st.session_state:
        st.session_state.last_state = run_ticket(query, max_attempts=max_attempts)

    summary = summarize_state_for_ui(st.session_state.last_state)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Route", summary["route"])
    c2.metric("Risk", summary["risk_level"])
    c3.metric("Attempts", f"{summary['attempt']}/{summary['max_attempts']}")
    c4.metric("Approval", "observed" if summary["approval_observed"] else "not required")

    st.subheader("Final response")
    st.write(summary["final_answer"])

    st.subheader("Routing rationale")
    st.write(summary["classification_reason"])

    st.subheader("Tool results")
    st.json(summary["tool_results"])

    st.subheader("Audit events")
    st.dataframe(summary["events"], use_container_width=True)

    if summary["errors"]:
        st.subheader("Errors")
        st.json(summary["errors"])


if __name__ == "__main__":
    main()
