import hashlib
from pathlib import Path


def find_duplicates(root: str) -> list[list[str]]:
    base = Path(root)
    if not base.is_dir():
        raise FileNotFoundError(root)
    groups: dict[str, list[str]] = {}
    for path in base.rglob("*"):
        if path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            groups.setdefault(digest, []).append(path.relative_to(base).as_posix())
    found = [sorted(g) for g in groups.values() if len(g) > 1]
    return sorted(found)
