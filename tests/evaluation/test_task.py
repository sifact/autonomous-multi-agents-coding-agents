from pathlib import Path

import pytest

from coding_agent.evaluation import load_tasks

TASKS = Path(__file__).parent.parent / "fixtures" / "tasks"


def test_loads_sample_tasks_sorted():
    tasks = load_tasks(TASKS)
    assert [t.id for t in tasks] == ["fix_mean", "sum_csv"]


def test_task_fields():
    by_id = {t.id: t for t in load_tasks(TASKS)}
    s = by_id["sum_csv"]
    assert s.category == "data_script"
    assert "total" in s.prompt
    assert s.fixtures["data.csv"].startswith("name,amount")
    assert "tests/test_hidden.py" in s.hidden_tests
    assert s.starter is None
    assert "solution.py" in s.reference
    f = by_id["fix_mean"]
    assert f.category == "bug_fix"
    assert f.starter is not None and "stats.py" in f.starter
    assert f.fixtures == {}


def test_missing_prompt_raises(tmp_path):
    (tmp_path / "t1" / "hidden_tests").mkdir(parents=True)
    (tmp_path / "t1" / "hidden_tests" / "test_x.py").write_text("")
    (tmp_path / "t1" / "task.toml").write_text('category = "x"\n')
    with pytest.raises(ValueError, match="prompt.md"):
        load_tasks(tmp_path)


def test_missing_hidden_tests_raises(tmp_path):
    (tmp_path / "t1").mkdir()
    (tmp_path / "t1" / "prompt.md").write_text("do it")
    (tmp_path / "t1" / "task.toml").write_text('category = "x"\n')
    with pytest.raises(ValueError, match="hidden_tests"):
        load_tasks(tmp_path)


def test_skips_hidden_and_underscore_dirs(tmp_path):
    for name in (".git", "__pycache__", "_draft"):
        (tmp_path / name).mkdir()
    assert load_tasks(tmp_path) == []


def test_difficulty_read_from_toml(tmp_path):
    d = tmp_path / "t"
    (d / "hidden_tests").mkdir(parents=True)
    (d / "hidden_tests" / "test_x.py").write_text("def test_x():\n    assert 1\n")
    (d / "prompt.md").write_text("p")
    (d / "task.toml").write_text('category = "data_script"\ndifficulty = "hard"\n')
    from coding_agent.evaluation import load_task

    assert load_task(d).difficulty == "hard"
    (d / "task.toml").write_text('category = "data_script"\n')
    assert load_task(d).difficulty is None
