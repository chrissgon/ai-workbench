#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["keyring==25.7.0"]
# ///
"""Publisher provider for LinkedIn: publish a post as the authenticated member.

Sources (official LinkedIn documentation, all accessed 2026-09-26):
- Posts API (request body, 201 + x-restli-id response, w_member_social):
  https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api?view=li-lms-2026-09
- Images API (initializeUpload request and response, value.uploadUrl, value.image):
  https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/images-api?view=li-lms-2026-09
- Image byte upload (PUT to uploadUrl with the OAuth token in Authorization), linked from the Images API page:
  https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/vector-asset-api?view=li-lms-2026-09#upload-the-image
- little Text Format (reserved characters, backslash escaping) used by the commentary field:
  https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/little-text-format?view=li-lms-2026-09
- API versioning (latest version header 202609, versions supported at least one year):
  https://learn.microsoft.com/en-us/linkedin/marketing/versioning
- Sign In with LinkedIn using OpenID Connect (GET /v2/userinfo returns sub, name):
  https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/sign-in-with-linkedin-v2
- Share on LinkedIn product (grants w_member_social; author is urn:li:person:{sub}):
  https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin
- Authorization code flow (60-day access tokens; programmatic refresh only for a limited set of partners):
  https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

LINKEDIN_VERSION = "202609"
RESTLI_PROTOCOL_VERSION = "2.0.0"
DEFAULT_API_BASE = "https://api.linkedin.com"
KEYRING_SERVICE = "ai-workbench"
KEYRING_USERNAME = "publisher-linkedin"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}
EXPIRY_WARNING_DAYS = 7
IMAGE_URN_PLACEHOLDER = "<image URN returned by initializeUpload>"
UPLOAD_URL_PLACEHOLDER = "<uploadUrl returned by initializeUpload>"
AUTHOR_PLACEHOLDER = "urn:li:person:<sub from /v2/userinfo; no token available>"

# Reserved characters of the little text format. Backslash comes first so that the
# escapes added for the other characters are not escaped twice.
LITTLE_RESERVED = "\\|{}@[]()<>#*_~"

EXIT_OK, EXIT_SERVICE, EXIT_USAGE, EXIT_NOT_CONFIGURED = 0, 1, 2, 3

HELP_EPILOG = f"""\
verbs:
  publish   Publish one post as the authenticated member. Needs --confirmed
            (or --dry-run). Refuses --at in the future: scheduling belongs to
            the scheduler class, not to this provider.

credentials (never from files or flags):
  The access token is read from the OS secret store (service "{KEYRING_SERVICE}",
  username "{KEYRING_USERNAME}"), written there by:
      uv run providers/publisher/auth.py --provider linkedin
  LINKEDIN_ACCESS_TOKEN        optional; an access token taken from the
                               environment instead of the secret store.
  LINKEDIN_TOKEN_EXPIRES_AT    optional; ISO-8601 expiry of LINKEDIN_ACCESS_TOKEN.

other environment variables:
  PUBLISHER_LINKEDIN_LEDGER    path of the idempotency ledger (JSON). Default:
                               $XDG_CACHE_HOME/ai-workbench/publisher-linkedin.json,
                               or ~/.cache/ai-workbench/publisher-linkedin.json.
  LINKEDIN_API_BASE            tests only. Replaces {DEFAULT_API_BASE} with a
                               loopback URL (http://127.0.0.1:<port>). Any other
                               host is refused. When set, the secret store is not
                               read; the token must come from LINKEDIN_ACCESS_TOKEN.

output:
  JSON on stdout: post_urn, post_url, token_expires_at, token_expires_in_days.
  Diagnostics on stderr. Tokens are never printed.

exit codes: 0 success, 1 provider or service error, 2 usage error, 3 not configured.

LinkedIn API version pinned: {LINKEDIN_VERSION}. Access tokens last 60 days and
there is no refresh token for self-serve apps: rerun auth.py before expiry.

examples:
  uv run providers/publisher/linkedin.py --check
  uv run providers/publisher/linkedin.py publish --platform linkedin \\
      --text-file post.txt --media cover.png --idempotency-key launch-2026-10 --dry-run
  uv run providers/publisher/linkedin.py publish --platform linkedin \\
      --text-file post.txt --idempotency-key launch-2026-10 --confirmed
"""


class ProviderError(Exception):
    """An error with an exit code and a one-line message for stderr."""

    def __init__(self, message: str, code: int = EXIT_SERVICE):
        super().__init__(message)
        self.code = code


def log(message: str) -> None:
    print(message, file=sys.stderr)


def escape_little_text(text: str) -> str:
    """Escape every reserved character of the little text format with a backslash."""
    return "".join("\\" + ch if ch in LITTLE_RESERVED else ch for ch in text)


def parse_iso(value: str) -> datetime:
    """Parse ISO-8601; a trailing Z means UTC; a value without offset is local time."""
    raw = value.strip()
    if raw.endswith(("Z", "z")):
        raw = raw[:-1] + "+00:00"
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


# --- configuration -----------------------------------------------------------


def api_base() -> tuple[str, bool]:
    """Return (base URL, test mode). Test mode accepts only loopback hosts."""
    override = os.environ.get("LINKEDIN_API_BASE")
    if not override:
        return DEFAULT_API_BASE, False
    parsed = urllib.parse.urlparse(override)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
        raise ProviderError(
            "LINKEDIN_API_BASE is for tests only and must be a loopback URL such as http://127.0.0.1:8080",
            EXIT_USAGE,
        )
    return override.rstrip("/"), True


def load_token(test_mode: bool) -> dict:
    """Return {"access_token": str, "expires_at": str|None}. Raise EXIT_NOT_CONFIGURED if absent or expired."""
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    expires_at = os.environ.get("LINKEDIN_TOKEN_EXPIRES_AT")
    if not token and not test_mode:
        try:
            import keyring  # imported lazily: only needed when the secret store is used
        except ImportError:
            raise ProviderError(
                "the keyring package is missing; run with: uv run providers/publisher/linkedin.py",
                EXIT_NOT_CONFIGURED,
            )
        try:
            stored = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
        except Exception as exc:  # the backend may be locked or unavailable
            raise ProviderError(f"cannot read the OS secret store: {type(exc).__name__}", EXIT_NOT_CONFIGURED)
        if stored:
            try:
                data = json.loads(stored)
                token, expires_at = data.get("access_token"), data.get("expires_at")
            except (ValueError, AttributeError):
                raise ProviderError(
                    "the stored LinkedIn credential is unreadable; rerun auth.py --provider linkedin",
                    EXIT_NOT_CONFIGURED,
                )
    if not token:
        raise ProviderError(
            "no LinkedIn access token; run: uv run providers/publisher/auth.py --provider linkedin",
            EXIT_NOT_CONFIGURED,
        )
    if expires_at:
        try:
            expiry = parse_iso(expires_at)
        except ValueError:
            raise ProviderError("the stored token expiry is not ISO-8601", EXIT_NOT_CONFIGURED)
        if expiry <= datetime.now(timezone.utc):
            raise ProviderError(
                f"the LinkedIn access token expired on {expiry.date().isoformat()}; "
                "run: uv run providers/publisher/auth.py --provider linkedin",
                EXIT_NOT_CONFIGURED,
            )
        expires_at = expiry.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return {"access_token": token, "expires_at": expires_at}


def days_until(expires_at: str | None) -> int | None:
    if not expires_at:
        return None
    return int((parse_iso(expires_at) - datetime.now(timezone.utc)).total_seconds() // 86400)


def ledger_path() -> Path:
    override = os.environ.get("PUBLISHER_LINKEDIN_LEDGER")
    if override:
        return Path(override).expanduser()
    cache = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(cache) / "ai-workbench" / "publisher-linkedin.json"


def ledger_read() -> dict:
    path = ledger_path()
    if not path.exists():
        return {"version": 1, "entries": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        raise ProviderError(f"the idempotency ledger at {path} is not valid JSON", EXIT_SERVICE)
    data.setdefault("entries", {})
    return data


def ledger_write(key: str, post_urn: str) -> None:
    path = ledger_path()
    data = ledger_read()
    data["entries"][key] = {
        "post_urn": post_urn,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".publisher-linkedin.", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


# --- HTTP --------------------------------------------------------------------


def rest_headers(token: str | None, json_body: bool = True) -> dict:
    headers = {
        "LinkedIn-Version": LINKEDIN_VERSION,
        "X-Restli-Protocol-Version": RESTLI_PROTOCOL_VERSION,
    }
    if json_body:
        headers["Content-Type"] = "application/json"
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def http(method: str, url: str, headers: dict, body: bytes | None = None) -> tuple[int, dict, bytes]:
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read()
    except urllib.error.HTTPError as exc:
        payload = exc.read()
        message = ""
        try:
            message = json.loads(payload).get("message", "")
        except (ValueError, AttributeError):
            pass
        path = urllib.parse.urlparse(url).path
        detail = f": {message}" if message else ""
        if exc.code == 401:
            raise ProviderError(
                f"LinkedIn rejected the token (401 on {method} {path}){detail}; "
                "run: uv run providers/publisher/auth.py --provider linkedin",
                EXIT_NOT_CONFIGURED,
            )
        raise ProviderError(f"LinkedIn returned {exc.code} on {method} {path}{detail}", EXIT_SERVICE)
    except urllib.error.URLError as exc:
        raise ProviderError(f"cannot reach LinkedIn: {exc.reason}", EXIT_SERVICE)


def userinfo(base: str, token: str) -> dict:
    # /v2/userinfo is an OpenID Connect endpoint: bearer token only, no version headers.
    status, _, body = http("GET", f"{base}/v2/userinfo", {"Authorization": f"Bearer {token}"})
    try:
        data = json.loads(body)
    except ValueError:
        raise ProviderError(f"unexpected /v2/userinfo response (status {status})")
    if not data.get("sub"):
        raise ProviderError("the /v2/userinfo response has no sub; the token lacks the openid scope")
    return data


def check_upload_url(url: str, base: str, test_mode: bool) -> None:
    """The upload receives the bearer token, so only send it to LinkedIn (or the test server)."""
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or ""
    if test_mode and host == urllib.parse.urlparse(base).hostname:
        return
    if parsed.scheme == "https" and (host == "linkedin.com" or host.endswith(".linkedin.com")):
        return
    raise ProviderError(f"refusing to upload to an unexpected host: {host or url}")


# --- publish -----------------------------------------------------------------


def post_body(author: str, commentary: str, image_urn: str | None) -> dict:
    body = {
        "author": author,
        "commentary": commentary,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    if image_urn:
        body["content"] = {"media": {"id": image_urn}}
    return body


def post_url(urn: str) -> str:
    return f"https://www.linkedin.com/feed/update/{urn}/"


def validate_publish_args(args) -> tuple[str, Path | None]:
    if args.platform != "linkedin":
        raise ProviderError(f"--platform {args.platform!r} is not served by this provider; use linkedin", EXIT_USAGE)
    text_path = Path(args.text_file)
    if not text_path.is_file():
        raise ProviderError(f"--text-file not found: {text_path}", EXIT_USAGE)
    text = text_path.read_text(encoding="utf-8").strip("\n")
    if not text.strip():
        raise ProviderError("--text-file is empty", EXIT_USAGE)
    media = args.media or []
    if len(media) > 1:
        raise ProviderError("this provider publishes at most one image per post; pass one --media", EXIT_USAGE)
    image = None
    if media:
        image = Path(media[0])
        if not image.is_file():
            raise ProviderError(f"--media not found: {image}", EXIT_USAGE)
        if image.suffix.lower() not in IMAGE_EXTENSIONS:
            raise ProviderError("--media must be a JPG, PNG or GIF image", EXIT_USAGE)
    if args.at:
        try:
            when = parse_iso(args.at)
        except ValueError:
            raise ProviderError(f"--at is not ISO-8601: {args.at}", EXIT_USAGE)
        if when > datetime.now(timezone.utc):
            raise ProviderError(
                "--at is in the future; the LinkedIn member Posts API has no scheduling. "
                "Scheduling belongs to the scheduler class, not to this provider: schedule a "
                "later call of this command without --at.",
                EXIT_USAGE,
            )
    if args.idempotency_key is not None and not args.idempotency_key.strip():
        raise ProviderError("--idempotency-key is empty", EXIT_USAGE)
    return text, image


def result(urn: str, token: dict, key: str | None, replayed: bool) -> dict:
    return {
        "platform": "linkedin",
        "post_urn": urn,
        "post_url": post_url(urn),
        "token_expires_at": token["expires_at"],
        "token_expires_in_days": days_until(token["expires_at"]),
        "idempotency_key": key,
        "replayed": replayed,
    }


def cmd_publish(args) -> int:
    text, image = validate_publish_args(args)
    if not args.dry_run and not args.confirmed:
        raise ProviderError(
            "refusing to publish without --confirmed; the calling skill must pass its confirmation gate "
            "first (use --dry-run to preview)",
            EXIT_USAGE,
        )
    base, test_mode = api_base()
    commentary = escape_little_text(text)
    key = args.idempotency_key

    if args.dry_run:
        return dry_run(base, test_mode, commentary, image, key)

    token = load_token(test_mode)
    if key:
        existing = ledger_read()["entries"].get(key)
        if existing:
            log(f"idempotency key {key!r} already published; returning the existing post")
            print(json.dumps(result(existing["post_urn"], token, key, True), indent=2))
            return EXIT_OK

    access = token["access_token"]
    author = f"urn:li:person:{userinfo(base, access)['sub']}"

    image_urn = None
    if image:
        init_body = {"initializeUploadRequest": {"owner": author}}
        _, _, raw = http(
            "POST",
            f"{base}/rest/images?action=initializeUpload",
            rest_headers(access),
            json.dumps(init_body).encode(),
        )
        try:
            value = json.loads(raw)["value"]
            upload_url, image_urn = value["uploadUrl"], value["image"]
        except (ValueError, KeyError, TypeError):
            raise ProviderError("unexpected initializeUpload response: no value.uploadUrl or value.image")
        check_upload_url(upload_url, base, test_mode)
        http(
            "PUT",
            upload_url,
            {"Authorization": f"Bearer {access}", "Content-Type": "application/octet-stream"},
            image.read_bytes(),
        )
        log(f"uploaded {image.name} as {image_urn}")

    status, headers, _ = http(
        "POST",
        f"{base}/rest/posts",
        rest_headers(access),
        json.dumps(post_body(author, commentary, image_urn)).encode(),
    )
    urn = headers.get("x-restli-id")
    if status != 201 or not urn:
        raise ProviderError(f"unexpected Posts API response: status {status}, no x-restli-id header")
    if key:
        ledger_write(key, urn)
    out = result(urn, token, key, False)
    if out["token_expires_in_days"] is not None and out["token_expires_in_days"] < EXPIRY_WARNING_DAYS:
        log(f"warning: the LinkedIn token expires in {out['token_expires_in_days']} days; rerun auth.py")
    print(json.dumps(out, indent=2))
    return EXIT_OK


def dry_run(base: str, test_mode: bool, commentary: str, image: Path | None, key: str | None) -> int:
    author = AUTHOR_PLACEHOLDER
    try:
        token = load_token(test_mode)
        author = f"urn:li:person:{userinfo(base, token['access_token'])['sub']}"
    except ProviderError as exc:
        log(f"dry run without the author URN: {exc}")
    shown = rest_headers(None)
    shown["Authorization"] = "Bearer <redacted>"
    requests = []
    if image:
        requests.append({
            "method": "POST",
            "url": f"{base}/rest/images?action=initializeUpload",
            "headers": shown,
            "body": {"initializeUploadRequest": {"owner": author}},
        })
        requests.append({
            "method": "PUT",
            "url": UPLOAD_URL_PLACEHOLDER,
            "headers": {"Authorization": "Bearer <redacted>", "Content-Type": "application/octet-stream"},
            "body": f"<{image.stat().st_size} bytes of {image}>",
        })
    requests.append({
        "method": "POST",
        "url": f"{base}/rest/posts",
        "headers": shown,
        "body": post_body(author, commentary, IMAGE_URN_PLACEHOLDER if image else None),
    })
    out = {"dry_run": True, "platform": "linkedin", "requests": requests}
    if key:
        existing = ledger_read()["entries"].get(key)
        out["idempotency_key"] = key
        out["existing_post_urn"] = existing["post_urn"] if existing else None
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return EXIT_OK


# --- check -------------------------------------------------------------------


def cmd_check() -> int:
    base, test_mode = api_base()
    try:
        token = load_token(test_mode)
    except ProviderError as exc:
        raise ProviderError(str(exc), EXIT_SERVICE)  # the contract: --check exits 1 when not ready
    info = userinfo(base, token["access_token"])
    days = days_until(token["expires_at"])
    out = {
        "ready": True,
        "platform": "linkedin",
        "member_name": info.get("name"),
        "person_urn": f"urn:li:person:{info['sub']}",
        "token_expires_at": token["expires_at"],
        "token_expires_in_days": days,
        "api_version": LINKEDIN_VERSION,
    }
    if days is None:
        log("warning: token expiry unknown")
    elif days < EXPIRY_WARNING_DAYS:
        out["warning"] = f"token expires in {days} days"
        log(f"warning: the LinkedIn token expires in {days} days; rerun auth.py --provider linkedin")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return EXIT_OK


# --- entry point ---------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="linkedin.py",
        description="Publisher provider for LinkedIn: publishes a post as the authenticated member "
        "through the versioned Posts API.",
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("verb", nargs="?", choices=["publish"], help="the action to run")
    parser.add_argument("--check", action="store_true", help="verify the token and print the member; no side effects")
    parser.add_argument("--platform", help="must be linkedin")
    parser.add_argument("--text-file", help="UTF-8 file with the post text; reserved characters are escaped")
    parser.add_argument("--media", action="append", help="one JPG, PNG or GIF image to attach")
    parser.add_argument("--at", help="ISO-8601 time; a future time is refused (use the scheduler class)")
    parser.add_argument("--idempotency-key", help="publish at most once per key (recorded in the local ledger)")
    parser.add_argument("--dry-run", action="store_true", help="print the exact request bodies and do nothing else")
    parser.add_argument("--confirmed", action="store_true", help="required to publish; set by the calling skill's gate")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.check:
            return cmd_check()
        if args.verb == "publish":
            if not args.platform or not args.text_file:
                raise ProviderError("publish needs --platform linkedin and --text-file <f>", EXIT_USAGE)
            return cmd_publish(args)
        raise ProviderError("give a verb (publish) or --check; see --help", EXIT_USAGE)
    except ProviderError as exc:
        log(f"error: {exc}")
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
