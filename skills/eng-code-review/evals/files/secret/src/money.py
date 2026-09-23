"""Money parsing helpers shared by every report."""


def parse_amount(text: str) -> float:
    """Parse an accounting amount; "(12.50)" means -12.50."""
    raw = text.strip()
    negative = raw.startswith("(") and raw.endswith(")")
    raw = raw.strip("()").replace(",", "")
    value = float(raw)
    return -value if negative else value
