#!/usr/bin/env python3
"""Check where a name or handle is registered: domains, code hosts, package registries, video.

Usage:
  python3 handle_check.py --name <handle> [--tld dev --tld com --tld com.br ...]
                          [--platform github --platform npm --platform devto --platform youtube]
                          [--responses <file>] [--today YYYY-MM-DD]

Defaults: --tld dev com io com.br, every platform of the PLATFORMS table. --platform names a place
where a handle can be looked up without signing in (a code host, a package registry, a video site);
it is not a social platform's name. Prints JSON, one row per check:
  status  "registered"  the name exists there (a domain has an RDAP record; a profile or scope exists)
          "not_found"   the service answered that it does not exist (for a domain: probably free,
                        to be confirmed at a registrar before buying)
          "unknown"     no reliable answer (network error, blocked, or the RDAP endpoint did not
                        return a record for a known control domain of the same TLD)
  source  the URL queried; checked_at, the date.
Also "all_unknown": true when every check is "unknown", which is what a run without the network
gives. The script cannot tell who owns what exists: ownership is the user's answer. Networks that
need a login to look a name up (the BY_HAND list: linkedin, instagram, x, threads, tiktok) are listed
under "check_by_hand", to be asked of the person.

--responses <file> reads the answers from a file instead of the network, and sends no request: a
JSON object whose keys are the URLs the script would query, each with {"status": <HTTP status or
null for no answer>}. A URL the file does not hold is read as no answer. It replays answers recorded
earlier (a test, a run without the network).

Reads only; sends nothing but the name. Exit 0, or 2 on a bad argument or an unreadable --responses file.
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,38}$")
TLD = re.compile(r"^[a-z]{2,24}(\.[a-z]{2,3})?$")
TIMEOUT = 20
UA = {"User-Agent": "brand-name-handle-check", "Accept": "application/json"}
# The networks to check, inside this skill (design rule 3 of AGENTS.md): a row added here is a change of
# this skill. PLATFORMS are looked up without signing in, by the URL template; BY_HAND need a login and are
# asked of the person.
PLATFORMS = {
    "github": "https://api.github.com/users/{name}",
    # The search API's "scope:" filter missed a scope that has packages (seen on a real scope);
    # the user/org package list answers 404 "Scope not found" when the scope does not exist.
    "npm": "https://registry.npmjs.org/-/user/{name}/package",
    "devto": "https://dev.to/api/users/by_username?url={name}",
    "youtube": "https://www.youtube.com/@{name}",
}
BY_HAND = ["linkedin", "instagram", "x", "threads", "tiktok"]
RESPONSES = None  # {url: status or None} when --responses is given; then no request is sent


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # rdap.org answers with a redirect to the registry's RDAP server; follow https only.
        if newurl.startswith("https://"):
            return urllib.request.Request(newurl, headers=UA)
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def http_status(url):
    if RESPONSES is not None:
        return RESPONSES.get(url), b""
    try:
        with OPENER.open(urllib.request.Request(url, headers=UA), timeout=TIMEOUT) as resp:
            return resp.status, resp.read(200_000)
    except urllib.error.HTTPError as exc:
        return exc.code, b""
    except (urllib.error.URLError, TimeoutError):
        return None, b""


def load_responses(path):
    """{url: status or None} from a --responses file; exits 2 when the file cannot be used."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        print(f"handle_check.py: cannot read --responses {path}: {exc}", file=sys.stderr)
        sys.exit(2)
    if not isinstance(data, dict):
        print("handle_check.py: --responses must hold a JSON object of URL -> {\"status\": ...}", file=sys.stderr)
        sys.exit(2)
    out = {}
    for url, answer in data.items():
        status = answer.get("status") if isinstance(answer, dict) else None
        if not (isinstance(answer, dict) and (status is None or isinstance(status, int))):
            print(f"handle_check.py: --responses: {url}: needs {{\"status\": <int or null>}}", file=sys.stderr)
            sys.exit(2)
        out[url] = status
    return out


def rdap_url(domain):
    if domain.endswith(".br"):
        return f"https://rdap.registro.br/domain/{domain}"
    return f"https://rdap.org/domain/{domain}"


def check_domain(name, tld):
    domain = f"{name}.{tld}"
    url = rdap_url(domain)
    control, _ = http_status(rdap_url(f"google.{tld}"))
    code, _ = http_status(url)
    if code == 200:
        status = "registered"
    elif code == 404 and control == 200:
        status = "not_found"
    else:
        status = "unknown"
    return {"check": f"domain {domain}", "status": status, "source": url}


def check_platform(name, platform):
    if platform not in PLATFORMS:
        raise ValueError(platform)
    url = PLATFORMS[platform].format(name=urllib.parse.quote(name))
    code, _ = http_status(url)
    status = {200: "registered", 404: "not_found"}.get(code, "unknown")
    return {"check": f"{platform} {name}", "status": status, "source": url}


def main():
    global RESPONSES
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True)
    ap.add_argument("--tld", action="append")
    ap.add_argument("--platform", action="append", choices=sorted(PLATFORMS))
    ap.add_argument("--responses", help="a JSON file of recorded answers; no request is sent")
    ap.add_argument("--today")
    args = ap.parse_args()
    name = args.name.lower()
    if not NAME.match(name):
        print("handle_check.py: --name must be 1-39 lowercase letters, digits or hyphens", file=sys.stderr)
        sys.exit(2)
    tlds = args.tld or ["dev", "com", "io", "com.br"]
    if not all(TLD.match(t) for t in tlds):
        print("handle_check.py: --tld must look like 'dev' or 'com.br'", file=sys.stderr)
        sys.exit(2)
    try:
        today = (date.fromisoformat(args.today) if args.today else date.today()).isoformat()
    except ValueError:
        print("handle_check.py: --today must be YYYY-MM-DD", file=sys.stderr)
        sys.exit(2)
    if args.responses:
        RESPONSES = load_responses(args.responses)
    rows = [check_domain(name, t) for t in tlds]
    rows += [check_platform(name, p) for p in (args.platform or list(PLATFORMS))]
    for r in rows:
        r["checked_at"] = today
    print(json.dumps({"name": name, "checks": rows, "all_unknown": all(r["status"] == "unknown" for r in rows),
                      "check_by_hand": BY_HAND}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
