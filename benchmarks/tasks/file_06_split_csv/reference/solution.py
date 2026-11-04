import csv
import os


def split_csv(path: str, rows_per_chunk: int, out_dir: str) -> list[str]:
    if rows_per_chunk < 1:
        raise ValueError("rows_per_chunk must be at least 1")
    stem = os.path.splitext(os.path.basename(path))[0]
    written: list[str] = []

    def flush(header: list[str], rows: list[list[str]]) -> None:
        os.makedirs(out_dir, exist_ok=True)
        target = os.path.join(out_dir, f"{stem}_part{len(written) + 1:03d}.csv")
        with open(target, "w", newline="", encoding="utf-8") as out:
            writer = csv.writer(out, lineterminator="\n")
            writer.writerow(header)
            writer.writerows(rows)
        written.append(target)

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            return []
        rows: list[list[str]] = []
        for row in reader:
            rows.append(row)
            if len(rows) == rows_per_chunk:
                flush(header, rows)
                rows = []
        if rows:
            flush(header, rows)
    return written
