import math
import re
import sys

NUMBER = re.compile(r"-?[0-9]+(\.[0-9]+)?")


class CalcError(Exception):
    """An evaluation error whose text is printed after ``error: ``."""


def power(a: float, b: float) -> float:
    try:
        result = a**b
    except (ArithmeticError, ValueError) as exc:
        raise CalcError("invalid power") from exc
    if isinstance(result, complex):
        raise CalcError("invalid power")
    return result


def binary(op: str, a: float, b: float) -> float:
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "^":
        return power(a, b)
    if b == 0:
        raise CalcError("division by zero")
    return a / b


def evaluate(line: str) -> float:
    stack: list[float] = []

    def need(count: int) -> None:
        if len(stack) < count:
            raise CalcError("stack underflow")

    for token in line.split():
        if NUMBER.fullmatch(token):
            stack.append(float(token))
        elif token in ("+", "-", "*", "/", "^"):
            need(2)
            b, a = stack.pop(), stack.pop()
            stack.append(binary(token, a, b))
        elif token == "neg":
            need(1)
            stack.append(-stack.pop())
        elif token == "dup":
            need(1)
            stack.append(stack[-1])
        elif token == "swap":
            need(2)
            stack[-2], stack[-1] = stack[-1], stack[-2]
        else:
            raise CalcError(f"bad token: {token}")
        if not math.isfinite(stack[-1]):
            raise CalcError("overflow")
    if len(stack) > 1:
        raise CalcError("too many values")
    return stack[0]


def render(value: float) -> str:
    return str(int(value)) if value.is_integer() else f"{value:.6g}"


def main(argv: list[str]) -> int:
    if argv:
        print("error: takes no arguments", file=sys.stderr)
        return 2
    status = 0
    for line in sys.stdin.buffer.read().decode("utf-8").split("\n"):
        if not line.split():
            continue
        try:
            print(render(evaluate(line)))
        except CalcError as exc:
            print(f"error: {exc}")
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
