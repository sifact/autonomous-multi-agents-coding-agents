from collections import Counter
from pathlib import Path

import pytest

from coding_agent.evaluation import load_fast_subset

ROOT = Path(__file__).parent.parent.parent / "benchmarks" / "tasks"
EXPECTED_MIX = {
    "data_script": 2, "file_processing": 2, "html_fixture": 1,
    "cli_app": 2, "chart": 1, "bug_fix": 2,
}

pytestmark = pytest.mark.benchmark


def test_fast_subset_has_ten_existing_tasks_with_the_stated_mix():
    tasks = load_fast_subset(ROOT)
    assert len(tasks) == 10
    assert len({t.id for t in tasks}) == 10
    assert Counter(t.category for t in tasks) == EXPECTED_MIX


def test_fast_subset_is_easy_or_medium_only():
    assert {t.difficulty for t in load_fast_subset(ROOT)} <= {"easy", "medium"}


def test_ids_in_the_file_all_exist_on_disk():
    path = ROOT.parent / "fast_subset.txt"
    ids = [ln.strip() for ln in path.read_text().splitlines()
           if ln.strip() and not ln.startswith("#")]
    assert len(ids) == 10
    assert all((ROOT / i).is_dir() for i in ids)


def test_loader_skips_comments_and_keeps_order(tmp_path):
    lst = tmp_path / "list.txt"
    lst.write_text("# note\n\nbugfix_05_leaderboard_ties\n  data_02_top_customers  \n")
    assert [t.id for t in load_fast_subset(ROOT, lst)] == [
        "bugfix_05_leaderboard_ties", "data_02_top_customers",
    ]


def test_loader_rejects_unknown_and_repeated_ids(tmp_path):
    lst = tmp_path / "list.txt"
    lst.write_text("data_02_top_customers\nno_such_task\n")
    with pytest.raises(ValueError, match="no_such_task"):
        load_fast_subset(ROOT, lst)
    lst.write_text("data_02_top_customers\ndata_02_top_customers\n")
    with pytest.raises(ValueError, match="duplicate"):
        load_fast_subset(ROOT, lst)
