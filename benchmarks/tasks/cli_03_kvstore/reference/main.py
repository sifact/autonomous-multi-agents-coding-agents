import argparse
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
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--file", default="store.json")
    parser.add_argument("command", nargs="?")
    parser.add_argument("rest", nargs="*")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2
    if args.command not in ARITY:
        return fail(2, f"unknown command: {args.command}")
    if len(args.rest) != ARITY[args.command]:
        return fail(2, f"wrong number of arguments for {args.command}")
    path = Path(args.file)
    try:
        store = load(path)
    except ValueError as exc:  # JSONDecodeError is a ValueError
        return fail(3, f"bad store file {path}: {exc}")
    if args.command == "list":
        for key in sorted(store):
            print(f"{key}={store[key]}")
        return 0
    key = args.rest[0]
    if args.command == "set":
        if key == "":
            return fail(2, "key must not be empty")
        store[key] = args.rest[1]
        save(path, store)
    elif key not in store:
        return fail(1, f"key not found: {key}")
    elif args.command == "get":
        print(store[key])
    else:
        del store[key]
        save(path, store)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
