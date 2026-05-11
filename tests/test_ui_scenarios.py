from langgraph_agent_lab.nodes import classify_node, intake_node
from langgraph_agent_lab.state import Route, Scenario
from langgraph_agent_lab.ui import (
    history_items_from_payload,
    load_demo_scenarios,
    load_json_artifact,
    load_text_artifact,
    resolve_hitl_button_decision,
    run_scenario,
    scenario_label,
    summarize_history_artifact,
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


def test_ui_hitl_buttons_map_to_explicit_decisions():
    assert resolve_hitl_button_decision(approve_clicked=True, reject_clicked=False) is True
    assert resolve_hitl_button_decision(approve_clicked=False, reject_clicked=True) is False
    assert resolve_hitl_button_decision(approve_clicked=False, reject_clicked=False) is None


def test_ui_artifact_loaders(tmp_path):
    text_path = tmp_path / "graph.mmd"
    json_path = tmp_path / "history.json"
    text_path.write_text("graph TD;", encoding="utf-8")
    json_path.write_text('{"history": []}', encoding="utf-8")

    assert load_text_artifact(text_path) == "graph TD;"
    assert load_json_artifact(json_path) == {"history": []}
    assert load_text_artifact(tmp_path / "missing.txt") == ""
    assert load_json_artifact(tmp_path / "missing.json") == {}


def test_ui_history_summary_counts_retry_evidence():
    summary = summarize_history_artifact(
        {
            "scenario_id": "S09",
            "thread_id": "thread-S09",
            "expected_route": "tool",
            "actual_route": "tool",
            "final_answer_present": True,
            "history": [
                {"evaluation_result": "needs_retry", "next": ["retry"]},
                {"evaluation_result": "success", "next": []},
            ],
        }
    )

    assert summary["scenario_id"] == "S09"
    assert summary["history_length"] == 2
    assert summary["retry_evidence_count"] == 1


def test_ui_history_payload_supports_single_and_all_formats():
    single = {"scenario_id": "S1", "history": []}
    all_payload = {"histories": [{"scenario_id": "S1"}, {"scenario_id": "S2"}]}

    assert history_items_from_payload(single) == [single]
    assert [item["scenario_id"] for item in history_items_from_payload(all_payload)] == ["S1", "S2"]
    assert history_items_from_payload({}) == []
