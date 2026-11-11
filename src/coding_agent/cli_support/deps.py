"""The one place the CLI builds its dependencies (settings, models, sandbox, systems).

Tests monkeypatch these functions to inject scripted models and fake systems, so
the CLI never needs a network or an API key under test. The CLI calls them as
``deps.<name>`` (module attribute) so a patch takes effect.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from coding_agent.config import Settings
from coding_agent.evaluation import (
    GraphSystem,
    SingleAgentLoop,
    SingleShot,
    run_safety_suite,  # noqa: F401 - re-exported so tests can patch it here
)
from coding_agent.evaluation.runner import REPO_ROOT
from coding_agent.evaluation.systems import System
from coding_agent.llm import ModelRouter, UsageTracker
from coding_agent.sandbox import DockerSandbox

MISSING_KEY_MESSAGE = "GROQ_API_KEY is not set. Copy .env.example to .env and add your key"
DOCKER_DOWN_MESSAGE = (
    "Docker is not available. Start Docker Desktop, or on a Mac run: "
    "colima start --cpu 2 --memory 4 --disk 20"
)
BUILD_COMMAND = "docker build -t coding-agent-sandbox:latest -f docker/sandbox.Dockerfile ."
SYSTEMS = ("single_shot", "single_agent", "graph")


class SetupError(RuntimeError):
    """The environment is not ready (no key, no Docker, no image): CLI exit code 3."""


def load_settings() -> Settings:
    return Settings()


def tasks_dir() -> Path:
    """Benchmark tasks, resolved from the repo root so the CWD does not matter."""
    return REPO_ROOT / "benchmarks" / "tasks"


def make_router(
    settings: Settings, tracker: UsageTracker | None, all_strong: bool = False
) -> ModelRouter:
    if not (settings.groq_api_key and settings.groq_api_key.get_secret_value()):
        raise SetupError(MISSING_KEY_MESSAGE)
    return ModelRouter(settings, tracker, all_strong=all_strong)


def _docker(*args: str) -> tuple[int, str]:
    """Run a docker CLI command; (exit code, combined output). 127 if docker is missing."""
    try:
        proc = subprocess.run(
            ["docker", *args], capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, str(exc)
    return proc.returncode, proc.stdout + proc.stderr


def make_sandbox(settings: Settings) -> DockerSandbox:
    if _docker("info")[0] != 0:
        raise SetupError(DOCKER_DOWN_MESSAGE)
    if _docker("image", "inspect", settings.sandbox_image)[0] != 0:
        raise SetupError(
            f"Sandbox image {settings.sandbox_image!r} not found. Build it with:\n  {BUILD_COMMAND}"
        )
    return DockerSandbox(settings.sandbox_image)


def build_system(
    name: str, settings: Settings, sandbox: DockerSandbox, all_strong: bool = False
) -> System:
    """The eval system exactly as the runner expects it (baselines use the strong model)."""
    if name == "graph":
        return GraphSystem(lambda tracker: make_router(settings, tracker, all_strong),
                           sandbox, settings)
    router = make_router(settings, None, all_strong)
    model, model_name = router.for_role("coder"), router.model_name("coder")
    if name == "single_shot":
        return SingleShot(model, sandbox, model_name=model_name)
    if name == "single_agent":
        return SingleAgentLoop(model, sandbox, settings, model_name=model_name)
    raise ValueError(f"unknown system {name!r}; expected one of {SYSTEMS}")
