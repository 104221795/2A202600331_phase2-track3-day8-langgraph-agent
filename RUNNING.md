# Running Guide

This guide uses Git Bash on Windows. In Git Bash, use forward slashes for
Windows paths:

```bash
/d/anaconda/python.exe
```

If your terminal already uses the correct Python environment, you can replace
`/d/anaconda/python.exe -m` with `python -m`.

For PowerShell, use `D:\anaconda\python.exe` instead.

## 1. Install Dependencies

Install the project with development tools:

```bash
/d/anaconda/python.exe -m pip install -e '.[dev]'
```

Install the optional Streamlit UI extra:

```bash
/d/anaconda/python.exe -m pip install -e '.[ui]'
```

The quotes around `'.[dev]'` and `'.[ui]'` matter in Git Bash because square
brackets can be interpreted as filename patterns.

## 2. Run Tests

```bash
/d/anaconda/python.exe -m pytest
```

Expected result:

```text
13 passed
```

## 3. Run Lint and Type Checks

```bash
/d/anaconda/python.exe -m ruff check src tests
/d/anaconda/python.exe -m mypy src
```

Expected result:

```text
All checks passed!
Success: no issues found in 11 source files
```

## 4. Generate Metrics and Report

Run all sample scenarios:

```bash
/d/anaconda/python.exe -m langgraph_agent_lab.cli run-scenarios --config configs/lab.yaml --output outputs/metrics.json
```

This generates:

- `outputs/metrics.json`
- `reports/lab_report.md`

Validate the metrics file:

```bash
/d/anaconda/python.exe -m langgraph_agent_lab.cli validate-metrics --metrics outputs/metrics.json
```

Expected result:

```text
Metrics valid. success_rate=100.00%
```

## 5. Run the Streamlit Bonus UI

Start the UI:

```bash
/d/anaconda/python.exe -m streamlit run src/langgraph_agent_lab/ui.py --server.port 8501
```

Open this URL in your browser:

```text
http://localhost:8501
```

The UI lets you enter a support ticket and inspect:

- route
- risk level
- retry count
- approval status
- final answer
- tool results
- audit events

## 6. Generate Bonus Evidence

Export the graph diagram:

```bash
/d/anaconda/python.exe -m langgraph_agent_lab.cli export-graph --output docs/graph.mmd
```

Export checkpoint history / time-travel evidence for a retry scenario:

```bash
/d/anaconda/python.exe -m langgraph_agent_lab.cli demo-history --config configs/lab.yaml --scenario-id S09_tool_retry_success --output outputs/state_history.json

/d/anaconda/python.exe -m langgraph_agent_lab.cli demo-history-all --config configs/lab.yaml --output outputs/state_history.json

```

Export checkpoint history / time-travel evidence for every scenario:

```bash
/d/anaconda/python.exe -m langgraph_agent_lab.cli demo-history-all --config configs/lab.yaml --output outputs/state_history.json
```

Install SQLite checkpoint support:

```bash
/d/anaconda/python.exe -m pip install -e '.[sqlite]'
```

Generate crash recovery evidence with SQLite:

```bash
/d/anaconda/python.exe -m langgraph_agent_lab.cli demo-crash-recovery --config configs/lab.yaml --scenario-id S09_tool_retry_success --database-url outputs/checkpoints.sqlite --output outputs/crash_recovery.json
```

Generated files:

- `docs/graph.mmd`
- `outputs/state_history.json`
- `outputs/crash_recovery.json`

## 7. Useful Demo Queries

Simple route:

```text
How do I reset my password?
```

Tool route:

```text
Please lookup order status for order 12345
```

Missing info route:

```text
Can you fix it?
```

Risky HITL route:

```text
Refund this customer and send confirmation email
```

Error and retry route:

```text
Timeout failure while processing request
```

Dead-letter route:

```text
System failure cannot recover after multiple attempts
```

## 8. Checkpoint

The completed checkpoint commit is:

```text
3fc546c Complete LangGraph lab implementation
```

To confirm your working tree is clean:

```bash
git status --short
```
