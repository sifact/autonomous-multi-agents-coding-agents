import argparse
import sys
from collections import Counter


def positive_int(text: str) -> int:
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return value


def words(text: str) -> list[str]:
    found, current = [], []
    for ch in text.lower():
        if ch.isalnum():
            current.append(ch)
        elif current:
            found.append("".join(current))
            current = []
    if current:
        found.append("".join(current))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description="Count word frequencies.")
    parser.add_argument("file", nargs="?", default="-")
    parser.add_argument("--top", type=positive_int, default=10)
    args = parser.parse_args()
    try:
        if args.file == "-":
            text = sys.stdin.buffer.read().decode("utf-8")
        else:
            with open(args.file, encoding="utf-8") as handle:
                text = handle.read()
    except (OSError, UnicodeDecodeError) as exc:
        print(f"error: cannot read {args.file}: {exc}", file=sys.stderr)
        return 2
    counts = Counter(words(text))
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    for word, count in ranked[: args.top]:
        print(f"{count} {word}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
