import pytest

from coding_agent.sandbox import PolicyFlag, scan


def rules(code):
    return {(f.rule, f.line) for f in scan(code)}


def test_os_system_flags_shell_exec_line_1():
    assert scan("os.system('ls')") == [PolicyFlag("shell_exec", 1)]


def test_benign_code_is_clean():
    assert scan("def f(x):\n    return x + 1\nprint(f(2))\n") == []


@pytest.mark.parametrize("code", [
    "import subprocess\nsubprocess.run(['ls'])",
    "import os\nos.popen('ls')",
    "eval('1+1')",
    "exec('x=1')",
])
def test_shell_exec_variants(code):
    assert any(f.rule == "shell_exec" for f in scan(code))


@pytest.mark.parametrize("code", [
    "import socket",
    "import urllib.request",
    "from urllib.request import urlopen",
    "import requests\nrequests.get('http://x')",
    "import http.client",
])
def test_network(code):
    assert any(f.rule == "network" for f in scan(code))


@pytest.mark.parametrize("code", [
    "import shutil\nshutil.rmtree('/')",
    "import os\nos.remove('/etc/passwd')",
    "x = 'rm -rf /'",
])
def test_destructive_fs(code):
    assert any(f.rule == "destructive_fs" for f in scan(code))


def test_relative_remove_is_fine():
    assert scan("import os\nos.remove('tmp.txt')") == []


def test_fork():
    assert ("fork", 2) in rules("import os\nos.fork()")


def test_line_numbers_point_at_the_call():
    assert ("shell_exec", 3) in rules("x = 1\n\nos.system('ls')")


def test_syntax_error_does_not_crash_and_returns_empty_ast_part():
    assert scan("def (:") == []


def test_syntax_error_still_regex_scanned():
    assert ("destructive_fs", 2) in rules("def (:\nrm -rf /")
