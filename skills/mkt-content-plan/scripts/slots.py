#!/usr/bin/env python3
"""Compute the publication slots of a content calendar: dates, times with offset, pillar and language.

Usage:
  python3 slots.py --start 2027-10-04 --weeks 1 --days mon,wed,fri --time 09:30 \
      --tz Europe/Lisbon --pillars "Guides|Case studies|Opinions" \
      --rotation "PT,EN,PT;EN,PT,EN" [--after-calendar docs/marketing/calendar.md | --first-week A] [--today 2027-09-28]

The n-th post of a week (in weekday order) gets the n-th pillar and the n-th language of that week's
rotation; a list in --time is matched to --days as given and sorted with them.
Rotation weeks are labelled A, B, C... in order and alternate across weeks; --first-week picks where the
rotation starts. --after-calendar reads an existing calendar: the last rotation label of its week headings
(a heading ending in "(<word> X)", in the artifact's language, for example "(rotation B)"), so that the new
weeks start at the label after it, and the highest number in the "#" column of its tables, so that row
numbers continue after it and are never reused; week numbers continue after its week headings.
A strategy with one language still passes a rotation: --rotation "EN,EN,EN".
Weeks run Monday to Sunday; --start may be any day, and slots before it in that week are skipped.

Prints JSON on stdout: {"slots": [{"n", "week", "rotation", "date", "weekday", "at", "pillar", "language"}],
"timezone", "first_week", "after_row", "warnings"}. "n" is the row number to copy into the calendar's "#"
column and "week" the number of the week heading; "after_row" is the highest row number found in
--after-calendar (0 without it).
Exit 2 on a usage error (a start in the past, more days than pillars, etc.), with the message on stderr.
Standard library only; no network.
"""
import argparse
import json
import re
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
    times = [t.strip() for t in a.time.split(",")]
    if len(times) == 1:
        times = times * len(days)
    if len(times) != len(days):
        fail("--time takes one time, or one per day in --days")
    try:
        clock = [time.fromisoformat(t) for t in times]
    except ValueError as e:
        fail(f"bad time: {e}")
    # Each time belongs to the day it was given with: sort the pairs, never the days alone.
    pairs = sorted(zip(days, clock), key=lambda pair: DAYS.index(pair[0]))
    days, clock = [d for d, _ in pairs], [c for _, c in pairs]
    pillars = [p.strip() for p in a.pillars.split("|") if p.strip()]
    rotation = [[x.strip().upper() for x in w.split(",")] for w in a.rotation.split(";") if w.strip()]
    if not rotation:
        fail('--rotation needs at least one week of languages, for example "EN,PT,EN"; '
             'a strategy with one language passes "EN,EN,EN"')
    if len(days) > len(pillars):
        fail(f"{len(days)} days but only {len(pillars)} pillars: this script plans one post per pillar per week, "
             "so the strategy's rhythm has more posts than pillars; ask the user which pillar takes the extra posts")
    for i, w in enumerate(rotation):
        if len(w) != len(days):
            fail(f"rotation week {chr(65 + i)} has {len(w)} languages for {len(days)} posts")
    labels = [chr(65 + i) for i in range(len(rotation))]
    if a.after_calendar and a.first_week:
        fail("use --after-calendar or --first-week, not both")
    first = (a.first_week or "A").strip().upper()
    after_row = after_week = 0
    if a.after_calendar:
        try:
            with open(a.after_calendar, encoding="utf-8") as fh:
                previous = fh.read()
        except OSError as e:
            fail(f"--after-calendar: {e}")
        # The week heading carries the label in the artifact's language: "(rotation B)", "(rotação B)".  # validate: allow english-only -- a Portuguese week heading, the case this parser supports
        found = re.findall(r"^#+ .*\(\w+ ([A-Z])\)\s*$", previous, re.M)
        rows = [int(r) for r in re.findall(r"^\|\s*(\d+)\s*\|", previous, re.M)]
        after_row = max(rows, default=0)
        after_week = len(found)
        if found:
            if found[-1] not in labels:
                fail(f"previous calendar ends with rotation {found[-1]}, not in {','.join(labels)}")
            first = labels[(labels.index(found[-1]) + 1) % len(labels)]
    if first not in labels:
        fail(f"--first-week must be one of {','.join(labels)}, the weeks of --rotation")
    warnings = []
    if len(days) < len(pillars):
        warnings.append(f"{len(pillars) - len(days)} pillar(s) get no post each week: {', '.join(pillars[len(days):])}")

    monday = start - timedelta(days=start.weekday())
    slots, n = [], after_row
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
                "week": after_week + w + 1,
                "rotation": label,
                "date": day.isoformat(),
                "weekday": d,
                "at": at.isoformat(),
                "pillar": pillars[i],
                "language": langs[i],
            })
    json.dump({"slots": slots, "timezone": a.tz, "first_week": first, "after_row": after_row,
               "warnings": warnings}, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
