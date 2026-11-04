import argparse
import re
import sys

LEVELS = ["DEBUG", "INFO", "WARN", "ERROR", "FATAL"]
ENTRY = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2} "
                   r"(DEBUG|INFO|WARN|ERROR|FATAL)(?: |$)")


def parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("file", nargs="?", default="-")
    parser.add_argument("--min-level", default="DEBUG")
    parser.add_argument("--summary", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return None
    args.min_level = args.min_level.upper()
    return args if args.min_level in LEVELS else None


def read_lines(path: str) -> list[str]:
    if path == "-":
        data = sys.stdin.buffer.read()
    else:
        with open(path, "rb") as handle:
            data = handle.read()
    lines = data.decode("utf-8").split("\n")
    if lines[-1] == "":
        lines.pop()
    return lines


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args is None:
        print("error: bad arguments", file=sys.stderr)
        return 2
    try:
        lines = read_lines(args.file)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"error: cannot read {args.file}: {exc}", file=sys.stderr)
        return 3
    floor = LEVELS.index(args.min_level)
    counts = dict.fromkeys(LEVELS, 0)
    selected: list[str] = []
    keep = False
    for line in lines:
        match = ENTRY.match(line)
        if match:
            keep = LEVELS.index(match.group(1)) >= floor
            if keep:
                counts[match.group(1)] += 1
        if keep:
            selected.append(line)
    if not any(counts.values()):
        return 1
    if args.summary:
        for level in LEVELS:
            if counts[level]:
                print(f"{level}: {counts[level]}")
    else:
        for line in selected:
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
