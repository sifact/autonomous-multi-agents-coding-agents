import json
import sys
from pathlib import Path

ARITY = {"set": 2, "get": 1, "del": 1, "list": 0}


def fail(code: int, message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return code


def load(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not all(isinstance(v, str) for v in data.values()):
        raise ValueError("store must be an object of strings")
    return data


def save(path: Path, store: dict[str, str]) -> None:
    path.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str]) -> int:
    path = Path("store.json")
    rest = list(argv)
    if rest and rest[0] == "--file":
        if len(rest) < 2:
            return fail(2, "--file needs a value")
        path, rest = Path(rest[1]), rest[2:]
    if not rest or rest[0] not in ARITY:
        return fail(2, f"unknown command: {rest[0] if rest else None}")
    command, rest = rest[0], rest[1:]
    if len(rest) != ARITY[command]:
        return fail(2, f"wrong number of arguments for {command}")
    if command == "set" and rest[0] == "":
        return fail(2, "key must not be empty")
    try:
        store = load(path)
    except ValueError as exc:  # JSONDecodeError is a ValueError
        return fail(3, f"bad store file {path}: {exc}")
    if command == "list":
        for key in sorted(store):
            print(f"{key}={store[key]}")
        return 0
    key = rest[0]
    if command == "set":
        store[key] = rest[1]
        save(path, store)
    elif key not in store:
        return fail(1, f"key not found: {key}")
    elif command == "get":
        print(store[key])
    else:
        del store[key]
        save(path, store)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
