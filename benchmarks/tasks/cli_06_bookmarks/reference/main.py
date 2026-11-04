import argparse
import json
import sys
from collections import Counter
from pathlib import Path

STATE = Path("bookmarks.json")


def fail(code: int, message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return code


def valid(data: object) -> bool:
    if not isinstance(data, dict) or type(data.get("next_id")) is not int:
        return False
    if not isinstance(data.get("items"), list):
        return False
    return all(
        isinstance(i, dict)
        and type(i.get("id")) is int
        and isinstance(i.get("url"), str)
        and isinstance(i.get("title"), str)
        and isinstance(i.get("tags"), list)
        and all(isinstance(t, str) for t in i["tags"])
        for i in data["items"]
    )


def load() -> dict:
    if not STATE.exists():
        return {"next_id": 1, "items": []}
    data = json.loads(STATE.read_text(encoding="utf-8"))
    if not valid(data):
        raise ValueError("unexpected bookmarks.json shape")
    return data


def save(data: dict) -> None:
    STATE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def positive_id(text: str) -> int:
    if not text.isascii() or not text.isdigit() or int(text) < 1:
        raise argparse.ArgumentTypeError("id must be a positive integer")
    return int(text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add", add_help=False)
    add.add_argument("url")
    add.add_argument("--title")
    add.add_argument("--tag", action="append", default=[])
    listing = sub.add_parser("list", add_help=False)
    listing.add_argument("--tag")
    remove = sub.add_parser("rm", add_help=False)
    remove.add_argument("id", type=positive_id)
    sub.add_parser("tags", add_help=False)
    return parser


def clean_tags(raw: list[str]) -> list[str] | None:
    tags: list[str] = []
    for tag in (t.strip().lower() for t in raw):
        if not tag:
            return None
        if tag not in tags:
            tags.append(tag)
    return tags


def add_bookmark(data: dict, args: argparse.Namespace) -> int:
    url = args.url.strip()
    tags = clean_tags(args.tag)
    if not url or tags is None:
        return fail(2, "url and tags must not be empty")
    existing = next((i for i in data["items"] if i["url"] == url), None)
    if existing:
        existing["tags"] += [t for t in tags if t not in existing["tags"]]
        save(data)
        print(f"exists {existing['id']}")
        return 0
    item = {"id": data["next_id"], "url": url, "title": args.title or url, "tags": tags}
    data["items"].append(item)
    data["next_id"] += 1
    save(data)
    print(f"added {item['id']}")
    return 0


def main(argv: list[str]) -> int:
    try:
        args = build_parser().parse_args(argv)
    except SystemExit:
        return 2
    try:
        data = load()
    except ValueError as exc:
        return fail(3, f"bad bookmarks.json: {exc}")
    items = data["items"]
    if args.command == "add":
        return add_bookmark(data, args)
    if args.command == "list":
        wanted = args.tag.strip().lower() if args.tag is not None else None
        for i in items:
            if wanted is None or wanted in i["tags"]:
                print(f"{i['id']}\t{i['title']}\t{i['url']}\t{','.join(i['tags'])}")
    elif args.command == "tags":
        counts = Counter(t for i in items for t in i["tags"])
        for tag, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"{tag} {count}")
    else:
        match = next((i for i in items if i["id"] == args.id), None)
        if match is None:
            return fail(1, f"no such id: {args.id}")
        items.remove(match)
        save(data)
        print(f"removed {args.id}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
