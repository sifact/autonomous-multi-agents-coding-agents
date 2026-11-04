import os


def summarize_tree(root: str) -> list[dict]:
    if not os.path.isdir(root):
        raise FileNotFoundError(root)
    totals: dict[str, list[int]] = {}
    for folder, _dirs, files in os.walk(root):
        for name in files:
            ext = os.path.splitext(name)[1].lower() or "(none)"
            entry = totals.setdefault(ext, [0, 0])
            entry[0] += 1
            entry[1] += os.path.getsize(os.path.join(folder, name))
    rows = [{"ext": e, "count": c, "bytes": b} for e, (c, b) in totals.items()]
    return sorted(rows, key=lambda r: (-r["bytes"], r["ext"]))
