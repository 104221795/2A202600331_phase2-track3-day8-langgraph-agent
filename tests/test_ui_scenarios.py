from langgraph_agent_lab.nodes import classify_node, intake_node
from langgraph_agent_lab.ui import summarize_state_for_ui


def _classify(query: str) -> dict:
    state = {"query": query, "messages": [], "events": []}
    state.update(intake_node(state))
    return classify_node(state)


def test_ui_summary_exposes_review_fields():
    summary = summarize_state_for_ui(
        {
            "route": "risky",
            "risk_level": "high",
            "classification_reason": "risky keyword(s): refund",
            "attempt": 1,
            "max_attempts": 3,
            "approval": {"approved": True},
            "final_answer": "Approved action completed.",
            "tool_results": ["OK"],
            "errors": [],
            "events": [{"node": "approval", "event_type": "completed", "message": "approved=True"}],
        }
    )

    assert summary["route"] == "risky"
    assert summary["approval_observed"] is True
    assert summary["events"][0]["node"] == "approval"


def test_ui_routing_scenarios_are_keyword_based():
    assert _classify("Cancel order 555 immediately")["route"] == "risky"
    assert _classify("Can you check shipment status?")["route"] == "tool"
    assert _classify("Please fix it")["route"] == "missing_info"
    assert _classify("The backend is unavailable and crashing")["route"] == "error"
