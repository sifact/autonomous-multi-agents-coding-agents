"""Command line: ``agent run | eval | safety | report``. Parsing, wiring and printing only."""
from __future__ import annotations

import time
from datetime import UTC, datetime
from enum import StrEnum
from importlib import metadata
from pathlib import Path
from typing import Annotated

import typer

from coding_agent.cli_support import deps
from coding_agent.cli_support.format import metrics_lines, money, record_line
from coding_agent.cli_support.printer import StepPrinter
from coding_agent.evaluation import aggregate, load_fast_subset, load_tasks, run_benchmark
from coding_agent.evaluation.runner import DEFAULT_OUT_DIR
from coding_agent.graph import build_graph, stream_task
from coding_agent.llm import MissingApiKeyError, UsageTracker
from coding_agent.sandbox import PathEscapeError, write_files

EXIT_OK, EXIT_FAILED, EXIT_BAD_INPUT, EXIT_SETUP = 0, 1, 2, 3
MAX_TASK_CHARS = 4000

app = typer.Typer(
    help="Multi-agent coding agent: plans, writes and runs code in a Docker sandbox, "
    "then repairs its own mistakes.",
    no_args_is_help=True, add_completion=False,
)


class SystemName(StrEnum):
    single_shot = "single_shot"
    single_agent = "single_agent"
    graph = "graph"


class Subset(StrEnum):
    fast = "fast"
    full = "full"


def _version(value: bool) -> None:
    if value:
        try:
            version = metadata.version("coding-agent")
        except metadata.PackageNotFoundError:
            version = "unknown"
        typer.echo(f"coding-agent {version}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[bool, typer.Option(
        "--version", callback=_version, is_eager=True, help="Show the version and exit."
    )] = False,
) -> None:
    """Multi-agent coding agent with a sandboxed Docker executor."""


def _fail(message: str, code: int) -> typer.Exit:
    typer.echo(message, err=True)
    return typer.Exit(code)


def _validated_task(task: str) -> str:
    task = task.strip()
    if not task:
        raise _fail("The task is empty. Describe what the program should do.", EXIT_BAD_INPUT)
    if len(task) > MAX_TASK_CHARS:
        raise _fail(
            f"The task is {len(task)} characters; the limit is {MAX_TASK_CHARS}.", EXIT_BAD_INPUT
        )
    return task


def _settings(max_rpm: int | None):
    settings = deps.load_settings()
    return settings.model_copy(update={"max_rpm": max_rpm}) if max_rpm else settings


@app.command()
def run(
    task: Annotated[str, typer.Argument(help="What the program should do, in plain English.")],
    out: Annotated[Path | None, typer.Option(
        help="Where to write the files (default ./agent_out/<UTC time>)."
    )] = None,
    all_strong: Annotated[bool, typer.Option(help="Use the strong model for every role.")] = False,
    max_rpm: Annotated[int | None, typer.Option(
        min=1, help="Cap on model requests per minute."
    )] = None,
    quiet: Annotated[bool, typer.Option(help="Print only the final summary.")] = False,
    verbose: Annotated[bool, typer.Option(help="Print full code of each version.")] = False,
) -> None:
    """Run the agent on TASK and write the resulting files."""
    task = _validated_task(task)
    settings = _settings(max_rpm)
    tracker = UsageTracker()
    try:
        router = deps.make_router(settings, tracker, all_strong)
        sandbox = deps.make_sandbox(settings)
    except deps.SetupError as exc:
        raise _fail(str(exc), EXIT_SETUP) from exc

    printer = StepPrinter(typer.echo, verbose=verbose, quiet=quiet)
    final = None
    start = time.monotonic()
    try:
        graph = build_graph(router, sandbox, settings)
        for node, update in stream_task(graph, task):
            if node == "finalize":
                final = update["final"]
            else:
                printer.handle(node, update)
    except MissingApiKeyError as exc:
        raise _fail(deps.MISSING_KEY_MESSAGE, EXIT_SETUP) from exc
    except Exception as exc:
        raise _fail(f"The run crashed: {type(exc).__name__}: {exc}", EXIT_FAILED) from exc
    wall = time.monotonic() - start
    if final is None:
        raise _fail("The run ended without a final report.", EXIT_FAILED)

    out_dir = out or Path("agent_out") / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    written = ""
    if final.files:
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            write_files(out_dir, final.files)
            written = f"Files written to: {out_dir}"
        except PathEscapeError as exc:
            written = f"Files NOT written: {exc}"
    typer.echo("")
    typer.echo("SUCCESS" if final.success else "FAILED")
    typer.echo(f"  repairs:  {final.repairs}")
    typer.echo(f"  tokens:   {final.usage.tokens_in} in / {final.usage.tokens_out} out")
    typer.echo(f"  cost:     {money(tracker.total_cost)}")
    typer.echo(f"  wall time: {wall:.1f}s")
    typer.echo(f"  {final.explanation}")
    if written:
        typer.echo(written)
    raise typer.Exit(EXIT_OK if final.success else EXIT_FAILED)


@app.command("eval")
def eval_(
    system: Annotated[SystemName, typer.Option(help="Which system to benchmark.")],
    subset: Annotated[Subset, typer.Option(
        help="fast (10 tasks) or full (all tasks)."
    )] = Subset.fast,
    repeats: Annotated[int, typer.Option(min=1, help="Runs per task.")] = 1,
    max_runs_per_min: Annotated[int | None, typer.Option(
        min=1, help="Pace run starts."
    )] = None,
    out_dir: Annotated[Path | None, typer.Option(help="Where to write the result JSON.")] = None,
    all_strong: Annotated[bool, typer.Option(help="Use the strong model for every role.")] = False,
    max_rpm: Annotated[int | None, typer.Option(
        min=1, help="Cap on model requests per minute."
    )] = None,
) -> None:
    """Run the benchmark for one system and print the headline metrics."""
    settings = _settings(max_rpm)
    try:
        deps.make_router(settings, UsageTracker(), all_strong)  # fail early on a missing key
        sandbox = deps.make_sandbox(settings)
        root = deps.tasks_dir()
        tasks = load_fast_subset(root) if subset is Subset.fast else load_tasks(root)
        eval_system = deps.build_system(system.value, settings, sandbox, all_strong)
    except deps.SetupError as exc:
        raise _fail(str(exc), EXIT_SETUP) from exc
    except (OSError, ValueError) as exc:
        raise _fail(f"Could not load the benchmark tasks: {exc}", EXIT_SETUP) from exc

    typer.echo(f"Running {system.value} on {len(tasks)} tasks ({subset.value}), x{repeats}")
    try:
        records = run_benchmark(
            tasks, eval_system, sandbox, repeats=repeats, max_runs_per_min=max_runs_per_min,
            out_dir=out_dir, on_record=lambda r: typer.echo(record_line(r)),
        )
    except Exception as exc:
        raise _fail(f"The benchmark stopped: {type(exc).__name__}: {exc}", EXIT_FAILED) from exc
    typer.echo("")
    typer.echo("\n".join(metrics_lines(aggregate(records))))
    saved = sorted((out_dir or DEFAULT_OUT_DIR).glob(f"{eval_system.name}-*.json"))
    if saved:
        typer.echo(f"Results written to: {saved[-1]}")


@app.command()
def safety() -> None:
    """Run the sandbox safety suite (attacks that must stay contained). No API key needed."""
    settings = deps.load_settings()
    try:
        sandbox = deps.make_sandbox(settings)
    except deps.SetupError as exc:
        raise _fail(str(exc), EXIT_SETUP) from exc
    report = deps.run_safety_suite(sandbox)
    for r in report.results:
        typer.echo(f"{r.name:<28} {'PASS' if r.passed else 'FAIL'}" + (
            f"  {r.detail}" if r.detail and not r.passed else ""))
    typer.echo(f"\n{report.passed}/{report.total} contained ({report.pass_rate:.0%})")
    raise typer.Exit(EXIT_OK if report.passed == report.total else EXIT_FAILED)


@app.command()
def report() -> None:
    """Build the results report (not implemented yet)."""
    typer.echo("Not implemented yet: see the README roadmap.")
