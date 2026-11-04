import os


def merge_files(paths: list[str], out_path: str) -> int:
    blocks = []
    for path in paths:
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read()
        if text and not text.endswith("\n"):
            text += "\n"
        blocks.append(f"==> {os.path.basename(path)} <==\n{text}")
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(blocks))
    return len(paths)
