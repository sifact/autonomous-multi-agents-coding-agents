import os
import re


def rename_files(
    directory: str, pattern: str, replacement: str, apply: bool = False
) -> list[tuple[str, str]]:
    names = os.listdir(directory)
    taken = set(names)
    plan: list[tuple[str, str]] = []
    for old in sorted(n for n in names if os.path.isfile(os.path.join(directory, n))):
        new = re.sub(pattern, replacement, old)
        if new == old:
            continue
        if new in taken:
            stem, ext = os.path.splitext(new)
            i = 1
            while f"{stem}_{i}{ext}" in taken:
                i += 1
            new = f"{stem}_{i}{ext}"
        taken.add(new)
        plan.append((old, new))
    if apply:
        for old, new in plan:
            os.rename(os.path.join(directory, old), os.path.join(directory, new))
    return plan
