import json
import sys
from pathlib import Path

STATE = Path("todo.json")


def fail(code: int, message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return code


def valid(data: object) -> bool:
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        return False
    if type(data.get("next_id")) is not int:
        return False
    return all(
        isinstance(i, dict)
        and type(i.get("id")) is int
        and isinstance(i.get("text"), str)
        and isinstance(i.get("done"), bool)
        for i in data["items"]
    )


def load() -> dict:
    if not STATE.exists():
        return {"next_id": 1, "items": []}
    data = json.loads(STATE.read_text(encoding="utf-8"))
    if not valid(data):
        raise ValueError("unexpected todo.json shape")
    return data


def save(data: dict) -> None:
    STATE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_id(text: str) -> int | None:
    if not text.isascii() or not text.isdigit() or int(text) < 1:
        return None
    return int(text)


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in {"add", "list", "done", "rm"}:
        return fail(2, "usage: main.py add|list|done|rm ...")
    command, rest = argv[0], argv[1:]
    if command == "add" and not " ".join(rest).strip():
        return fail(2, "text must not be empty")
    if command == "list" and rest not in ([], ["--pending"]):
        return fail(2, "usage: main.py list [--pending]")
    item_id = None
    if command in ("done", "rm"):
        item_id = parse_id(rest[0]) if len(rest) == 1 else None
        if item_id is None:
            return fail(2, f"{command} needs one positive integer id")
    try:
        data = load()
    except ValueError as exc:
        return fail(3, f"bad todo.json: {exc}")
    items = data["items"]
    if command == "add":
        item = {"id": data["next_id"], "text": " ".join(rest).strip(), "done": False}
        items.append(item)
        data["next_id"] += 1
        save(data)
        print(f"added {item['id']}")
    elif command == "list":
        shown = [i for i in items if not (rest and i["done"])]
        for i in shown:
            print(f"[{'x' if i['done'] else ' '}] {i['id']} {i['text']}")
        if not shown:
            print("no items")
    else:
        match = next((i for i in items if i["id"] == item_id), None)
        if match is None:
            return fail(1, f"no such id: {item_id}")
        if command == "rm":
            items.remove(match)
            save(data)
            print(f"removed {item_id}")
        else:
            if not match["done"]:
                match["done"] = True
                save(data)
            print(f"done {item_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
