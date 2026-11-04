"""Advisory static scan of generated code for risky constructs.

This is a hint for the agent and for reports, NOT a security boundary: it is
trivially bypassed (getattr tricks, string building). The container (no network,
read-only root, dropped caps, resource limits) is the real enforcement.

The code is only parsed with `ast`, never executed. On a syntax error the AST
pass is skipped (no `syntax_error` flag); the regex pass still runs on the text.
"""
import ast
import re
from dataclasses import dataclass

SHELL_EXEC = "shell_exec"
NETWORK = "network"
DESTRUCTIVE_FS = "destructive_fs"
FORK = "fork"

_SHELL_CALLS = {
    "os.system", "os.popen", "os.execv", "os.execve", "os.execvp", "os.spawnl", "os.spawnv",
    "subprocess.run", "subprocess.call", "subprocess.Popen", "subprocess.check_call",
    "subprocess.check_output", "eval", "exec",
}
_NETWORK_MODULES = {"socket", "urllib", "requests", "http", "httpx", "ftplib", "smtplib", "aiohttp"}
_DELETE_CALLS = {"shutil.rmtree", "os.remove", "os.unlink", "os.rmdir", "os.removedirs"}
_FORK_CALLS = {"os.fork", "os.forkpty"}
_RM_RF = re.compile(r"\brm\s+-[a-zA-Z]*[rR][a-zA-Z]*\s+(-\w+\s+)*/")


@dataclass(frozen=True)
class PolicyFlag:
    """One advisory finding: which rule fired and on which 1-based line."""

    rule: str
    line: int


def _dotted(node: ast.AST) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _is_absolute_path_arg(call: ast.Call) -> bool:
    arg = call.args[0] if call.args else None
    return (
        isinstance(arg, ast.Constant)
        and isinstance(arg.value, str)
        and arg.value.startswith("/")
    )


def _scan_ast(tree: ast.AST) -> list[PolicyFlag]:
    flags = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(a.name.split(".")[0] in _NETWORK_MODULES for a in node.names):
                flags.append(PolicyFlag(NETWORK, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] in _NETWORK_MODULES:
                flags.append(PolicyFlag(NETWORK, node.lineno))
        elif isinstance(node, ast.Call):
            name = _dotted(node.func)
            if name in _SHELL_CALLS:
                flags.append(PolicyFlag(SHELL_EXEC, node.lineno))
            elif name in _FORK_CALLS:
                flags.append(PolicyFlag(FORK, node.lineno))
            elif name in _DELETE_CALLS and _is_absolute_path_arg(node):
                flags.append(PolicyFlag(DESTRUCTIVE_FS, node.lineno))
    return flags


def _scan_text(code: str) -> list[PolicyFlag]:
    return [
        PolicyFlag(DESTRUCTIVE_FS, i)
        for i, line in enumerate(code.splitlines(), 1)
        if _RM_RF.search(line)
    ]


def scan(code: str) -> list[PolicyFlag]:
    """Return advisory flags for `code`, sorted by line; [] means nothing suspicious."""
    try:
        flags = _scan_ast(ast.parse(code))
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        flags = []
    flags += _scan_text(code)
    return sorted(set(flags), key=lambda f: (f.line, f.rule))
