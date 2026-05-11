# Lab Guide

## Step 1 - Understand the implemented graph

Implemented flow:

```text
START -> intake -> classify -> route
route simple       -> answer -> finalize -> END
route tool         -> tool -> evaluate -> answer -> finalize -> END
route tool (retry) -> tool -> evaluate -> retry -> tool -> evaluate -> ... (loop)
route missing_info -> clarify -> finalize -> END
route risky        -> risky_action -> approval -> tool -> evaluate -> answer -> finalize -> END
route error        -> retry -> tool -> evaluate -> retry -> ... (loop until success or max)
route (max retry)  -> retry -> dead_letter -> finalize -> END
```

The classifier uses keyword and state heuristics, not exact scenario ids. Priority
matters and is intentionally tested by the expanded mock data:

```text
risky -> tool -> missing_info -> error -> simple
```

This means a query such as "Cancel order 98765 after checking delivery status"
must route to `risky`, not `tool`, because cancellation requires approval.

## Step 2 - What is already implemented

1. `state.py`: typed state, append-only reducers, retry gates, approval fields,
   and scenario controls.
2. `nodes.py`: intake, classification, clarification, mock tool, evaluation,
   retry, risky action staging, approval, dead letter, and finalize nodes.
3. `routing.py`: explicit conditional routing after classify, evaluate, retry,
   and approval.
4. `graph.py`: all paths terminate through `finalize -> END`.
5. `persistence.py`: memory checkpointer plus SQLite support using an explicit
   connection and WAL mode.
6. `metrics.py`: scenario-level and aggregate metrics.
7. `report.py`: generated lab report based on actual metrics.
8. `ui.py`: optional Streamlit bonus UI for manual ticket demos.

## Step 3 - Run scenarios

```bash
/d/anaconda/python.exe -m langgraph_agent_lab.cli run-scenarios --config configs/lab.yaml --output outputs/metrics.json
/d/anaconda/python.exe -m langgraph_agent_lab.cli validate-metrics --metrics outputs/metrics.json
```

## Step 4 - Run quality checks

```bash
/d/anaconda/python.exe -m pytest
/d/anaconda/python.exe -m ruff check src tests
/d/anaconda/python.exe -m mypy src
```

## Step 5 - Expanded mock benchmark data

`data/sample/scenarios.jsonl` includes the original seven scenarios plus harder
mock scenarios for tutor-style benchmark preparation:

- risky/tool priority conflicts
- risky/error priority conflicts
- vague clarification requests
- tool lookup cases beyond order status
- retry-to-success cases
- retry-to-dead-letter cases
- safe default/simple route cases

These scenarios are intentionally phrased differently from the README examples
so the graph proves it is using route logic rather than memorized scenario ids.

## Step 6 - Extension tasks

Completed:

- Streamlit UI for ticket demos.
- Checkpoint history evidence in generated metrics.
- SQLite checkpointer support.

Possible next extensions:

- Switch to SQLite persistence (`checkpointer: sqlite` in `lab.yaml`) and verify state survives restart.
- Demonstrate crash-resume with the same `thread_id`.
- Add time-travel replay from a previous checkpoint using `get_state_history()`.
- Enable real HITL with `LANGGRAPH_INTERRUPT=true` and build a Streamlit approval UI.
- Add parallel fan-out for two mock tools and merge evidence.
- Export a graph diagram and include it in the report.

## Submission checklist

- [ ] `pytest` passes.
- [ ] `ruff check src tests` passes.
- [ ] `mypy src` passes.
- [ ] `run-scenarios` writes `outputs/metrics.json`.
- [ ] `validate-metrics` validates metrics.
- [ ] `reports/lab_report.md` is completed and matches latest metrics.
- [ ] You can explain one route and one failure mode in demo.
