import csv
from datetime import datetime, timedelta, timezone

BUCKETS = ("hour", "day", "week", "month")


def _parse(text: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(text.strip())
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _start(dt: datetime, bucket: str) -> datetime:
    if bucket == "hour":
        return dt.replace(minute=0, second=0, microsecond=0)
    day = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    if bucket == "day":
        return day
    if bucket == "week":
        return day - timedelta(days=day.weekday())
    return day.replace(day=1)


def _next(start: datetime, bucket: str) -> datetime:
    if bucket == "hour":
        return start + timedelta(hours=1)
    if bucket == "day":
        return start + timedelta(days=1)
    if bucket == "week":
        return start + timedelta(weeks=1)
    return (start.replace(day=28) + timedelta(days=4)).replace(day=1)


def _label(start: datetime, bucket: str) -> str:
    fmt = {"hour": "%Y-%m-%d %H:00", "day": "%Y-%m-%d", "week": "%Y-%m-%d", "month": "%Y-%m"}
    return start.strftime(fmt[bucket])


def bucket_events(path: str, bucket: str) -> dict[str, int]:
    if bucket not in BUCKETS:
        raise ValueError(f"unknown bucket {bucket!r}")
    starts: dict[datetime, int] = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            dt = _parse(row["timestamp"])
            if dt is not None:
                key = _start(dt, bucket)
                starts[key] = starts.get(key, 0) + 1
    if not starts:
        return {}
    result = {}
    current, last = min(starts), max(starts)
    while current <= last:
        result[_label(current, bucket)] = starts.get(current, 0)
        current = _next(current, bucket)
    return result
