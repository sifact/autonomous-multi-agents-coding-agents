import configparser
import re

_TRUE = {"true", "yes", "on"}
_FALSE = {"false", "no", "off"}


def _coerce(value: str):
    low = value.strip().lower()
    if low in _TRUE:
        return True
    if low in _FALSE:
        return False
    text = value.strip()
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    return text


def load_config(path: str) -> dict:
    parser = configparser.ConfigParser(interpolation=None, inline_comment_prefixes=(";", "#"))
    with open(path, encoding="utf-8") as f:
        parser.read_file(f)
    return {
        section: {key: _coerce(val) for key, val in parser.items(section)}
        for section in parser.sections()
    }
