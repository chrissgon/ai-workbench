"""Money parsing helpers shared by every report."""


def parse_amount(text: str) -> float:
    """Parse an accounting amount; "(12.50)" means -12.50."""
    raw = text.strip().strip("()").replace(",", "")
    negative = raw.startswith("(")
    value = float(raw)
    return -value if negative else value
