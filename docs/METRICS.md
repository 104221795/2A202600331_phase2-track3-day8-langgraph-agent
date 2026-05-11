# Metrics Specification

`outputs/metrics.json` must validate against `MetricsReport` in `src/langgraph_agent_lab/metrics.py`.

The current implementation generates this file with:

```bash
/d/anaconda/python.exe -m langgraph_agent_lab.cli run-scenarios --config configs/lab.yaml --output outputs/metrics.json
```

Validate it with:

```bash
/d/anaconda/python.exe -m langgraph_agent_lab.cli validate-metrics --metrics outputs/metrics.json
```

Required fields:

- `total_scenarios`: number of scenarios executed. Minimum 6.
- `success_rate`: fraction of scenarios that meet expected route and output requirements.
- `avg_nodes_visited`: average number of audit events/nodes visited per scenario.
- `total_retries`: count of retry node visits across scenarios.
- `total_interrupts`: count of approval/HITL events across scenarios.
- `resume_success`: true if you demonstrate crash-resume or state-history replay.
- `scenario_metrics`: one object per scenario.

Current expected local result after running the expanded mock benchmark data:

- success rate: `100.00%`
- state-history evidence: `resume_success=true`
- risky/HITL scenarios observe approval events
- retry scenarios include retry counts and error records
- dead-letter scenarios include a final manual-review answer

Each scenario metric should include:

- `scenario_id`
- `success`
- `expected_route`
- `actual_route`
- `nodes_visited`
- `retry_count`
- `interrupt_count`
- `approval_required`
- `approval_observed`
- `latency_ms`
- `errors`

## How success is computed

A scenario is successful when:

1. `actual_route` equals `expected_route`.
2. The graph produces either `final_answer` or `pending_question`.
3. If `approval_required=true`, an approval decision is observed.

This keeps the benchmark focused on behavior rather than exact answer strings.

## Useful interpretation notes

- `nodes_visited` is derived from append-only audit events.
- `retry_count` counts visits to the `retry` node.
- `interrupt_count` counts approval/HITL events. In mock mode this is still counted
  as approval coverage, even without a live LangGraph interrupt.
- `resume_success=true` means checkpoint state history was observed through
  `get_state_history()` during scenario execution.
- `errors` is append-only and intentionally includes transient retry failures and
  dead-letter escalation records.

## Grading notes

Metrics are not just numbers. Your report must explain why the numbers look the way they do.
