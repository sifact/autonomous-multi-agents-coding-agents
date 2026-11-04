# Autonomous Multi-Agent Coding Agent with Sandbox: Design

Status: draft, written without the Q&A round (the user chose "just start"). Every choice marked **[my call]** is a default the user has not confirmed.

## Intent
A portfolio project that can be defended in interviews. It takes a plain-English coding task, then plans, writes, runs and repairs the code on its own, inside a locked-down sandbox. The README must show measured numbers, not a tutorial clone. The central question it answers with data is: **does a multi-agent graph beat a single-shot LLM or a single looping agent, or does it only burn tokens?**

## Goals
1. LangGraph graph with Planner → Architect → Coder → Executor → Reviewer/Debugger. The Reviewer routes conditionally: pass → END, fix → Coder, replan → Planner, give up → END with an explanation.
2. Self-repair: at most 3 repair attempts per step, then stop and say what failed and why.
3. Real sandbox. Model-generated code never touches `exec`/`eval` or the host.
4. Benchmark of 30-50 tasks with hidden tests, plus three systems compared: single-shot, single-agent loop, full graph. Ablation table in the README.
5. CLI (`agent run "..."`), then a small web UI that streams steps live.
6. Langfuse tracing: plan, code versions, errors, fixes, final result per run.
7. CI runs a fast eval subset on every push, with a badge.

## Non-goals and anti-goals
- Not a general IDE agent; tasks are small Python programs.
- No scraping of real sites; web-style tasks use local HTML fixtures.
- Anti-goal: numbers that cannot be reproduced from the repo. Every README figure comes from a committed eval run.
- Anti-goal: a sandbox that is only claimed safe. Each limit has a test that proves it triggers.

## Decisions **[my call]**
| Topic | Choice | Why |
|---|---|---|
| Models | **Groq only** (the user's only access, decided by the user). Small fast model for planner/architect/reviewer, larger model for coder/debugger, per role in config. Defaults `llama-3.1-8b-instant` / `llama-3.3-70b-versatile` are unverified and get checked on first real run. | Cheap routing is a result worth measuring; a config switch allows an all-strong ablation. Free-tier rate limits mean 429 backoff and throttled eval runs. |
| Sandbox | Docker (via Colima on this Mac), one short-lived container per execution | Free, local, works in CI. E2B stays possible behind the same `Sandbox` interface. |
| Tracing | Langfuse | Open source, self-hostable, free cloud tier, has an official skill. |
| Orchestration | LangGraph (Python 3.13, uv) | Required by the brief. |
| Eval trigger | CI runs a fast subset against the real API with a spend cap; the full benchmark is run locally and its results file is committed. | Keeps CI cost bounded. |

## Architecture
```
src/coding_agent/
  config.py  cli.py                 # cross-cutting
  agents/        planner, architect, coder, executor, reviewer nodes + prompts
  graph/         state schema, routing functions, graph builder
  sandbox/       Sandbox interface, DockerSandbox, limits, policy checks
  llm/           model factory, per-role routing, token/$ accounting
  evaluation/    task loader, runner, hidden-test grader, metrics, baselines, report
  tracing/       Langfuse setup
  serving/       FastAPI + SSE event stream, static web UI
tests/  benchmarks/tasks/<id>/{prompt.md, fixtures/, hidden_tests/}
```

### Graph
- State: task, plan + acceptance criteria, file layout, code versions, last execution result, attempt counters per step, total token/cost.
- Reviewer outputs one of `pass | fix | replan | stop`. Routing is a plain function over that verdict plus counters, so it is unit-testable without any LLM.
- Replans are capped (2) so the graph always terminates. A global step budget is a second backstop.

### Sandbox
- Container flags: non-root user, `--network none`, `--memory`, `--cpus`, `--pids-limit`, read-only root filesystem, tmpfs for `/tmp`, workspace as the only bind mount, `--cap-drop ALL`, `no-new-privileges`, wall-clock timeout enforced by the host with a kill.
- Disk limit via size-capped workspace tmpfs/volume.
- Network allow-list is off by default; the interface supports opting in per task but no benchmark task uses it.
- Static policy scan flags dangerous patterns (`os.system`, `subprocess` of shells, `rm -rf /`, socket use) before execution. Flags are logged and shown to the Reviewer; the container remains the real enforcement.
- Safety test suite, each a task that must be stopped: fork bomb, infinite loop, huge allocation, delete outside workspace, outbound network call, disk fill, read of host paths. Safety-test pass rate is a reported metric.

## Evaluation
- 30-50 tasks in categories: data scripts, file processing, CLI apps, charts, injected-bug fixes. Optional HumanEval+/MBPP+ subset for comparability.
- Hidden tests run in the sandbox after the agent finishes; the agent never sees them.
- Systems: (A) single-shot, (B) single agent with repair loop, (C) full graph; ablations on model routing and on dropping Planner/Architect.
- Metrics: pass@1 (first execution), final pass rate after repair, % runtime errors fixed within 3 attempts, mean attempts, tokens and $ per task, wall time, safety pass rate. Report variance across seeds/repeats where budget allows.
- Honest reporting: if the graph does not beat the single agent, the README says so.

## Interfaces
- CLI: `agent run "task"`, `agent eval --system {single_shot,single_agent,graph} --subset fast|full`, `agent safety`.
- Web UI: task box, live step stream (plan, code diffs, stdout/stderr, verdicts), run summary with cost. Public demo notes data is synthetic. API key server-side only, rate and input-size limits. No Docker for deployment (per global rules); deployment target decided at that stage, since the sandbox needs a Docker host and so does constrain the choice. E2B is the likely fallback for a hosted demo.

## Deliverables
README with the architecture diagram (Excalidraw, `docs/`), ablation table, safety results, a GIF of fail → read error → fix → pass, CI badge. A project-scope `coding-agent-eval` skill is created only if the installed vendor skills prove insufficient for the harness work.

## Environment findings (2026-11-05)
- Docker CLI present; daemon was down. Colima started (2 CPU, 4 GB, 20 GB disk) and works.
- `GROQ_API_KEY` is **not set**. Unit tests use a fake LLM; real runs, baselines and CI need the key in `.env` (gitignored).
- Installed at project scope: `langgraph-fundamentals` (langchain-ai/langchain-skills), `langfuse` (langfuse/skills). Both read first; no scripts, last updated Oct/Nov 2026.

## Left to the builder
Prompt wording, exact task list, resource limit numbers (start: 512 MB, 1 CPU, 30 s, 64 PIDs), report format.
