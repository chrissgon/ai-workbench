#!/usr/bin/env python3
"""Measure the public starting point of a brand's products before any target is set.

Usage:
  python3 baselines.py [--npm <package>]... [--github <owner/repo>]... [--responses <file>] [--today YYYY-MM-DD]

For each npm package: downloads in the last week and the last month (api.npmjs.org). For each
GitHub repository: stars, forks, watchers and creation date (api.github.com, unauthenticated, 60
requests per hour). Reads only; sends nothing but the package and repository names. Prints JSON to
stdout: {"measurements": [...], "errors": [...]}. A measurement has its value, the period, the URL
it came from and the access date, so every number in the strategy can cite it. An item that is not
measured is an entry of "errors" and does not stop the others; its "status" tells two facts apart:
  "not_found"     the service answered 404: the package or repository does not exist
  "not_measured"  no usable answer (network blocked or unreachable, a timeout, another HTTP status,
                  an answer that is not the expected JSON): nothing is known about the item
--responses <file> reads the answers from a file instead of the network, and sends no request: a
JSON object whose keys are the URLs the script would query, each with {"status": <HTTP status or
null for no answer>, "body": <the JSON the service returned, for a 200>}. A URL the file does not
hold is read as no answer. It replays answers recorded earlier (a test, a run without the network).
Exit 0 when every item was measured, 1 when any was not, 2 on bad arguments or an unreadable
--responses file. Social-network metrics (followers, impressions) are not read here: the platform's
reference says what can be read from outside, and the rest is asked of the user.
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
RESPONSES = None  # {url: {"status": int or None, "body": ...}} when --responses is given; then no request


class NotMeasured(Exception):
    """No usable answer for an item."""


class NotFound(Exception):
    """The service answered 404 for an item."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def get_json(url):
    if RESPONSES is not None:
        answer = RESPONSES.get(url) or {}
        status = answer.get("status")
        if status == 404:
            raise NotFound(f"HTTP 404 from {url}")
        if status != 200:
            raise NotMeasured(f"no answer recorded for {url}" if status is None else f"HTTP {status} from {url}")
        return answer.get("body")
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "brand-strategy-baselines"})
    try:
        with OPENER.open(req, timeout=TIMEOUT) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise NotFound(f"HTTP 404 from {url}") from exc
        raise NotMeasured(f"HTTP {exc.code} from {url}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise NotMeasured(f"no answer from {url}: {exc}") from exc
    except ValueError as exc:
        raise NotMeasured(f"the answer from {url} is not JSON") from exc


def field(data, key, url):
    if not isinstance(data, dict) or key not in data:
        raise NotMeasured(f"the answer from {url} has no {key!r}")
    return data[key]


def npm(package, today):
    out = []
    quoted = urllib.parse.quote(package, safe="@/")
    for period in ("last-week", "last-month"):
        url = f"https://api.npmjs.org/downloads/point/{period}/{quoted}"
        data = get_json(url)
        out.append({"item": package, "metric": f"npm downloads ({period})", "value": field(data, "downloads", url),
                    "period": f"{field(data, 'start', url)} to {field(data, 'end', url)}", "source": url,
                    "accessed": today})
    return out


def github(repo, today):
    url = f"https://api.github.com/repos/{repo}"
    data = get_json(url)
    return [{"item": repo, "metric": m, "value": field(data, k, url), "period": "at access", "source": url,
             "accessed": today}
            for m, k in (("GitHub stars", "stargazers_count"), ("GitHub forks", "forks_count"),
                         ("GitHub watchers", "subscribers_count"), ("created", "created_at"))]


def load_responses(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        print(f"baselines.py: cannot read --responses {path}: {exc}", file=sys.stderr)
        sys.exit(2)
    ok = isinstance(data, dict) and all(
        isinstance(a, dict) and (a.get("status") is None or isinstance(a.get("status"), int)) for a in data.values())
    if not ok:
        print('baselines.py: --responses must hold a JSON object of URL -> {"status": <int or null>, "body": ...}',
              file=sys.stderr)
        sys.exit(2)
    return data


def main():
    global RESPONSES
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--npm", action="append", default=[])
    ap.add_argument("--github", action="append", default=[])
    ap.add_argument("--responses", help="a JSON file of recorded answers; no request is sent")
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
    if args.responses:
        RESPONSES = load_responses(args.responses)
    rows, errors = [], []
    for kind, names, fn in (("npm", args.npm, npm), ("github", args.github, github)):
        for name in names:
            try:
                rows.extend(fn(name, today))
            except NotFound as exc:
                errors.append({"item": name, "kind": kind, "status": "not_found", "error": str(exc)})
            except NotMeasured as exc:
                errors.append({"item": name, "kind": kind, "status": "not_measured", "error": str(exc)})
    print(json.dumps({"measurements": rows, "errors": errors}, indent=2))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
