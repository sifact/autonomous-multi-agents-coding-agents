from coding_agent.cli_support.format import sanitize
from coding_agent.cli_support.printer import StepPrinter
from coding_agent.sandbox import ExecResult


def test_sanitize_drops_whole_sequences_and_controls():
    assert sanitize("a\x1b]0;title\x07b") == "ab"
    assert sanitize("a\x1b]0;title\x1b\\b") == "ab"
    assert sanitize("a\x1b[2Jb\x1b[31;1mc") == "abc"
    assert sanitize("a\x9b31mb") == "ab"
    assert sanitize("a\x07b\x85c\x00d\x7fe\rf") == "abcdef"
    assert sanitize("keep\ttabs\nand newlines") == "keep\ttabs\nand newlines"
    assert sanitize("plain [2J text") == "plain [2J text"


def test_printer_handles_executor_without_a_command():
    lines: list[str] = []
    r = ExecResult(1, "", "The coder produced no files.", False, False, 0.0)
    StepPrinter(lines.append).handle("executor", {
        "code_versions": [{"version": 1, "command": None, "summary": "exit 1", "flags": []}],
        "last_exec": r,
    })
    text = "\n".join(lines)
    assert "not run" in text and "The coder produced no files." in text
