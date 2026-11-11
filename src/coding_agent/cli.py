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
from coding_agent.cli_support.errors import AUTH_MESSAGE, is_auth_error
from coding_agent.cli_support.format import metrics_lines, money, record_line, sanitize
from coding_agent.cli_support.printer import StepPrinter
from coding_agent.evaluation import aggregate, load_fast_subset, load_tasks, run_benchmark
from coding_agent.evaluation.readme_block import ReadmeMarkerError, write_readme_block
from coding_agent.evaluation.report import load_results, render_markdown
from coding_agent.graph import build_graph, stream_task
from coding_agent.llm import MissingApiKeyError, UsageTracker
from coding_agent.sandbox import PathEscapeError, write_files

EXIT_OK, EXIT_FAILED, EXIT_BAD_INPUT, EXIT_SETUP, EXIT_INTERRUPTED = 0, 1, 2, 3, 130
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
    typer.echo(sanitize(message), err=True)
    return typer.Exit(code)


def show(text: str) -> None:
    """Print text that may come from a model or a program, with terminal controls removed."""
    typer.echo(sanitize(text))


def _api_failure(exc: Exception) -> typer.Exit:
    """Clean message + exit code for an error raised mid-run (never echoes the key)."""
    if is_auth_error(exc) or isinstance(exc, MissingApiKeyError):
        message = AUTH_MESSAGE if is_auth_error(exc) else deps.MISSING_KEY_MESSAGE
        return _fail(message, EXIT_SETUP)
    return _fail(sanitize(f"The run failed: {type(exc).__name__}: {exc}"), EXIT_FAILED)


def _write_files(out_dir: Path, files: dict[str, str]) -> str | None:
    """Write through the safe writer; the error text on failure, else None."""
    if not files:
        return None
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        write_files(out_dir, files)
    except (OSError, PathEscapeError) as exc:
        return f"{type(exc).__name__}: {exc}"
    return None


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
    show(deps.tracing_status_line(settings))
    tracker = UsageTracker()
    try:
        router = deps.make_router(settings, tracker, all_strong)
        sandbox = deps.make_sandbox(settings)
    except deps.SetupError as exc:
        raise _fail(str(exc), EXIT_SETUP) from exc

    printer = StepPrinter(typer.echo, verbose=verbose, quiet=quiet)
    final = None
    attempts = 0  # code generations: first draft + every repair or replan rewrite
    start = time.monotonic()
    session = "run-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    try:
        graph = build_graph(router, sandbox, settings)
        with deps.trace_run(
            settings, session_id=session, system="graph", input_text=task
        ) as trace:
            for node, update in stream_task(graph, task, config=trace.config or None):
                if node == "finalize":
                    final = update["final"]
                    trace.set_report(final)
                else:
                    attempts += node == "coder"
                    printer.handle(node, update)
    except KeyboardInterrupt as exc:
        raise _fail("Interrupted.", EXIT_INTERRUPTED) from exc
    except Exception as exc:
        raise _api_failure(exc) from exc
    finally:
        deps.flush_traces()  # short-lived process: send queued traces before exiting
    wall = time.monotonic() - start
    if final is None:
        raise _fail("The run ended without a final report.", EXIT_FAILED)

    out_dir = out or Path("agent_out") / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    write_error = _write_files(out_dir, final.files)
    show("")
    show("SUCCESS" if final.success else "FAILED")
    show(f"  attempts: {attempts} (1 + {final.repairs} repair(s) in the last plan)")
    show(f"  tokens:   {final.usage.tokens_in} in / {final.usage.tokens_out} out")
    show(f"  cost:     {money(tracker.total_cost)}")
    show(f"  wall time: {wall:.1f}s")
    show(f"  {final.explanation}")
    if write_error:
        show(f"Files NOT written to {out_dir}: {write_error}")
        for path, content in sorted(final.files.items()):
            show(f"--- {path} ---\n{content}")
        raise typer.Exit(EXIT_SETUP)
    if final.files:
        show(f"Files written to: {out_dir}")
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
    all_strong: Annotated[bool, typer.Option(
        help="Graph only: strong model for every role (baselines already use the strong coder)."
    )] = False,
    max_rpm: Annotated[int | None, typer.Option(
        min=1, help="Cap on model requests per minute."
    )] = None,
) -> None:
    """Run the benchmark for one system and print the headline metrics."""
    settings = _settings(max_rpm)
    show(deps.tracing_status_line(settings))
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

    config = f"Running {system.value} on {len(tasks)} tasks ({subset.value}), x{repeats}"
    show(config)
    if all_strong and system is not SystemName.graph:
        show(f"note: --all-strong has no effect on {system.value} (it already uses the strong "
             "coder model)")
    saved: list[Path] = []
    try:
        records = run_benchmark(
            tasks, eval_system, sandbox, repeats=repeats, max_runs_per_min=max_runs_per_min,
            out_dir=out_dir, on_record=lambda r: show(record_line(r)), on_saved=saved.append,
            tracing=settings,
        )
    except KeyboardInterrupt as exc:
        _report_saved(saved, partial=True)
        raise _fail("Interrupted.", EXIT_INTERRUPTED) from exc
    except Exception as exc:
        _report_saved(saved, partial=True)
        raise _api_failure(exc) from exc
    finally:
        deps.flush_traces()
    show("")
    show("\n".join(metrics_lines(aggregate(records))))
    _report_saved(saved, partial=False)


def _report_saved(saved: list[Path], *, partial: bool) -> None:
    if saved:
        show(f"{'Partial results saved to' if partial else 'Results written to'}: {saved[-1]}")


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
def report(
    results_dir: Annotated[Path | None, typer.Option(
        help="Folder with the result JSON files (default benchmarks/results)."
    )] = None,
    all_runs: Annotated[bool, typer.Option(
        "--all", help="One row per result file instead of the latest per system."
    )] = False,
    by_category: Annotated[bool, typer.Option(
        help="Add final-pass tables by task category and difficulty."
    )] = False,
    write_readme: Annotated[bool, typer.Option(
        help="Replace the results block in the README with this report."
    )] = False,
    readme: Annotated[Path | None, typer.Option(
        help="README to update (default: the repo's)."
    )] = None,
) -> None:
    """Print the results table from saved benchmark runs. No API key needed."""
    folder = results_dir or deps.results_dir()
    results = load_results(
        folder, on_warning=lambda m: typer.echo(sanitize(f"warning: {m}"), err=True)
    ) if folder.is_dir() else []
    if not results:
        raise _fail(
            f"No result files found in {folder}. Run `agent eval --system ...` first.",
            EXIT_BAD_INPUT,
        )
    markdown = render_markdown(
        results, by_category=by_category, all_runs=all_runs, tasks_dir=deps.tasks_dir()
    )
    show(markdown)
    if write_readme:
        target = readme or deps.readme_path()
        try:
            write_readme_block(target, markdown)
        except (ReadmeMarkerError, OSError) as exc:
            raise _fail(f"README not updated: {exc}", EXIT_FAILED) from exc
        show(f"README results block updated: {target}")
