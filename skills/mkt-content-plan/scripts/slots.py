#!/usr/bin/env python3
"""Compute the publication slots of a content calendar: dates, times with offset, pillar and language.

Usage:
  python3 slots.py --start 2026-10-05 --weeks 1 --days mon,wed,fri --time 09:30 \
      --tz America/Sao_Paulo --pillars "Build to serve|AI in public|Tech in conversation" \
      --rotation "PT,EN,PT;EN,PT,EN" [--after-calendar docs/marketing/calendar.md | --first-week A] [--today 2026-09-29]

The n-th post of a week gets the n-th pillar and the n-th language of that week's rotation.
Rotation weeks are labelled A, B, C... in order and alternate across weeks; --first-week picks
where the rotation starts; --after-calendar reads the last "(rotation X)" label of an existing calendar
and starts at the label after it, so a new calendar continues the previous one.
Weeks run Monday to Sunday; --start may be any day, and slots before it in that week are skipped.

Prints JSON on stdout: {"slots": [{"n", "week", "rotation", "date", "weekday", "at", "pillar", "language"}],
"timezone", "warnings"}. Exit 2 on a usage error (a start in the past, more days than pillars, etc.).
Standard library only; no network.
"""
import argparse
import json
import sys
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(2)


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", required=True, help="first day to consider, YYYY-MM-DD")
    p.add_argument("--weeks", type=int, default=1, help="number of weeks (default 1)")
    p.add_argument("--days", required=True, help="weekdays, comma separated: mon,wed,fri")
    p.add_argument("--time", required=True, help="local time HH:MM, one for all days, or one per day: 09:30,12:00,09:30")
    p.add_argument("--tz", required=True, help="IANA timezone, e.g. America/Sao_Paulo")
    p.add_argument("--pillars", required=True, help="pillars in order, separated by |")
    p.add_argument("--rotation", required=True, help="languages per week, weeks separated by ; posts by ,")
    p.add_argument("--first-week", help="rotation label of the first week (default A)")
    p.add_argument("--after-calendar", help="previous calendar: start after its last rotation label")
    p.add_argument("--today", help="today's date, YYYY-MM-DD (default: the system date)")
    return p.parse_args(argv)


def main(argv=None) -> int:
    a = parse_args(argv)
    try:
        start = date.fromisoformat(a.start)
        today = date.fromisoformat(a.today) if a.today else date.today()
    except ValueError as e:
        fail(f"bad date: {e}")
    if start <= today:
        fail(f"--start {start} is not after today ({today}); a calendar starts tomorrow at the earliest")
    if not 1 <= a.weeks <= 12:
        fail("--weeks must be between 1 and 12")
    try:
        tz = ZoneInfo(a.tz)
    except (ZoneInfoNotFoundError, ValueError):
        fail(f"unknown timezone {a.tz!r}")
    days = [d.strip().lower() for d in a.days.split(",") if d.strip()]
    if not days or any(d not in DAYS for d in days) or len(set(days)) != len(days):
        fail(f"--days must be distinct values among {','.join(DAYS)}")
    days.sort(key=DAYS.index)
    times = [t.strip() for t in a.time.split(",")]
    if len(times) == 1:
        times = times * len(days)
    if len(times) != len(days):
        fail("--time takes one time, or one per day in --days")
    try:
        clock = [time.fromisoformat(t) for t in times]
    except ValueError as e:
        fail(f"bad time: {e}")
    pillars = [p.strip() for p in a.pillars.split("|") if p.strip()]
    rotation = [[x.strip().upper() for x in w.split(",")] for w in a.rotation.split(";") if w.strip()]
    if len(days) > len(pillars):
        fail(f"{len(days)} days but only {len(pillars)} pillars; one post per pillar per week")
    for i, w in enumerate(rotation):
        if len(w) != len(days):
            fail(f"rotation week {chr(65 + i)} has {len(w)} languages for {len(days)} posts")
    labels = [chr(65 + i) for i in range(len(rotation))]
    if a.after_calendar and a.first_week:
        fail("use --after-calendar or --first-week, not both")
    first = (a.first_week or "A").strip().upper()
    if a.after_calendar:
        import re
        try:
            found = re.findall(r"\(rotation ([A-Z])\)", open(a.after_calendar, encoding="utf-8").read())
        except OSError as e:
            fail(f"--after-calendar: {e}")
        if found:
            if found[-1] not in labels:
                fail(f"previous calendar ends with rotation {found[-1]}, not in {','.join(labels)}")
            first = labels[(labels.index(found[-1]) + 1) % len(labels)]
    if first not in labels:
        fail(f"--first-week must be one of {','.join(labels)}")
    warnings = []
    if len(days) < len(pillars):
        warnings.append(f"{len(pillars) - len(days)} pillar(s) get no post each week: {', '.join(pillars[len(days):])}")

    monday = start - timedelta(days=start.weekday())
    slots, n = [], 0
    for w in range(a.weeks):
        label = labels[(labels.index(first) + w) % len(labels)]
        langs = rotation[labels.index(label)]
        for i, d in enumerate(days):
            day = monday + timedelta(weeks=w, days=DAYS.index(d))
            if day < start:
                warnings.append(f"{day} ({d}) is before --start and was skipped")
                continue
            n += 1
            at = datetime.combine(day, clock[i], tzinfo=tz)
            slots.append({
                "n": n,
                "week": w + 1,
                "rotation": label,
                "date": day.isoformat(),
                "weekday": d,
                "at": at.isoformat(),
                "pillar": pillars[i],
                "language": langs[i],
            })
    json.dump({"slots": slots, "timezone": a.tz, "first_week": first, "warnings": warnings}, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
