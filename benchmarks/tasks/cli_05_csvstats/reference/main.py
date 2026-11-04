import argparse
import csv
import math
import statistics
import sys


def fail(code: int, message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return code


def parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("file")
    parser.add_argument("--column", required=True)
    try:
        return parser.parse_args(argv)
    except SystemExit:
        return None


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args is None:
        return fail(2, "usage: main.py FILE --column NAME")
    try:
        with open(args.file, encoding="utf-8-sig", newline="") as handle:
            records = list(csv.reader(handle))
    except (OSError, UnicodeDecodeError) as exc:
        return fail(2, f"cannot read {args.file}: {exc}")
    if not records or args.column not in records[0]:
        return fail(4, f"no such column: {args.column}")
    index = records[0].index(args.column)
    values: list[float] = []
    rows = (r for r in records[1:] if r)
    for number, row in enumerate(rows, start=1):
        cell = row[index].strip() if index < len(row) else ""
        if not cell:
            continue
        try:
            value = float(cell)
        except ValueError:
            value = math.nan
        if not math.isfinite(value):
            return fail(3, f"row {number}: not a number: {cell}")
        values.append(value)
    print(f"count: {len(values)}")
    if values:
        print(f"min: {min(values):.2f}")
        print(f"max: {max(values):.2f}")
        print(f"mean: {sum(values) / len(values):.2f}")
        print(f"median: {statistics.median(values):.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
