#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["keyring>=25"]
# ///
"""One-time OAuth 2.0 authorization for publisher providers.

LinkedIn (--provider linkedin), sources accessed 2026-09-26:
- Authorization code flow (authorization URL, token exchange, 60-day tokens,
  programmatic refresh tokens only for a limited set of partners):
  https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow
- Sign In with LinkedIn using OpenID Connect (scopes openid, profile):
  https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/sign-in-with-linkedin-v2
- Share on LinkedIn (scope w_member_social):
  https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
import secrets
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

KEYRING_SERVICE = "ai-workbench"
LINKEDIN_KEYRING_USERNAME = "publisher-linkedin"
LINKEDIN_AUTHORIZE_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_SCOPES = "openid profile w_member_social"
CALLBACK_HOST, CALLBACK_PORT, CALLBACK_PATH = "localhost", 8765, "/callback"
REDIRECT_URI = f"http://{CALLBACK_HOST}:{CALLBACK_PORT}{CALLBACK_PATH}"
CALLBACK_TIMEOUT_SECONDS = 300
EXIT_OK, EXIT_SERVICE, EXIT_USAGE, EXIT_NOT_CONFIGURED = 0, 1, 2, 3

HELP_EPILOG = f"""\
LinkedIn developer app setup (once):
  1. Go to https://www.linkedin.com/developers/apps and create an app. LinkedIn
     requires the app to be linked to a LinkedIn Page (create or pick a Page you
     administer; posts are still published as you, the member).
  2. In the app's Products tab, add "Share on LinkedIn" (grants w_member_social)
     and "Sign In with LinkedIn using OpenID Connect" (grants openid, profile).
  3. In the Auth tab, add the authorized redirect URL:
         {REDIRECT_URI}
  4. Export the client ID and secret in your shell, never in a file:
         export LINKEDIN_CLIENT_ID=...
         export LINKEDIN_CLIENT_SECRET=...
  5. Run:
         uv run providers/publisher/auth.py --provider linkedin
     Approve in the browser. The access token and its expiry are stored in the OS
     secret store (service "{KEYRING_SERVICE}", username "{LINKEDIN_KEYRING_USERNAME}"),
     never on disk in plain text.

environment variables:
  LINKEDIN_CLIENT_ID       required for the authorization.
  LINKEDIN_CLIENT_SECRET   required for the authorization.

LinkedIn access tokens last 60 days. Programmatic refresh tokens exist only for
approved partners, so rerun this command before the token expires; while you are
still signed in to LinkedIn the consent screen is skipped.

exit codes: 0 success, 1 provider or service error, 2 usage error, 3 not configured.

examples:
  uv run providers/publisher/auth.py --provider linkedin
  uv run providers/publisher/auth.py --provider linkedin --no-browser
  uv run providers/publisher/auth.py --provider linkedin --check
"""


class AuthError(Exception):
    def __init__(self, message: str, code: int = EXIT_SERVICE):
        super().__init__(message)
        self.code = code


def log(message: str) -> None:
    print(message, file=sys.stderr)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def keyring_module():
    try:
        import keyring
    except ImportError:
        raise AuthError("the keyring package is missing; run with: uv run providers/publisher/auth.py",
                        EXIT_NOT_CONFIGURED)
    return keyring


# --- LinkedIn ------------------------------------------------------------------


def linkedin_check() -> int:
    keyring = keyring_module()
    try:
        stored = keyring.get_password(KEYRING_SERVICE, LINKEDIN_KEYRING_USERNAME)
    except Exception as exc:
        raise AuthError(f"cannot read the OS secret store: {type(exc).__name__}")
    if not stored:
        print(json.dumps({"provider": "linkedin", "stored": False}, indent=2))
        log("not ready: no LinkedIn token stored; run auth.py --provider linkedin")
        return EXIT_SERVICE
    try:
        data = json.loads(stored)
    except ValueError:
        raise AuthError("the stored LinkedIn credential is unreadable; rerun auth.py --provider linkedin")
    expires_at = data.get("expires_at")
    days = None
    expired = False
    if expires_at:
        delta = datetime.fromisoformat(expires_at.replace("Z", "+00:00")) - now_utc()
        days = int(delta.total_seconds() // 86400)
        expired = delta.total_seconds() <= 0
    out = {
        "provider": "linkedin",
        "stored": True,
        "expires_at": expires_at,
        "expires_in_days": days,
        "expired": expired,
        "scope": data.get("scope"),
        "has_refresh_token": bool(data.get("refresh_token")),
    }
    print(json.dumps(out, indent=2))
    if expired:
        log("not ready: the stored LinkedIn token has expired; rerun auth.py --provider linkedin")
        return EXIT_SERVICE
    if days is not None and days < 7:
        log(f"warning: the LinkedIn token expires in {days} days; rerun auth.py --provider linkedin")
    return EXIT_OK


def wait_for_code(expected_state: str) -> str:
    """Serve one callback on localhost:8765 and return the authorization code."""
    outcome: dict = {}
    done = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (http.server naming)
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != CALLBACK_PATH:
                self.send_response(404)
                self.end_headers()
                return
            query = urllib.parse.parse_qs(parsed.query)
            state = query.get("state", [""])[0]
            if not hmac.compare_digest(state, expected_state):
                outcome["error"] = "the state parameter does not match; possible CSRF, nothing stored"
                status, text = 401, "State mismatch. Nothing was stored. You can close this tab."
            elif "error" in query:
                outcome["error"] = f"LinkedIn returned {query['error'][0]}: " + query.get("error_description", [""])[0]
                status, text = 400, "Authorization was not granted. You can close this tab."
            elif not query.get("code"):
                outcome["error"] = "the callback carried no code"
                status, text = 400, "No authorization code received. You can close this tab."
            else:
                outcome["code"] = query["code"][0]
                status, text = 200, "Authorization received. You can close this tab and return to the terminal."
            body = f"<!doctype html><title>ai-workbench</title><p>{text}</p>".encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            done.set()

        def log_message(self, *args):  # silence request logs: the URL carries the code
            return

    try:
        server = HTTPServer((CALLBACK_HOST, CALLBACK_PORT), Handler)
    except OSError as exc:
        raise AuthError(f"cannot listen on {REDIRECT_URI}: {exc.strerror}")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        if not done.wait(CALLBACK_TIMEOUT_SECONDS):
            raise AuthError(f"no callback within {CALLBACK_TIMEOUT_SECONDS} seconds")
    finally:
        server.shutdown()
        server.server_close()
    if "error" in outcome:
        raise AuthError(outcome["error"])
    return outcome["code"]


def exchange_code(code: str, client_id: str, client_secret: str) -> dict:
    form = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
    }).encode()
    request = urllib.request.Request(
        LINKEDIN_TOKEN_URL, data=form, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            err = json.loads(exc.read())
            detail = f": {err.get('error', '')} {err.get('error_description', '')}".rstrip()
        except (ValueError, AttributeError):
            pass
        raise AuthError(f"token exchange failed with {exc.code}{detail}")
    except urllib.error.URLError as exc:
        raise AuthError(f"cannot reach LinkedIn: {exc.reason}")
    if not data.get("access_token") or not data.get("expires_in"):
        raise AuthError("the token response has no access_token or expires_in")
    return data


def linkedin_authorize(open_browser: bool) -> int:
    client_id = os.environ.get("LINKEDIN_CLIENT_ID")
    client_secret = os.environ.get("LINKEDIN_CLIENT_SECRET")
    missing = [n for n, v in (("LINKEDIN_CLIENT_ID", client_id), ("LINKEDIN_CLIENT_SECRET", client_secret)) if not v]
    if missing:
        raise AuthError(f"set {' and '.join(missing)} in the shell environment first (see --help)",
                        EXIT_NOT_CONFIGURED)
    keyring = keyring_module()  # fail before the browser step if the store is unavailable

    state = secrets.token_urlsafe(32)
    url = LINKEDIN_AUTHORIZE_URL + "?" + urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "state": state,
            "scope": LINKEDIN_SCOPES,
        },
        quote_via=urllib.parse.quote,  # spaces as %20, as in LinkedIn's example
    )
    log("Open this URL to authorize (it contains no secret):")
    log(url)
    if open_browser:
        webbrowser.open(url)
    log(f"Waiting for the callback on {REDIRECT_URI} ...")
    code = wait_for_code(state)

    token = exchange_code(code, client_id, client_secret)
    obtained = now_utc()
    record = {
        "access_token": token["access_token"],
        "expires_at": iso(obtained + timedelta(seconds=int(token["expires_in"]))),
        "obtained_at": iso(obtained),
        "scope": token.get("scope"),
    }
    if token.get("refresh_token"):  # only for partners with programmatic refresh enabled
        record["refresh_token"] = token["refresh_token"]
        if token.get("refresh_token_expires_in"):
            record["refresh_token_expires_at"] = iso(obtained + timedelta(seconds=int(token["refresh_token_expires_in"])))
    try:
        keyring.set_password(KEYRING_SERVICE, LINKEDIN_KEYRING_USERNAME, json.dumps(record))
    except Exception as exc:
        raise AuthError(f"cannot write to the OS secret store: {type(exc).__name__}")
    print(json.dumps({
        "provider": "linkedin",
        "stored": True,
        "secret_store": {"service": KEYRING_SERVICE, "username": LINKEDIN_KEYRING_USERNAME},
        "expires_at": record["expires_at"],
        "scope": record["scope"],
        "has_refresh_token": "refresh_token" in record,
    }, indent=2))
    if "refresh_token" not in record:
        log(f"No refresh token: rerun this command before {record['expires_at']}.")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="auth.py",
        description="Run the OAuth 2.0 authorization for a publisher provider once and store the "
        "token in the OS secret store.",
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--provider", required=True, choices=["linkedin"], help="the provider to authorize")
    parser.add_argument("--check", action="store_true", help="report whether a token is stored and when it expires")
    parser.add_argument("--no-browser", action="store_true", help="print the authorization URL without opening a browser")
    args = parser.parse_args(argv)
    try:
        if args.check:
            return linkedin_check()
        return linkedin_authorize(open_browser=not args.no_browser)
    except AuthError as exc:
        log(f"error: {exc}")
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
