# Running Guide

This project was verified with the Anaconda Python interpreter on Windows:

```powershell
D:\anaconda\python.exe
```

If your terminal already uses the correct Python environment, you can replace
`D:\anaconda\python.exe -m` with `python -m`.

## 1. Install Dependencies

Install the project with development tools:

```powershell
D:\anaconda\python.exe -m pip install -e .[dev]
```

Install the optional Streamlit UI extra:

```powershell
D:\anaconda\python.exe -m pip install -e .[ui]
```

## 2. Run Tests

```powershell
D:\anaconda\python.exe -m pytest
```

Expected result:

```text
13 passed
```

## 3. Run Lint and Type Checks

```powershell
D:\anaconda\python.exe -m ruff check src tests
D:\anaconda\python.exe -m mypy src
```

Expected result:

```text
All checks passed!
Success: no issues found in 11 source files
```

## 4. Generate Metrics and Report

Run all sample scenarios:

```powershell
D:\anaconda\python.exe -m langgraph_agent_lab.cli run-scenarios --config configs/lab.yaml --output outputs/metrics.json
```

This generates:

- `outputs/metrics.json`
- `reports/lab_report.md`

Validate the metrics file:

```powershell
D:\anaconda\python.exe -m langgraph_agent_lab.cli validate-metrics --metrics outputs/metrics.json
```

Expected result:

```text
Metrics valid. success_rate=100.00%
```

## 5. Run the Streamlit Bonus UI

Start the UI:

```powershell
D:\anaconda\python.exe -m streamlit run src/langgraph_agent_lab/ui.py --server.port 8501
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

## 6. Useful Demo Queries

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

## 7. Checkpoint

The completed checkpoint commit is:

```text
3fc546c Complete LangGraph lab implementation
```

To confirm your working tree is clean:

```powershell
git status --short
```

