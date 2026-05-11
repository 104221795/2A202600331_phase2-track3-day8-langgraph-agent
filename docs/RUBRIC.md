# Grading Rubric

| Category | Points | Evidence |
|---|---:|---|
| Architecture and state schema | 20 | Typed state, reducers for append-only fields, lean serializable state, clear node boundaries |
| Graph behavior | 25 | Correct routes for six scenarios, bounded retry, HITL approval path, all routes terminate |
| Persistence and recovery | 15 | Checkpointer used, thread id per run, state history or crash-resume evidence |
| Metrics and tests | 20 | `metrics.json` valid, scenario coverage, tests pass, meaningful error counts |
| Report and demo | 15 | Architecture explanation, metrics table, failure analysis, improvement plan |
| Production hygiene | 5 | README, config, environment handling, lint/type discipline |

## Suggested grade bands

- 90-100: production-quality structure, metrics, report, and at least one extension.
- 75-89: core graph works, metrics valid, report explains trade-offs.
- 60-74: graph mostly works but persistence/report or error handling is incomplete.
- <60: does not run, hard-codes scenarios, or lacks metrics/report.

## Current implementation evidence

This repository is implemented for the 90-100 target band:

- Typed state is defined in `state.py` with append-only reducers for `messages`,
  `tool_results`, `errors`, and `events`.
- Routing is keyword and state based, not scenario-id based.
- Route priority is deterministic: risky, tool, missing information, error, then
  simple.
- Retry loops are bounded by `max_attempts` and terminate at `dead_letter` when
  exhausted.
- Risky actions pass through `risky_action -> approval` before tool execution.
- `MemorySaver` checkpointing is enabled by default, and SQLite checkpoint support
  is implemented for the extension path.
- The CLI records checkpoint history evidence in `resume_success`.
- `reports/lab_report.md` is generated from live metrics.
- Bonus extension is implemented with an optional Streamlit UI in
  `src/langgraph_agent_lab/ui.py`.
- Bonus graph diagram evidence can be generated with `export-graph`.
- Bonus time-travel evidence can be generated with `demo-history`.

## Benchmark-readiness checklist

Use this list before a tutor or hidden benchmark run:

- [ ] `pytest` passes.
- [ ] `ruff check src tests` passes.
- [ ] `mypy src` passes.
- [ ] `run-scenarios` regenerates `outputs/metrics.json`.
- [ ] `validate-metrics` reports `success_rate=100.00%`.
- [ ] `reports/lab_report.md` reflects the latest scenario count.
- [ ] `docs/graph.mmd` exists after running `export-graph`.
- [ ] `outputs/state_history.json` exists after running `demo-history`.
- [ ] Expanded mock scenarios in `data/sample/scenarios.jsonl` pass without any
  scenario-id-specific code.
