# Autonomous Multi-Agent Coding Agent with a Sandbox

Give it a coding task in plain English. A team of agents plans it, designs the files, writes the code, **runs it inside a locked-down Docker sandbox**, reads the error, and fixes its own mistakes, up to three repair attempts, then stops and explains what went wrong.

Built with [LangGraph](https://langchain-ai.github.io/langgraph/) and Groq-hosted models. The point of the project is not only that it works, but that the claim "multiple agents help" is **measured**: a hidden-test benchmark compares the full agent graph against a single-shot LLM and a single looping agent.

> **Status: work in progress.** The sandbox, the agent graph, the evaluation harness and most of the benchmark are built and tested. The command-line tool, tracing, the web UI and the measured results are next. See [Status](#status) for exactly what exists today. No benchmark numbers are published yet, because they have not been run yet.

---

## How it works

```
 task (plain English)
        │
        ▼
   ┌─────────┐   ┌───────────┐   ┌────────┐   ┌──────────┐   ┌──────────┐
   │ Planner │──▶│ Architect │──▶│ Coder  │──▶│ Executor │──▶│ Reviewer │
   │ steps + │   │ files &   │   │ writes │   │ runs it  │   │ reads    │
   │ criteria│   │ structure │   │ code   │   │ in the   │   │ output & │
   └─────────┘   └───────────┘   └────────┘   │ sandbox  │   │ decides  │
        ▲                             ▲       └──────────┘   └────┬─────┘
        │ replan (max 2)              │ fix (max 3 repairs)       │
        └─────────────────────────────┴───────────────────────────┤
                                                       pass / stop│
                                                                  ▼
                                                      final report + files
```

- **Planner** breaks the task into steps and acceptance criteria.
- **Architect** chooses the files and structure.
- **Coder** writes the code with the strong model; repairs run under a separate `debugger` role that sees the reviewer's feedback and the error.
- **Executor** runs it in the sandbox. It never runs model-written code on your machine.
- **Reviewer** reads stdout, stderr and the traceback, then decides: **pass**, **fix** (back to the coder), **replan** (back to the planner) or **stop**.

The loop is a real graph with conditional edges, not a straight line. It always terminates: at most 3 repairs, at most 2 replans, and a global step budget of 40 node visits. When it gives up, the report says what failed and why.

## Safety: model-written code never runs on the host

Every execution happens in a short-lived Docker container with:

| Control | Setting |
|---|---|
| User | non-root |
| Network | off (`--network none`) |
| Capabilities | all dropped, `no-new-privileges` |
| Root filesystem | read-only; only the workspace is writable |
| CPU / memory / processes | 1 CPU, 512 MB, 64 PIDs (configurable) |
| Wall-clock time | 30 s, enforced from the host with a hard kill |
| Disk | capped; a host watcher kills the container if the workspace outgrows the limit |

There is also a static scan that flags risky patterns (shell calls, network use, destructive file operations, forking) before anything runs. It is advisory; the container is the real enforcement.

**The sandbox is tested by attacking it.** A safety suite runs seven hostile programs and checks that each one is contained: a fork bomb, an infinite loop, a huge memory allocation, deleting files outside the workspace, an outbound network call, filling the disk, and reading host paths. Each check was mutation-tested: with the matching protection removed, the matching test fails (the infinite-loop case can only hang, so a per-test timeout guards it).

Model output is also treated as untrusted when it flows back into prompts. Program output is tagged and neutralised, and a `pass` verdict is only accepted when the program actually exited cleanly.

## Evaluation: do multiple agents actually help?

The most important part of the project is the benchmark, not the demo.

**The benchmark** is 46 tasks with hidden tests, the agent never sees them. 36 are written and reviewed so far:

| Category | Written | Planned |
|---|---|---|
| Data scripts (CSV/JSON processing) | 10 | 10 |
| File processing (merge, dedupe, rename, split, parse config) | 8 | 8 |
| HTML parsing from **local fixtures** (no real websites) | 4 | 4 |
| Command-line apps (todo, key-value store, calculator, ...) | 8 | 8 |
| Charts (checked on the figure's actual content) | 6 | 6 |
| Bug-fix (a bug is injected, the agent must fix it) | 0 | 10 |

The written tasks are 14 easy, 15 medium and 7 hard.

**How the tasks are kept honest.** Every task has a prompt that pins the exact interface, a reference solution, and hidden tests. Each task was then reviewed by someone other than its author, who recomputed expected values by an independent method, wrote alternative correct solutions to make sure they pass, and wrote wrong-but-plausible solutions to make sure they fail. A validator checks that the reference passes and that empty or starter code fails. The grader refuses agent-written files that could tamper with the test run.

**Three systems are compared** on the same tasks:

1. **Single-shot**: one LLM call, no execution.
2. **Single agent with a loop**: generate, run, read the error, repair (up to 3 times).
3. **The full multi-agent graph.**

**Metrics:** pass@1, pass rate after repair, share of runtime errors fixed within 3 repairs, average attempts, tokens and cost per task, wall time, and safety-test pass rate. Two details keep the comparison fair:

- All systems share the same output format, fixtures, sandbox limits and repair budget.
- The graph can try more times overall than the loop (a replan resets its repair counter), so the results also report a **budget-matched pass rate** alongside the plain one, so a better score can't simply mean "more retries". Crashed runs count as failures and are excluded from cost averages instead of making a system look cheaper.

**Results: not published yet.** The runs need a Groq API key and have not been executed. When they are, the numbers, the ablation table and the honest conclusion (including if the extra agents only burn tokens) will go here, taken only from result files committed to this repo.

## Status

| Piece | State |
|---|---|
| Docker sandbox with limits | Done, tested |
| Safety suite (7 attacks) + static scan | Done, tested |
| LangGraph agents and routing (planner, architect, coder, executor, reviewer) | Done, tested with scripted models and the real sandbox |
| Baselines and benchmark runner | Done, tested |
| Benchmark tasks | 36 of 46 written |
| Command line (`agent run "..."`) | Next |
| Langfuse tracing | Planned |
| Measured results and ablation table | Planned (needs a Groq key) |
| CI with an evaluation badge | Planned |
| Web UI that streams the agent's steps | Planned |
| Architecture diagram and a demo GIF of a self-repair | Planned |

The test suite (365 tests) passes locally, including the tests that run against the real sandbox.

## Run it

Requirements: Python 3.12+, [uv](https://docs.astral.sh/uv/), and Docker (on a Mac, Colima or Docker Desktop).

```bash
git clone https://github.com/sifact/autonomous-multi-agents-coding-agents.git
cd autonomous-multi-agents-coding-agents
uv sync

# build the sandbox image used to run generated code
docker build -t coding-agent-sandbox:latest -f docker/sandbox.Dockerfile .

# run the test suite (includes the sandbox safety tests, so Docker must be running)
uv run pytest
```

To use real models, copy `.env.example` to `.env` and set `GROQ_API_KEY`. The key stays on your machine and is never committed. Model names for the cheap role (planner, architect, reviewer) and the strong role (coder, repairs) are configurable in `src/coding_agent/config.py`.

## Tech stack

Python · LangGraph · Groq (via `langchain-groq`) · Docker · pydantic · pytest · uv · ruff. Planned: Langfuse, FastAPI, GitHub Actions.

## Project layout

```
src/coding_agent/
  agents/       planner, architect, coder, executor, reviewer, prompts
  graph/        state, routing rules, graph builder, final report
  sandbox/      Docker sandbox, limits, workspace, static scan
  llm/          Groq client with rate-limit handling, role routing, cost tracking
  evaluation/   tasks, grader, metrics, baselines, runner, safety suite
benchmarks/tasks/   the benchmark: prompt, fixtures, hidden tests, reference per task
docker/             sandbox image definition
tests/              unit and end-to-end tests
docs/superpowers/   design document and implementation plan
```

Each core module has a short guide in a `guide/` folder next to it. The design and the build plan are in [`docs/superpowers/`](docs/superpowers/).
