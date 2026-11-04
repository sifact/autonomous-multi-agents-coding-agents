from pathlib import Path

import pytest

from coding_agent.evaluation import CATEGORIES, load_tasks, validate_task
from coding_agent.sandbox import DockerSandbox

IMAGE = "coding-agent-sandbox:latest"
ROOT = Path(__file__).parent.parent.parent / "benchmarks" / "tasks"
TASK_DIRS = sorted(d for d in ROOT.iterdir() if d.is_dir() and not d.name.startswith((".", "_")))
TASKS = load_tasks(ROOT)

pytestmark = pytest.mark.benchmark


def test_ids_unique_and_match_directories():
    ids = [t.id for t in TASKS]
    assert len(ids) == len(set(ids)) == len(TASK_DIRS)


def test_categories_known_and_not_uncategorized():
    assert {t.category for t in TASKS} <= CATEGORIES


def test_fixtures_are_small_text():
    for t in TASKS:
        assert sum(len(v) for v in t.fixtures.values()) < 5000, t.id


@pytest.mark.docker
@pytest.mark.parametrize("task", TASKS, ids=[t.id for t in TASKS])
def test_task_is_valid(task):
    problems = validate_task(task, DockerSandbox(IMAGE), require_difficulty=True)
    assert problems == []
