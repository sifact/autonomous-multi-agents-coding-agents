import pytest

from coding_agent.evaluation import SAFETY_CASES, run_case, run_safety_suite
from coding_agent.sandbox import DockerSandbox

docker = pytest.mark.docker
IMAGE = "coding-agent-sandbox:latest"
NAMES = ["fork_bomb", "infinite_loop", "memory_hog", "delete_outside_workspace",
         "network_call", "disk_fill", "read_host_path"]


@pytest.fixture(scope="module")
def sandbox():
    return DockerSandbox(IMAGE)


def test_all_expected_cases_defined():
    assert [c.name for c in SAFETY_CASES] == NAMES


@docker
@pytest.mark.parametrize("name", NAMES)
def test_case_is_contained(sandbox, name):
    case = next(c for c in SAFETY_CASES if c.name == name)
    result = run_case(sandbox, case)
    assert result.passed, f"{name} not contained: {result.detail}"


@docker
def test_suite_reports_all_passed(sandbox):
    report = run_safety_suite(sandbox)
    assert report.total == len(NAMES)
    assert report.passed == report.total and report.pass_rate == 1.0
    assert [r.name for r in report.results] == NAMES


def test_failing_case_is_reported_not_hidden():
    from coding_agent.evaluation import SafetyCase
    from coding_agent.sandbox import ExecResult

    class Leaky:
        def run(self, workspace, command, limits=None):
            return ExecResult(0, "", "", False, False, 0.0)

    case = SafetyCase("x", "pass", expect=lambda r: r.timed_out)
    assert not run_case(Leaky(), case).passed
