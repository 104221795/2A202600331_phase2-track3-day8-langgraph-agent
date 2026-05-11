from types import SimpleNamespace

import pytest

from langgraph_agent_lab.cli import _find_scenario, _snapshot_to_record
from langgraph_agent_lab.state import Route, Scenario


def test_snapshot_to_record_is_stable_json_shape():
    snapshot = SimpleNamespace(
        values={
            "scenario_id": "S",
            "route": "error",
            "attempt": 1,
            "max_attempts": 3,
            "evaluation_result": "needs_retry",
            "final_answer": None,
            "pending_question": None,
            "events": [{"node": "retry"}],
        },
        metadata={"source": "loop"},
        next=("tool",),
    )

    record = _snapshot_to_record(1, snapshot)

    assert record["index"] == 1
    assert record["scenario_id"] == "S"
    assert record["events_count"] == 1
    assert record["next"] == ["tool"]


def test_find_scenario_returns_match():
    scenario = Scenario(id="S", query="hello", expected_route=Route.SIMPLE)

    assert _find_scenario([scenario], "S") is scenario


def test_find_scenario_rejects_unknown_id():
    scenario = Scenario(id="S", query="hello", expected_route=Route.SIMPLE)

    with pytest.raises(Exception, match="Unknown scenario_id=missing"):
        _find_scenario([scenario], "missing")
