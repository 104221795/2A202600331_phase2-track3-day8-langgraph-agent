from langgraph_agent_lab.nodes import classify_node, intake_node
from langgraph_agent_lab.state import Route, Scenario
from langgraph_agent_lab.ui import (
    load_demo_scenarios,
    run_scenario,
    scenario_label,
    summarize_state_for_ui,
)


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
    assert summary["route_help"] == "Human approval required before action"


def test_ui_routing_scenarios_are_keyword_based():
    assert _classify("Cancel order 555 immediately")["route"] == "risky"
    assert _classify("Can you check shipment status?")["route"] == "tool"
    assert _classify("Please fix it")["route"] == "missing_info"
    assert _classify("The backend is unavailable and crashing")["route"] == "error"


def test_ui_loads_all_demo_scenarios():
    scenarios = load_demo_scenarios()

    assert len(scenarios) >= 15
    assert any(scenario.requires_approval for scenario in scenarios)
    assert "S04_risky" in {scenario.id for scenario in scenarios}


def test_ui_scenario_label_is_demo_friendly():
    scenario = Scenario(id="demo", query="Refund customer", expected_route=Route.RISKY)

    assert scenario_label(scenario) == "demo | risky | Refund customer"


def test_ui_can_reject_hitl_scenario_safely():
    scenario = Scenario(
        id="reject_demo",
        query="Refund this customer",
        expected_route=Route.RISKY,
        requires_approval=True,
    )

    result = run_scenario(scenario, approval_approved=False)
    summary = summarize_state_for_ui(result)

    assert summary["route"] == "risky"
    assert summary["approval_observed"] is True
    assert summary["approval_approved"] is False
    assert "provide the customer" in summary["final_answer"]
