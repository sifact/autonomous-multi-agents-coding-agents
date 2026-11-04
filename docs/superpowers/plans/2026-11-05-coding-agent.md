# Autonomous Multi-Agent Coding Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a LangGraph multi-agent coding agent that plans, writes, runs (in a Docker sandbox) and repairs code, plus a benchmark that measures whether the multi-agent graph beats simpler baselines.

**Architecture:** Sandbox and eval harness first (TDD), then LLM layer, graph, baselines, tracing, CLI, CI, web UI. The graph's routing is pure functions over a typed state, so it is tested without an LLM. All agents take an injected `ChatModel` and `Sandbox`, so tests use fakes.

**Tech Stack:** Python 3.13, uv, LangGraph, langchain-groq, pydantic v2, pytest, ruff, Docker (Colima locally), Langfuse, FastAPI + SSE.

**Spec:** `docs/superpowers/specs/2026-11-05-coding-agent-design.md`

## Global Constraints
- Package `src/coding_agent/` with sub-packages `agents/ graph/ sandbox/ llm/ evaluation/ tracing/ serving/`; only `cli.py`, `config.py` at top level. Each sub-package exports its public API from `__init__.py`; callers import from the package.
- Every core ML module (evaluation, llm, agents, sandbox) gets `guide/<module>.md`: H1 = file name, one-line summary, exactly 5 bullets. No `.md` next to code.
- Model-generated code never runs via `exec`/`eval`/host subprocess; only through `Sandbox`.
- Container: non-root, `--network none`, `--cap-drop ALL`, `no-new-privileges`, read-only root fs, defaults 512 MB, 1 CPU, 30 s, 64 PIDs, 64 MB disk.
- Max 3 repair attempts per step; max 2 replans; global step budget 40 node visits.
- LLM provider is **Groq only** (user has no other access). Roles: planner/architect/reviewer → `model_cheap` (default `llama-3.1-8b-instant`); coder/debugger → `model_strong` (default `llama-3.3-70b-versatile`); both configurable in `Settings`. These IDs are unverified defaults: Task 13 confirms them against Groq's `/openai/v1/models` and swaps in a stronger coder model if one is available.
- Seeds and model names recorded in every eval result file. README numbers only from committed `benchmarks/results/*.json`.
- No scraping of real sites; HTML tasks use local fixtures.
- Ignore patterns root-anchored (`/data/`, `/.env`). Never add Claude/AI mentions to commits or PRs. Do not use Docker for deploying the web app (the sandbox image is the one exception).
- `GROQ_API_KEY` is currently unset: tasks 1-12 need no key; tasks 13 and 15 do. Groq's free tier has tight per-minute/per-day limits, so the LLM layer retries 429s with backoff and the runner can throttle (`--max-rpm`).

## Review Focus
1. Code that prints 10 MB of output: executor truncates stdout/stderr to 20 KB before it reaches the LLM and the UI.
2. Model returns malformed/no JSON verdict: reviewer retries once, then treats it as `stop` with an explanation, never crashes.
3. Generated code writes files outside the planned layout or with `../` paths: workspace writer rejects path escape.
4. Task prompt that is empty or huge: CLI/API reject empty, and inputs over 4,000 chars.
5. Container left running after timeout/Ctrl-C: no orphan containers (checked by test).

---

### Task 1: Scaffold, config, sandbox image
**Files:** Create `pyproject.toml` (entry point `agent = coding_agent.cli:app`, pytest marker `docker`), `.gitignore`, `.env.example`, `src/coding_agent/{__init__,config}.py`, `docker/sandbox.Dockerfile` (python:3.13-slim, user uid 1000, pytest/pandas/matplotlib preinstalled, no pip network needed at run time), `tests/test_config.py`, `README.md` stub.
**Interfaces:** Produces `Settings` (pydantic-settings; fields `groq_api_key: str|None`, `model_cheap`, `model_strong`, `sandbox_image="coding-agent-sandbox:latest"`, `limits: Limits` defaults above, `max_repairs=3`, `max_replans=2`, `step_budget=40`) and `get_settings() -> Settings`.
- [ ] Test `test_defaults_match_spec` asserts the values above; `test_env_override` sets `MODEL_STRONG=x` and reads it.
- [ ] Run `uv run pytest tests/test_config.py` → FAIL; implement; → PASS.
- [ ] `docker build -t coding-agent-sandbox:latest -f docker/sandbox.Dockerfile .` succeeds.
- [ ] Commit `chore: scaffold project`.

### Task 2: Sandbox interface and DockerSandbox
**Files:** Create `sandbox/{limits,base,docker_sandbox,workspace,__init__}.py`, `tests/sandbox/test_docker_sandbox.py` (marker `docker`), `tests/sandbox/test_workspace.py`.
**Interfaces:** Produces `Limits(memory_mb, cpus, timeout_s, pids, disk_mb, network: bool)` (frozen dataclass); `ExecResult(exit_code:int, stdout:str, stderr:str, timed_out:bool, oom_killed:bool, duration_s:float)`; `Sandbox` Protocol with `run(self, workspace: Path, command: list[str], limits: Limits | None = None) -> ExecResult`; `DockerSandbox(image: str)`; `write_files(workspace: Path, files: dict[str,str]) -> None` (raises `PathEscapeError` on absolute or `..` paths); `truncate(text:str, max_chars:int=20_000) -> str`.
- [ ] Tests: `test_hello_world`, `test_nonzero_exit_captured_with_traceback`, `test_runs_as_non_root` (`id -u` != 0), `test_timeout_kills_container_and_leaves_no_orphan` (`docker ps -q` empty after), `test_files_written_in_workspace_visible_to_host`, `test_write_files_rejects_escape` (`../x`, `/etc/x`), `test_truncate_marks_cut`.
- [ ] Implement via the `docker` CLI with `subprocess` (host side only). Use a unique `--name`, `docker kill` on timeout. Disk cap: try size-capped tmpfs workspace, fallback to bind mount + `--ulimit fsize` + post-run size check; pick whichever makes the Task 3 disk-fill test pass.
- [ ] Run `uv run pytest tests/sandbox -v` → PASS. Commit `feat(sandbox): docker sandbox with limits`.

### Task 3: Sandbox safety suite and policy scan
**Files:** Create `sandbox/policy.py`, `evaluation/safety.py`, `tests/sandbox/test_safety.py` (marker `docker`), `tests/sandbox/test_policy.py`.
**Interfaces:** Produces `scan(code:str) -> list[PolicyFlag]` (`PolicyFlag(rule:str, line:int)`; rules: `shell_exec`, `network`, `destructive_fs`, `fork`); `SAFETY_CASES: list[SafetyCase]` (`name, code, expect: Callable[[ExecResult], bool]`); `run_safety_suite(sandbox: Sandbox) -> SafetyReport` (`passed:int, total:int, results:list[...]`, `pass_rate` property).
- [ ] One test per case, each asserting containment: `fork_bomb` (returns within timeout, host unaffected, no orphans), `infinite_loop` (`timed_out`), `memory_hog` (`oom_killed` or non-zero), `delete_outside_workspace` (a sentinel file in the image's `/usr` is still present, and a host canary file is untouched), `network_call` (connect fails), `disk_fill` (stopped, host disk delta under 200 MB), `read_host_path` (`/Users` absent).
- [ ] Policy tests: `scan("os.system('ls')")` flags `shell_exec` at line 1; benign code returns `[]`.
- [ ] Implement; run `uv run pytest tests/sandbox -v` → PASS. Commit `feat(sandbox): safety suite and policy scan`.

### Task 4: Eval task format, grader, metrics
**Files:** Create `evaluation/{task,grader,metrics,__init__}.py`, `tests/evaluation/test_{task,grader,metrics}.py`, two sample tasks under `tests/fixtures/tasks/`.
**Interfaces:** Produces `Task(id, category, prompt, fixtures: dict[str,str], hidden_tests: dict[str,str], starter: dict[str,str]|None, reference: dict[str,str])`; `load_tasks(root: Path) -> list[Task]` (dirs `prompt.md`, `fixtures/`, `hidden_tests/`, `starter/`, `reference/`); `grade(task: Task, files: dict[str,str], sandbox: Sandbox) -> GradeResult(passed:bool, output:str)` (copies files + hidden tests into a fresh workspace, runs `pytest -q`); `RunRecord(task_id, system, first_try_pass:bool, final_pass:bool, had_runtime_error:bool, fixed_within_3:bool, attempts:int, tokens_in:int, tokens_out:int, cost_usd:float, wall_s:float)`; `aggregate(records) -> Metrics` with pass@1, final pass rate, `runtime_errors_fixed_pct` (fixed / had_runtime_error, `None` if none), mean attempts, mean cost, mean tokens, mean wall.
- [ ] Tests: loader reads sample tasks; grader passes the reference and fails the starter/empty files; `aggregate` on hand-built records gives exact expected numbers including the no-runtime-errors case.
- [ ] Implement, pass, commit `feat(eval): task format, grader, metrics`.

### Task 5: LLM layer
**Files:** Create `llm/{base,groq_model,fake,pricing,router,__init__}.py`, `tests/llm/test_{fake,pricing,router}.py`.
**Interfaces:** Produces `Usage(tokens_in:int, tokens_out:int)`; `ChatModel` Protocol `invoke(self, system:str, user:str) -> LLMResponse(text:str, usage:Usage)`; `FakeLLM(script: list[str])` (returns scripted replies in order, records calls, raises if exhausted); `cost_usd(model:str, usage:Usage) -> float` from a pricing table in `pricing.py` (Groq list prices per model, used as a notional $ even on the free tier; fill from Groq's pricing page, `None` for unknown models and report tokens only); `ModelRouter(settings, factory=...)` with `for_role(role: Literal["planner","architect","coder","reviewer","debugger"]) -> ChatModel`; `UsageTracker` (thread-safe `add(model, usage)`, `.total_tokens`, `.total_cost`).
- [ ] Tests: router maps planner→cheap, coder→strong; tracker sums; `cost_usd` for known numbers; FakeLLM exhaustion raises.
- [ ] Implement `GroqChatModel` wrapping `langchain-groq`, with exponential backoff on HTTP 429 and a `max_rpm` limiter (backoff and limiter unit-tested with a fake clock; real calls smoke-tested in Task 13). Commit.

### Task 6: Graph state and routing
**Files:** Create `graph/{state,routing,__init__}.py`, `tests/graph/test_routing.py`.
**Interfaces:** Produces `AgentState` (TypedDict: `task`, `plan: list[Step]`, `criteria: list[str]`, `layout: list[str]`, `files: dict[str,str]`, `code_versions: list[dict]`, `last_exec: ExecResult|None`, `verdict: Verdict|None`, `repairs: int`, `replans: int`, `visits: int`, `events: Annotated[list, add]`, `final: FinalReport|None`); `Verdict(action: Literal["pass","fix","replan","stop"], reason:str)`; `route_after_review(state, settings) -> Literal["coder","planner","end"]`.
- [ ] Parameterised tests: `pass`→end; `fix` with repairs<3 →coder; `fix` with repairs==3 →end (stop with failure explanation); `replan` with replans<2 →planner, ==2 →end; visits≥40 →end regardless; unknown action → end.
- [ ] Implement, pass, commit.

### Task 7: Agent nodes and graph
**Files:** Create `agents/{planner,architect,coder,executor,reviewer,prompts,json_out,__init__}.py`, `graph/builder.py`, `tests/agents/test_*.py`, `tests/graph/test_end_to_end_fake.py`.
**Interfaces:** Each node is built by a factory taking deps, e.g. `make_planner(model: ChatModel) -> Callable[[AgentState], dict]`; `make_executor(sandbox: Sandbox, settings) -> ...` (writes files with `write_files`, runs `scan`, runs `python main.py` or `pytest` per plan, truncates output, increments nothing); `parse_json(text:str, schema: type[BaseModel]) -> BaseModel` (strips fences, raises `ParseError`); `build_graph(router: ModelRouter, sandbox: Sandbox, settings) -> CompiledGraph`; `run_task(graph, task:str) -> FinalReport(success:bool, files:dict, explanation:str, repairs:int, usage:Usage)`.
- [ ] Node tests with `FakeLLM`: planner parses plan+criteria; reviewer returns `stop` after one malformed reply plus one retry failing; executor flags policy hit and truncates 10 MB output.
- [ ] End-to-end fake test A: script = plan, layout, buggy code, reviewer `fix`, fixed code, reviewer `pass`, using `DockerSandbox`: final success with `repairs==1` and code versions length 2.
- [ ] Test B: always-buggy coder → stops after exactly 3 repairs with an explanation containing the last error text. Test C: reviewer `replan` goes back to planner (assert node order from `events`).
- [ ] Implement; use the `langgraph-fundamentals` skill (StateGraph, conditional edges). Commit `feat(agents): multi-agent graph`.

### Task 8: Baselines as eval systems
**Files:** Create `evaluation/{systems,runner}.py`, `tests/evaluation/test_{systems,runner}.py`.
**Interfaces:** Produces `System` Protocol `solve(task: Task) -> SystemOutput(files, attempts:int, first_try_pass: bool|None, had_runtime_error:bool, fixed:bool, usage:Usage, wall_s:float)`; `SingleShot(model, sandbox)` (one call, no execution feedback), `SingleAgentLoop(model, sandbox, max_repairs=3)` (one prompt, run, feed stderr back), `GraphSystem(router, sandbox, settings)`; `run_benchmark(tasks, system, sandbox, repeats:int=1, seed:int=0) -> list[RunRecord]` that grades each output with hidden tests and writes `benchmarks/results/<system>-<timestamp>.json` including model names, seed, git SHA.
- [ ] Tests with FakeLLM: SingleShot makes exactly 1 call and never executes; SingleAgentLoop stops after success and after 3 repairs; runner marks `first_try_pass` from the first execution, not the final one.
- [ ] Commit.

### Task 9: Benchmark tasks (30-50)
**Files:** Create `benchmarks/tasks/<id>/...`, `src/coding_agent/evaluation/validate.py`, `tests/benchmark/test_tasks_valid.py` (marker `docker`).
**Interfaces:** Produces `validate_task(task, sandbox) -> list[str]` (problems). A task is valid iff reference passes hidden tests and starter/empty fails.
- [ ] Author ≥40 tasks: 10 data scripts (CSV in fixtures), 8 file processing, 8 CLI apps with tests, 6 charts (assert PNG exists, non-empty, plus data-derived checks), 10 bug-fix (starter has injected bug, record bug type), 4 local-HTML-fixture parsing. Optional later: HumanEval+/MBPP+ subset in `benchmarks/humaneval_plus/`.
- [ ] `test_all_tasks_valid` parametrised over every task; unique ids; hidden tests never referenced from prompts.
- [ ] Commit in batches of about 10 tasks.

### Task 10: CLI
**Files:** Create `cli.py` (Typer), `tests/test_cli.py`.
**Interfaces:** Produces commands `agent run TASK [--workspace PATH] [--all-strong]`, `agent eval --system {single_shot,single_agent,graph} --subset {fast,full}`, `agent safety`, `agent report` (Task 12). `fast` subset = 10 tasks listed in `benchmarks/fast_subset.txt`.
- [ ] Tests: empty task and 4,001-char task exit code 2; `agent safety` prints pass rate (docker marker); `run` with injected fake factory prints plan, attempts and final result.
- [ ] Commit.

### Task 11: Langfuse tracing
**Files:** Create `tracing/{langfuse_setup,__init__}.py`, `tests/tracing/test_tracing.py`.
**Interfaces:** Produces `get_callbacks(settings) -> list` (empty when keys absent, so tests and CI-without-keys work), `trace_metadata(run_id, system, task_id) -> dict`. Each node adds a span with plan, code version index, stderr, verdict.
- [ ] Test: no keys → `[]`, no network calls made; with fake keys → one handler. Use the `langfuse` skill's instrumentation reference for the real integration; manually confirm one run shows plan, code versions, errors, fixes, result in the Langfuse UI.
- [ ] Commit.

### Task 12: Report and ablation table
**Files:** Create `evaluation/report.py`, `tests/evaluation/test_report.py`.
**Interfaces:** Produces `render_markdown(results: list[Path]) -> str` (one row per system/config: pass@1, final, % errors fixed ≤3, attempts, tokens, $, wall) and `agent report --write-readme-table`.
- [ ] Test on hand-written result files; golden Markdown string. Commit.

### Task 13: Real runs and ablations (needs `GROQ_API_KEY`)
- [ ] Verify `model_cheap`/`model_strong` exist via Groq's models endpoint and that the strong model follows the JSON output the agents need; adjust defaults.
- [ ] Smoke test `agent run "parse sales.csv and plot monthly revenue"` end to end; fix prompt problems found.
- [ ] Run `agent eval` for single_shot, single_agent, graph (full, repeats=3), plus ablations: all-strong routing (no cheap/strong split), no architect, no planner. Commit result JSONs.
- [ ] Write the honest conclusion (does the graph help vs cost?) from the numbers.

### Task 14: Web UI with live streaming
**Files:** Create `serving/{app,events,rate_limit}.py`, `serving/static/{index.html,app.js,style.css}`, `tests/serving/test_app.py`.
**Interfaces:** Produces `POST /api/run` → SSE of `{type: plan|layout|code|exec|verdict|final, data}`; 4,000-char input cap; per-IP rate limit (5 runs/hour default); API key only server-side. `agent serve` starts it.
- [ ] Tests with fake graph: events arrive in order; oversize input 413; 6th request 429; response never contains the API key. Apply the Client-ready UI rules (Playground/About tabs, dark default) when polishing, and check screenshots at desktop and phone widths in both themes.
- [ ] Commit.

### Task 15: CI, diagram, README, GIF, deploy
- [ ] `.github/workflows/ci.yml`: lint + unit tests + sandbox safety suite on every push; fast-subset eval for graph only if the repo secret `GROQ_API_KEY` exists, with a request cap; badge in README. (User must add the secret.)
- [ ] `docs/architecture.excalidraw` from `~/.claude/templates/excalidraw_diagram_template.py`, dark theme, Cascadia, rendered and checked.
- [ ] Record the failing → reading error → fixing → passing GIF from a real run.
- [ ] README: architecture, ablation table (generated), safety results, honest limitations, how to run. Then decide hosting (sandbox needs a Docker host or E2B), deploy, and update the `**Live demo:**` line and `~/Documents/deployed-links.md`.
- [ ] Create a `coding-agent-eval` skill in `.claude/skills/` only if the harness work showed a gap in the vendor skills.

## Self-review
- Spec coverage: graph/routing (6-7), self-repair cap (6-7), sandbox limits and safety tests (2-3), benchmark and baselines and metrics (4, 8, 9), ablation (12-13), tracing (11), CLI (10), web UI (14), CI/badge/diagram/GIF/README (15). Optional HumanEval+/MBPP+ is marked optional in Task 9.
- Names checked across tasks: `Sandbox.run`, `ExecResult`, `Limits`, `ModelRouter.for_role`, `RunRecord`, `System.solve`.
