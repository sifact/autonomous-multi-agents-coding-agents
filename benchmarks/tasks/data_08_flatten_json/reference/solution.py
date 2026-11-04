import json


def _walk(value, prefix: str, sep: str, out: dict) -> None:
    if isinstance(value, dict) and value:
        for key, child in value.items():
            _walk(child, f"{prefix}{sep}{key}" if prefix else str(key), sep, out)
    elif isinstance(value, list) and value:
        for index, child in enumerate(value):
            _walk(child, f"{prefix}{sep}{index}" if prefix else str(index), sep, out)
    elif prefix:
        out[prefix] = value


def flatten_file(path: str, sep: str = ".") -> dict:
    with open(path) as f:
        data = json.load(f)
    out: dict = {}
    _walk(data, "", sep, out)
    return out
