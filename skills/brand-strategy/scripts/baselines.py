#!/usr/bin/env python3
"""Measure the public starting point of a brand's products before any target is set.

Usage:
  python3 baselines.py [--npm <package>]... [--github <owner/repo>]... [--today YYYY-MM-DD]

For each npm package: downloads in the last week and the last month (api.npmjs.org). For each
GitHub repository: stars, forks, watchers and creation date (api.github.com, unauthenticated, 60
requests per hour). Reads only; sends nothing but the package and repository names. Prints JSON to
stdout, one entry per item with its value, the period, the URL it came from and the access date,
so every number in the strategy can cite it. An item that fails is reported with its error and
does not stop the others. Exit 0 when every item was measured, 1 when any failed, 2 on bad
arguments. Social-network metrics (followers, impressions) are not public APIs for a member
account: ask the user for them.
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

NPM_NAME = re.compile(r"^(@[a-z0-9][\w.-]*/)?[a-z0-9][\w.-]*$")
REPO_NAME = re.compile(r"^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$")
TIMEOUT = 20


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def get_json(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "brand-strategy-baselines"})
    with OPENER.open(req, timeout=TIMEOUT) as resp:
        return json.load(resp)


def npm(package, today):
    out = []
    quoted = urllib.parse.quote(package, safe="@/")
    for period in ("last-week", "last-month"):
        url = f"https://api.npmjs.org/downloads/point/{period}/{quoted}"
        data = get_json(url)
        out.append({"item": package, "metric": f"npm downloads ({period})", "value": data["downloads"],
                    "period": f"{data['start']} to {data['end']}", "source": url, "accessed": today})
    return out


def github(repo, today):
    url = f"https://api.github.com/repos/{repo}"
    data = get_json(url)
    return [{"item": repo, "metric": m, "value": data[k], "period": "at access", "source": url, "accessed": today}
            for m, k in (("GitHub stars", "stargazers_count"), ("GitHub forks", "forks_count"),
                         ("GitHub watchers", "subscribers_count"), ("created", "created_at"))]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--npm", action="append", default=[])
    ap.add_argument("--github", action="append", default=[])
    ap.add_argument("--today", help="YYYY-MM-DD written as the access date; default today")
    args = ap.parse_args()
    if not args.npm and not args.github:
        print("baselines.py: give at least one --npm or --github", file=sys.stderr)
        sys.exit(2)
    for name in args.npm:
        if not NPM_NAME.match(name):
            print(f"baselines.py: not an npm package name: {name!r}", file=sys.stderr)
            sys.exit(2)
    for name in args.github:
        if not REPO_NAME.match(name):
            print(f"baselines.py: not an owner/repo name: {name!r}", file=sys.stderr)
            sys.exit(2)
    try:
        today = (date.fromisoformat(args.today) if args.today else date.today()).isoformat()
    except ValueError:
        print("baselines.py: --today must be YYYY-MM-DD", file=sys.stderr)
        sys.exit(2)
    rows, errors = [], []
    for kind, names, fn in (("npm", args.npm, npm), ("github", args.github, github)):
        for name in names:
            try:
                rows.extend(fn(name, today))
            except (urllib.error.URLError, KeyError, ValueError, TimeoutError) as exc:
                errors.append({"item": name, "kind": kind, "error": str(exc)})
    print(json.dumps({"measurements": rows, "errors": errors}, indent=2))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
