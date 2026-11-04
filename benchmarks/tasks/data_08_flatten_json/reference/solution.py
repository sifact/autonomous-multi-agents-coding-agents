import json


def _join(prefix: str | None, part: str, sep: str) -> str:
    return part if prefix is None else f"{prefix}{sep}{part}"


def _walk(value, prefix: str | None, sep: str, out: dict) -> None:
    """``prefix`` is None only at the document root, so "" stays a valid key."""
    if isinstance(value, dict) and value:
        for key, child in value.items():
            _walk(child, _join(prefix, str(key), sep), sep, out)
    elif isinstance(value, list) and value:
        for index, child in enumerate(value):
            _walk(child, _join(prefix, str(index), sep), sep, out)
    elif prefix is not None:
        out[prefix] = value


def flatten_file(path: str, sep: str = ".") -> dict:
    with open(path) as f:
        data = json.load(f)
    out: dict = {}
    _walk(data, None, sep, out)
    return out
