"""Node skeletons for the LangGraph workflow.

Each function should be small, testable, and return a partial state update. Avoid mutating the
input state in place.
"""

from __future__ import annotations

import re

from .state import AgentState, ApprovalDecision, Route, make_event

RISKY_KEYWORDS = {"refund", "delete", "send", "cancel", "remove", "revoke"}
TOOL_KEYWORDS = {"status", "order", "lookup", "check", "track", "find", "search"}
ERROR_KEYWORDS = {"timeout", "fail", "failure", "error", "crash", "unavailable", "cannot recover"}
VAGUE_PRONOUNS = {"it", "this", "that", "thing", "issue", "problem"}


def _normalize_query(query: str) -> str:
    return " ".join(query.strip().split())


def _tokens(query: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", query.lower())


def _contains_phrase(query: str, phrase: str) -> bool:
    if " " in phrase:
        return phrase in query.lower()
    return phrase in set(_tokens(query))


def intake_node(state: AgentState) -> dict:
    """Normalize raw query into state fields.

    The graph keeps the original query and a normalized copy so downstream
    routing remains deterministic while preserving the submitted ticket text.
    """
    query = _normalize_query(state.get("query", ""))
    return {
        "query": query,
        "normalized_query": query.lower(),
        "messages": [f"intake:{query[:40]}"],
        "events": [make_event("intake", "completed", "query normalized", query_length=len(query))],
    }


def classify_node(state: AgentState) -> dict:
    """Classify the query into a route.

    Keyword categories are intentionally broad and based on word/phrase matches,
    not scenario ids. Priority follows the lab rubric: risky > tool >
    missing_info > error > simple.
    """
    query = state.get("normalized_query") or state.get("query", "").lower()
    tokens = _tokens(query)
    token_set = set(tokens)
    route = Route.SIMPLE
    risk_level = "low"
    reason = "default safe response"

    risky_hits = sorted(keyword for keyword in RISKY_KEYWORDS if _contains_phrase(query, keyword))
    tool_hits = sorted(keyword for keyword in TOOL_KEYWORDS if _contains_phrase(query, keyword))
    error_hits = sorted(keyword for keyword in ERROR_KEYWORDS if _contains_phrase(query, keyword))
    is_vague = len(tokens) < 6 and bool(token_set & VAGUE_PRONOUNS)

    if risky_hits:
        route = Route.RISKY
        risk_level = "high"
        reason = f"risky keyword(s): {', '.join(risky_hits)}"
    elif tool_hits:
        route = Route.TOOL
        risk_level = "medium"
        reason = f"tool keyword(s): {', '.join(tool_hits)}"
    elif is_vague:
        route = Route.MISSING_INFO
        reason = "short vague request with unresolved pronoun"
    elif error_hits:
        route = Route.ERROR
        risk_level = "medium"
        reason = f"error keyword(s): {', '.join(error_hits)}"
    return {
        "route": route.value,
        "risk_level": risk_level,
        "classification_reason": reason,
        "events": [make_event("classify", "completed", f"route={route.value}", reason=reason)],
    }


def ask_clarification_node(state: AgentState) -> dict:
    """Ask for missing information instead of hallucinating.

    This path deliberately avoids inventing missing details.
    """
    question = (
        "Can you provide the customer, order, or account details needed "
        "to complete this request?"
    )
    return {
        "pending_question": question,
        "final_answer": question,
        "events": [make_event("clarify", "completed", "missing information requested")],
    }


def tool_node(state: AgentState) -> dict:
    """Call a mock tool.

    Simulates transient failures for retry scenarios and returns structured,
    serializable text suitable for metrics and reporting.
    """
    attempt = int(state.get("attempt", 0))
    should_fail = bool(state.get("should_retry")) or state.get("route") == Route.ERROR.value
    if should_fail and attempt < 2:
        result = (
            f"ERROR: transient failure attempt={attempt} "
            f"scenario={state.get('scenario_id', 'unknown')}"
        )
    else:
        result = (
            "OK: support lookup completed "
            f"scenario={state.get('scenario_id', 'unknown')} attempt={attempt}"
        )
    return {
        "tool_results": [result],
        "events": [
            make_event(
                "tool",
                "completed",
                f"tool executed attempt={attempt}",
                result=result,
            )
        ],
    }


def risky_action_node(state: AgentState) -> dict:
    """Prepare a risky action for approval.

    The action is intentionally staged before approval; no external side effect
    is represented as complete until the approval node succeeds.
    """
    query = state.get("query", "requested support action")
    return {
        "proposed_action": f"Stage high-risk support action for review: {query}",
        "events": [
            make_event(
                "risky_action",
                "pending_approval",
                "approval required",
                risk_level=state.get("risk_level"),
            )
        ],
    }


def approval_node(state: AgentState) -> dict:
    """Human approval step with optional LangGraph interrupt().

    Set LANGGRAPH_INTERRUPT=true to use real interrupt() for HITL demos.
    Default uses mock decision so tests and CI run offline.

    Reject/edit paths are represented by ``approved=False`` and route to the
    clarification node, making the graph safe by default.
    """
    import os

    if os.getenv("LANGGRAPH_INTERRUPT", "").lower() == "true":
        from langgraph.types import interrupt

        value = interrupt({
            "proposed_action": state.get("proposed_action"),
            "risk_level": state.get("risk_level"),
        })
        if isinstance(value, dict):
            decision = ApprovalDecision(**value)
        else:
            decision = ApprovalDecision(approved=bool(value))
    else:
        decision = ApprovalDecision(approved=True, comment="mock approval for lab")
    return {
        "approval": decision.model_dump(),
        "events": [make_event("approval", "completed", f"approved={decision.approved}")],
    }


def retry_or_fallback_node(state: AgentState) -> dict:
    """Record a retry attempt or fallback decision.

    The router bounds the loop; this node records the next attempt and a
    deterministic backoff hint for auditability.
    """
    attempt = int(state.get("attempt", 0)) + 1
    max_attempts = int(state.get("max_attempts", 3))
    backoff_ms = min(250 * (2 ** max(attempt - 1, 0)), 2_000)
    errors = [f"transient failure attempt={attempt}/{max_attempts}"]
    return {
        "attempt": attempt,
        "errors": errors,
        "events": [
            make_event(
                "retry",
                "completed",
                "retry attempt recorded",
                attempt=attempt,
                max_attempts=max_attempts,
                backoff_ms=backoff_ms,
            )
        ],
    }


def answer_node(state: AgentState) -> dict:
    """Produce a final response.

    Answers are grounded in the latest tool result when one exists and include
    approval context for risky actions.
    """
    if state.get("tool_results"):
        answer = f"I found: {state['tool_results'][-1]}"
        if state.get("approval"):
            answer = f"Approved action completed. {answer}"
    else:
        answer = "Here is the safe support guidance for your request."
    return {
        "final_answer": answer,
        "events": [make_event("answer", "completed", "answer generated")],
    }


def evaluate_node(state: AgentState) -> dict:
    """Evaluate tool results — the 'done?' check that enables retry loops.

    Structured validation would be a natural production upgrade; this lab uses
    deterministic tool prefixes so tests and demos are stable.
    """
    tool_results = state.get("tool_results", [])
    latest = tool_results[-1] if tool_results else ""
    if "ERROR" in latest:
        return {
            "evaluation_result": "needs_retry",
            "events": [
                make_event(
                    "evaluate",
                    "completed",
                    "tool result indicates failure, retry needed",
                )
            ],
        }
    return {
        "evaluation_result": "success",
        "events": [make_event("evaluate", "completed", "tool result satisfactory")],
    }


def dead_letter_node(state: AgentState) -> dict:
    """Log unresolvable failures for manual review.

    Third layer of error strategy: retry -> dead letter for manual review.
    """
    return {
        "final_answer": (
            "Request could not be completed after maximum retry attempts. "
            "Logged for manual review."
        ),
        "errors": ["dead_letter: max retries exceeded"],
        "events": [
            make_event(
                "dead_letter",
                "completed",
                f"max retries exceeded, attempt={state.get('attempt', 0)}",
            )
        ],
    }


def finalize_node(state: AgentState) -> dict:
    """Finalize the run and emit a final audit event."""
    return {"events": [make_event("finalize", "completed", "workflow finished")]}
