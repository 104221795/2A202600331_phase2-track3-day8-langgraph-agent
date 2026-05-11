"""State schema for the Day 08 LangGraph lab.

Students should extend the schema only when needed. Keep state lean and serializable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from operator import add
from typing import Annotated, Any, TypedDict

from pydantic import BaseModel, Field, field_validator


class Route(StrEnum):
    SIMPLE = "simple"
    TOOL = "tool"
    MISSING_INFO = "missing_info"
    RISKY = "risky"
    ERROR = "error"
    DEAD_LETTER = "dead_letter"
    DONE = "done"


class LabEvent(BaseModel):
    """Append-only audit event for grading and debugging."""

    node: str
    event_type: str
    message: str
    latency_ms: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovalDecision(BaseModel):
    approved: bool = False
    reviewer: str = "mock-reviewer"
    comment: str = ""


class AgentState(TypedDict, total=False):
    """LangGraph state.

    TODO(student): decide which fields should be append-only and which should be overwritten.
    The current annotations give a safe starting point for auditability.
    """

    thread_id: str
    scenario_id: str
    query: str
    normalized_query: str
    route: str
    risk_level: str
    classification_reason: str
    attempt: int
    max_attempts: int
    requires_approval: bool
    should_retry: bool
    final_answer: str | None
    pending_question: str | None
    proposed_action: str | None
    approval_decision: dict[str, Any] | None
    approval: dict[str, Any] | None
    evaluation_result: str | None
    messages: Annotated[list[str], add]
    tool_results: Annotated[list[str], add]
    errors: Annotated[list[str], add]
    events: Annotated[list[dict[str, Any]], add]


class Scenario(BaseModel):
    id: str
    query: str
    expected_route: Route
    requires_approval: bool = False
    should_retry: bool = False
    max_attempts: int = 3
    tags: list[str] = Field(default_factory=list)

    @field_validator("query")
    @classmethod
    def query_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query must not be empty")
        return value


def initial_state(scenario: Scenario) -> AgentState:
    """Create a serializable initial state for one scenario."""
    return {
        "thread_id": f"thread-{scenario.id}",
        "scenario_id": scenario.id,
        "query": scenario.query,
        "normalized_query": "",
        "route": "",
        "risk_level": "unknown",
        "classification_reason": "",
        "attempt": 0,
        "max_attempts": scenario.max_attempts,
        "requires_approval": scenario.requires_approval,
        "should_retry": scenario.should_retry,
        "final_answer": None,
        "pending_question": None,
        "proposed_action": None,
        "approval_decision": None,
        "approval": None,
        "evaluation_result": None,
        "messages": [],
        "tool_results": [],
        "errors": [],
        "events": [],
    }


def make_event(node: str, event_type: str, message: str, **metadata: Any) -> dict[str, Any]:
    """Create a normalized event payload."""
    payload = {"ts": datetime.now(UTC).isoformat(), **metadata}
    return LabEvent(
        node=node,
        event_type=event_type,
        message=message,
        metadata=payload,
    ).model_dump()
