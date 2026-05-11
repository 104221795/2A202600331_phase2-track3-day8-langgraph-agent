"""CLI for the lab."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer
import yaml

from .graph import build_graph
from .metrics import MetricsReport, metric_from_state, summarize_metrics, write_metrics
from .persistence import build_checkpointer
from .report import write_report
from .scenarios import load_scenarios
from .state import Scenario, initial_state

app = typer.Typer(no_args_is_help=True)


def _snapshot_to_record(index: int, snapshot: Any) -> dict[str, Any]:
    """Convert a LangGraph state snapshot into a stable JSON record."""
    values = getattr(snapshot, "values", {}) or {}
    metadata = getattr(snapshot, "metadata", {}) or {}
    next_nodes = list(getattr(snapshot, "next", ()) or ())
    events = values.get("events", []) or []
    return {
        "index": index,
        "scenario_id": values.get("scenario_id"),
        "route": values.get("route"),
        "attempt": values.get("attempt"),
        "max_attempts": values.get("max_attempts"),
        "evaluation_result": values.get("evaluation_result"),
        "final_answer_present": bool(values.get("final_answer")),
        "pending_question_present": bool(values.get("pending_question")),
        "events_count": len(events),
        "next": next_nodes,
        "metadata": metadata,
    }


def _find_scenario(scenarios: list[Scenario], scenario_id: str) -> Scenario:
    for scenario in scenarios:
        if scenario.id == scenario_id:
            return scenario
    known = ", ".join(scenario.id for scenario in scenarios)
    raise typer.BadParameter(f"Unknown scenario_id={scenario_id}. Known: {known}")


def _run_history_scenario(
    graph: Any,
    scenario: Scenario,
) -> dict[str, Any]:
    """Run one scenario and return checkpoint history evidence."""
    state = initial_state(scenario)
    run_config = {"configurable": {"thread_id": state["thread_id"]}}
    final_state = graph.invoke(state, config=run_config)
    history = [
        _snapshot_to_record(index, snapshot)
        for index, snapshot in enumerate(graph.get_state_history(run_config), start=1)
    ]
    return {
        "scenario_id": scenario.id,
        "thread_id": state["thread_id"],
        "expected_route": scenario.expected_route.value,
        "actual_route": final_state.get("route"),
        "final_answer_present": bool(final_state.get("final_answer")),
        "history_length": len(history),
        "history": history,
    }


@app.command("run-scenarios")
def run_scenarios(
    config: Annotated[Path, typer.Option("--config")],
    output: Annotated[Path, typer.Option("--output")],
) -> None:
    """Run all grading scenarios and write metrics JSON."""
    cfg = yaml.safe_load(config.read_text(encoding="utf-8"))
    scenarios = load_scenarios(cfg["scenarios_path"])
    checkpointer = build_checkpointer(cfg.get("checkpointer", "memory"), cfg.get("database_url"))
    graph = build_graph(checkpointer=checkpointer)
    metrics = []
    history_observed = False
    for scenario in scenarios:
        state = initial_state(scenario)
        run_config = {"configurable": {"thread_id": state["thread_id"]}}
        final_state = graph.invoke(state, config=run_config)
        if checkpointer is not None:
            try:
                history = list(graph.get_state_history(run_config))
                history_observed = history_observed or bool(history)
            except Exception:
                history_observed = history_observed or bool(final_state.get("events"))
        metrics.append(
            metric_from_state(
                final_state,
                scenario.expected_route.value,
                scenario.requires_approval,
            )
        )
    report = summarize_metrics(metrics, resume_success=history_observed)
    write_metrics(report, output)
    if cfg.get("report_path"):
        write_report(report, cfg["report_path"])
    typer.echo(f"Wrote metrics to {output}")


@app.command("validate-metrics")
def validate_metrics(metrics: Annotated[Path, typer.Option("--metrics")]) -> None:
    """Validate metrics JSON schema for grading."""
    payload = json.loads(metrics.read_text(encoding="utf-8"))
    report = MetricsReport.model_validate(payload)
    if report.total_scenarios < 6:
        raise typer.BadParameter("Expected at least 6 scenarios")
    typer.echo(f"Metrics valid. success_rate={report.success_rate:.2%}")


@app.command("export-graph")
def export_graph(output: Annotated[Path, typer.Option("--output")]) -> None:
    """Export the compiled graph as Mermaid markdown."""
    graph = build_graph()
    mermaid = graph.get_graph().draw_mermaid()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(f"```mermaid\n{mermaid}\n```\n", encoding="utf-8")
    typer.echo(f"Wrote graph diagram to {output}")


@app.command("demo-history")
def demo_history(
    config: Annotated[Path, typer.Option("--config")],
    scenario_id: Annotated[str, typer.Option("--scenario-id")],
    output: Annotated[Path, typer.Option("--output")],
) -> None:
    """Run one scenario and export checkpoint history for time-travel evidence."""
    cfg = yaml.safe_load(config.read_text(encoding="utf-8"))
    scenarios = load_scenarios(cfg["scenarios_path"])
    scenario = _find_scenario(scenarios, scenario_id)
    checkpointer = build_checkpointer(cfg.get("checkpointer", "memory"), cfg.get("database_url"))
    graph = build_graph(checkpointer=checkpointer)
    payload = _run_history_scenario(graph, scenario)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    typer.echo(f"Wrote checkpoint history to {output}")


@app.command("demo-history-all")
def demo_history_all(
    config: Annotated[Path, typer.Option("--config")],
    output: Annotated[Path, typer.Option("--output")],
) -> None:
    """Run every scenario and export checkpoint history evidence."""
    cfg = yaml.safe_load(config.read_text(encoding="utf-8"))
    scenarios = load_scenarios(cfg["scenarios_path"])
    checkpointer = build_checkpointer(cfg.get("checkpointer", "memory"), cfg.get("database_url"))
    graph = build_graph(checkpointer=checkpointer)
    histories = [_run_history_scenario(graph, scenario) for scenario in scenarios]
    payload = {
        "total_scenarios": len(histories),
        "scenario_ids": [item["scenario_id"] for item in histories],
        "histories": histories,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    typer.echo(f"Wrote all checkpoint histories to {output}")


if __name__ == "__main__":
    app()
