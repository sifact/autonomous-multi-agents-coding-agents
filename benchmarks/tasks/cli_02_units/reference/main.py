import math
import sys

LENGTH = {"m": 1.0, "km": 1000.0, "cm": 0.01, "in": 0.0254, "ft": 0.3048, "mi": 1609.344}
TEMPERATURE = {"c", "f", "k"}


def fail(code: int, message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return code


def to_kelvin(value: float, unit: str) -> float:
    if unit == "c":
        return value + 273.15
    if unit == "f":
        return (value - 32) * 5 / 9 + 273.15
    return value


def from_kelvin(kelvin: float, unit: str) -> float:
    if unit == "c":
        return kelvin - 273.15
    if unit == "f":
        return (kelvin - 273.15) * 9 / 5 + 32
    return kelvin


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        return fail(2, "usage: main.py VALUE FROM TO")
    try:
        value = float(argv[0])
    except ValueError:
        return fail(2, f"not a number: {argv[0]}")
    if not math.isfinite(value):
        return fail(2, f"not a finite number: {argv[0]}")
    source, target = argv[1].lower(), argv[2].lower()
    for unit in (source, target):
        if unit not in LENGTH and unit not in TEMPERATURE:
            return fail(3, f"unknown unit: {unit}")
    if (source in LENGTH) != (target in LENGTH):
        return fail(4, f"cannot convert {source} to {target}")
    if source in LENGTH:
        result = value * LENGTH[source] / LENGTH[target]
    else:
        kelvin = to_kelvin(value, source)
        if kelvin < 0:
            return fail(5, "temperature below absolute zero")
        result = from_kelvin(kelvin, target)
    print(f"{result:.4f} {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
