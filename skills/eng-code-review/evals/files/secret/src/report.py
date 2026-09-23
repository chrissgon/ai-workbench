"""Totals for statement lines."""
from money import parse_amount


def total(lines: list[str]) -> float:
    return round(sum(parse_amount(line) for line in lines), 2)
