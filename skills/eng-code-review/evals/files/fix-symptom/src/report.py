"""Totals for statement lines."""
from money import parse_amount


def total(lines: list[str]) -> float:
    result = 0.0
    for line in lines:
        value = parse_amount(line)
        if line.strip().startswith("("):
            value = -abs(value)
        result += value
    return round(result, 2)
