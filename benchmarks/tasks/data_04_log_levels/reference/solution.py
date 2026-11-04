import re

LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
ENTRY = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \[(DEBUG|INFO|WARNING|ERROR|CRITICAL)\]")


def count_levels(path: str) -> dict[str, int]:
    counts = dict.fromkeys(LEVELS, 0)
    with open(path) as f:
        for line in f:
            match = ENTRY.match(line)
            if match:
                counts[match.group(1)] += 1
    return counts
