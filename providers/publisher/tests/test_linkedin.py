"""Offline tests for providers/publisher/linkedin.py and auth.py.

Run: uv run --with pytest pytest providers/publisher/tests

No network and no real credentials: a local fake LinkedIn server answers on
127.0.0.1 (LINKEDIN_API_BASE), the token is a fake one in LINKEDIN_ACCESS_TOKEN,
and the idempotency ledger lives in a temporary directory (PUBLISHER_LINKEDIN_LEDGER).
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "linkedin.py"
AUTH_SCRIPT = HERE.parent / "auth.py"
FAKE_TOKEN = "FAKE-test-token-9f8e7d6c5b4a-never-print-me"
SUB = "782bbtaQ"
AUTHOR = f"urn:li:person:{SUB}"
POST_URN = "urn:li:share:7000000000000000001"
IMAGE_URN = "urn:li:image:C4E10AQFoyyAjHPMQuQ"
RESERVED_TEXT = "a\\b|c{d}e@f[g]h(i)j<k>l#m*n_o~p"
RESERVED_ESCAPED = "a\\\\b\\|c\\{d\\}e\\@f\\[g\\]h\\(i\\)j\\<k\\>l\\#m\\*n\\_o\\~p"


def load_module():
    spec = importlib.util.spec_from_file_location("linkedin_provider", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeLinkedIn:
    """A tiny LinkedIn stand-in that records every request."""

    def __init__(self):
        self.requests: list[dict] = []
        self.post_status = 201
        self.post_delay = 0.0
        self.userinfo_status = 200
        self.redirect_userinfo = False
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def _record(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                fake.requests.append({
                    "method": self.command,
                    "path": self.path,
                    "headers": {k.lower(): v for k, v in self.headers.items()},
                    "body": body,
                })
                return body

            def _send(self, status, payload=None, headers=None):
                data = json.dumps(payload).encode() if payload is not None else b""
                self.send_response(status)
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                if payload is not None:
                    self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):  # noqa: N802
                self._record()
                if self.path == "/v2/userinfo":
                    if fake.redirect_userinfo:
                        return self._send(302, None, {"Location": f"{fake.base}/captured"})
                    if fake.userinfo_status != 200:
                        return self._send(fake.userinfo_status, {"message": "Invalid access token", "status": 401})
                    return self._send(200, {"sub": SUB, "name": "Test Member", "given_name": "Test"})
                self._send(404, {"message": "not found"})

            def do_POST(self):  # noqa: N802
                self._record()
                if self.path == "/rest/images?action=initializeUpload":
                    return self._send(200, {"value": {
                        "uploadUrlExpiresAt": 1650567510704,
                        "uploadUrl": f"{fake.base}/dms-uploads/C4E10AQFoyyAjHPMQuQ/uploaded-image/0?ut=abc",
                        "image": IMAGE_URN,
                    }})
                if self.path == "/rest/posts":
                    if fake.post_delay:
                        time.sleep(fake.post_delay)
                    if fake.post_status != 201:
                        return self._send(fake.post_status, {"message": "MISSING_FIELD", "status": fake.post_status})
                    return self._send(201, None, {"x-restli-id": POST_URN})
                self._send(404, {"message": "not found"})

            def do_PUT(self):  # noqa: N802
                self._record()
                if self.path.startswith("/dms-uploads/"):
                    return self._send(201)
                self._send(404, {"message": "not found"})

            def log_message(self, *args):
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()

    def paths(self):
        return [(r["method"], r["path"]) for r in self.requests]


@pytest.fixture()
def fake():
    server = FakeLinkedIn()
    yield server
    server.close()


@pytest.fixture()
def env(tmp_path, fake):
    base_env = {k: v for k, v in os.environ.items()
                if not k.startswith(("LINKEDIN_", "PUBLISHER_"))}
    base_env.update({
        "HOME": str(tmp_path / "home"),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
        "LINKEDIN_API_BASE": fake.base,
        "LINKEDIN_ACCESS_TOKEN": FAKE_TOKEN,
        "LINKEDIN_TOKEN_EXPIRES_AT": (datetime.now(timezone.utc) + timedelta(days=45, hours=1)).isoformat(),
        "PUBLISHER_LINKEDIN_LEDGER": str(tmp_path / "ledger" / "publisher-linkedin.json"),
    })
    return base_env


@pytest.fixture()
def text_file(tmp_path):
    path = tmp_path / "post.txt"
    path.write_text(RESERVED_TEXT + "\n", encoding="utf-8")
    return path


@pytest.fixture()
def image_file(tmp_path):
    path = tmp_path / "cover.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"fake-image-bytes" * 4)
    return path


def run(script, args, env):
    proc = subprocess.run([sys.executable, str(script), *args], env=env,
                          capture_output=True, text=True, timeout=60)
    # No run may ever print the token, not even partially.
    for stream in (proc.stdout, proc.stderr):
        assert FAKE_TOKEN not in stream
        assert FAKE_TOKEN[:12] not in stream
    return proc


def publish_args(text_file, *extra):
    """publish arguments; a fresh idempotency key is added unless the test passes one."""
    args = ["publish", "--platform", "linkedin", "--text-file", str(text_file), *extra]
    if "--idempotency-key" not in extra:
        args += ["--idempotency-key", f"test-{uuid.uuid4().hex}"]
    return args


def ledger(env):
    path = Path(env["PUBLISHER_LINKEDIN_LEDGER"])
    return json.loads(path.read_text())["entries"] if path.exists() else {}


def post_count(fake):
    return len([p for p in fake.paths() if p == ("POST", "/rest/posts")])


def assert_rest_headers(request):
    h = request["headers"]
    assert h["authorization"] == f"Bearer {FAKE_TOKEN}"
    assert h["linkedin-version"] == "202609"
    assert h["x-restli-protocol-version"] == "2.0.0"
    assert h["content-type"] == "application/json"


def expected_post(image_urn=None):
    body = {
        "author": AUTHOR,
        "commentary": RESERVED_ESCAPED,
        "visibility": "PUBLIC",
        "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [],
                         "thirdPartyDistributionChannels": []},
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    if image_urn:
        body["content"] = {"media": {"id": image_urn}}
    return body


# --- unit ----------------------------------------------------------------------


def test_escape_every_reserved_character():
    module = load_module()
    assert module.escape_little_text(RESERVED_TEXT) == RESERVED_ESCAPED
    assert module.escape_little_text("plain text, ok! 100% sure.") == "plain text, ok! 100% sure."
    assert module.escape_little_text("\\*") == "\\\\\\*"


# --- help and guards -------------------------------------------------------------


def test_help_documents_env_and_verbs(env):
    proc = run(SCRIPT, ["--help"], env)
    assert proc.returncode == 0
    for word in ("publish", "--check", "--dry-run", "--confirmed", "LINKEDIN_API_BASE",
                 "PUBLISHER_LINKEDIN_LEDGER", "LINKEDIN_ACCESS_TOKEN", "202609"):
        assert word in proc.stdout


def test_refuses_without_confirmed(env, fake, text_file):
    proc = run(SCRIPT, publish_args(text_file), env)
    assert proc.returncode == 2
    assert "--confirmed" in proc.stderr
    assert fake.requests == []
    assert proc.stdout == ""


def test_refuses_future_at(env, fake, text_file):
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    proc = run(SCRIPT, publish_args(text_file, "--at", future, "--confirmed"), env)
    assert proc.returncode == 2
    assert "scheduler" in proc.stderr
    assert fake.requests == []


def test_past_at_publishes_now(env, fake, text_file):
    past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    proc = run(SCRIPT, publish_args(text_file, "--at", past, "--confirmed"), env)
    assert proc.returncode == 0, proc.stderr
    assert ("POST", "/rest/posts") in fake.paths()


def test_rejects_two_images(env, fake, text_file, image_file):
    proc = run(SCRIPT, publish_args(text_file, "--media", str(image_file), "--media", str(image_file),
                                    "--confirmed"), env)
    assert proc.returncode == 2
    assert fake.requests == []


def test_rejects_wrong_platform(env, fake, text_file):
    args = ["publish", "--platform", "x", "--text-file", str(text_file), "--confirmed"]
    assert run(SCRIPT, args, env).returncode == 2


def test_rejects_non_loopback_api_base(env, text_file):
    env["LINKEDIN_API_BASE"] = "https://evil.example.com"
    proc = run(SCRIPT, publish_args(text_file, "--confirmed"), env)
    assert proc.returncode == 2
    assert "loopback" in proc.stderr


def test_not_configured_without_token(env, fake, text_file):
    del env["LINKEDIN_ACCESS_TOKEN"]
    proc = run(SCRIPT, publish_args(text_file, "--confirmed"), env)
    assert proc.returncode == 3
    assert fake.requests == []


def test_expired_token_is_not_configured(env, fake, text_file):
    env["LINKEDIN_TOKEN_EXPIRES_AT"] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    proc = run(SCRIPT, publish_args(text_file, "--confirmed"), env)
    assert proc.returncode == 3
    assert "expired" in proc.stderr
    assert fake.requests == []


# --- dry run -------------------------------------------------------------------


def test_dry_run_text_prints_exact_body_and_posts_nothing(env, fake, text_file):
    proc = run(SCRIPT, publish_args(text_file, "--dry-run"), env)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["dry_run"] is True
    assert len(out["requests"]) == 1
    req = out["requests"][0]
    assert req["method"] == "POST" and req["url"] == f"{fake.base}/rest/posts"
    body = dict(req["body"])
    assert body.pop("author").startswith("urn:li:person:<")
    assert body == {k: v for k, v in expected_post().items() if k != "author"}
    assert req["headers"]["Authorization"] == "Bearer <redacted>"
    assert req["headers"]["LinkedIn-Version"] == "202609"
    assert fake.requests == []


def test_dry_run_with_image_uses_placeholder(env, fake, text_file, image_file):
    proc = run(SCRIPT, publish_args(text_file, "--media", str(image_file), "--dry-run"), env)
    assert proc.returncode == 0, proc.stderr
    reqs = json.loads(proc.stdout)["requests"]
    assert [r["method"] for r in reqs] == ["POST", "PUT", "POST"]
    assert reqs[0]["body"]["initializeUploadRequest"]["owner"].startswith("urn:li:person:<")
    assert reqs[2]["body"]["content"]["media"]["id"] == "<image URN returned by initializeUpload>"
    assert fake.requests == []


def test_dry_run_without_token_still_prints(env, fake, text_file):
    del env["LINKEDIN_ACCESS_TOKEN"]
    proc = run(SCRIPT, publish_args(text_file, "--dry-run"), env)
    assert proc.returncode == 0
    body = json.loads(proc.stdout)["requests"][0]["body"]
    assert body["author"].startswith("urn:li:person:<")
    assert fake.requests == []


def test_dry_run_reads_no_token(env, fake, text_file):
    # L05: the dry run read the token and called /v2/userinfo.
    env["LINKEDIN_TOKEN_EXPIRES_AT"] = "not a date"  # reading the token would report this
    proc = run(SCRIPT, publish_args(text_file, "--dry-run"), env)
    assert proc.returncode == 0, proc.stderr
    assert "token" not in proc.stderr.lower()
    assert fake.requests == []


# --- publish -------------------------------------------------------------------


def test_publish_text_sends_exact_request(env, fake, text_file):
    proc = run(SCRIPT, publish_args(text_file, "--confirmed"), env)
    assert proc.returncode == 0, proc.stderr
    assert fake.paths() == [("GET", "/v2/userinfo"), ("POST", "/rest/posts")]
    assert fake.requests[0]["headers"]["authorization"] == f"Bearer {FAKE_TOKEN}"
    post = fake.requests[1]
    assert_rest_headers(post)
    assert json.loads(post["body"]) == expected_post()
    out = json.loads(proc.stdout)
    assert out["post_urn"] == POST_URN
    assert out["post_url"] == f"https://www.linkedin.com/feed/update/{POST_URN}/"
    assert out["token_expires_at"].startswith(
        (datetime.now(timezone.utc) + timedelta(days=45, hours=1)).date().isoformat())
    assert out["token_expires_in_days"] == 45
    assert out["replayed"] is False


def test_publish_with_image_upload_sequence(env, fake, text_file, image_file):
    proc = run(SCRIPT, publish_args(text_file, "--media", str(image_file), "--confirmed"), env)
    assert proc.returncode == 0, proc.stderr
    assert [m for m, _ in fake.paths()] == ["GET", "POST", "PUT", "POST"]
    _, init, upload, post = fake.requests
    assert init["path"] == "/rest/images?action=initializeUpload"
    assert_rest_headers(init)
    assert json.loads(init["body"]) == {"initializeUploadRequest": {"owner": AUTHOR}}
    assert upload["path"] == "/dms-uploads/C4E10AQFoyyAjHPMQuQ/uploaded-image/0?ut=abc"
    assert upload["headers"]["authorization"] == f"Bearer {FAKE_TOKEN}"
    assert upload["body"] == image_file.read_bytes()
    assert post["path"] == "/rest/posts"
    assert json.loads(post["body"]) == expected_post(IMAGE_URN)


def test_service_error_exits_1(env, fake, text_file):
    fake.post_status = 400
    proc = run(SCRIPT, publish_args(text_file, "--confirmed"), env)
    assert proc.returncode == 1
    assert "400" in proc.stderr and "MISSING_FIELD" in proc.stderr


def test_rejected_token_exits_3(env, fake, text_file):
    fake.userinfo_status = 401
    proc = run(SCRIPT, publish_args(text_file, "--confirmed"), env)
    assert proc.returncode == 3
    assert ("POST", "/rest/posts") not in fake.paths()


# --- idempotency ---------------------------------------------------------------


def test_idempotency_key_posts_once(env, fake, text_file):
    args = publish_args(text_file, "--idempotency-key", "launch-1", "--confirmed")
    first = run(SCRIPT, args, env)
    assert first.returncode == 0, first.stderr
    second = run(SCRIPT, args, env)
    assert second.returncode == 0, second.stderr
    assert [p for p in fake.paths() if p == ("POST", "/rest/posts")] == [("POST", "/rest/posts")]
    assert json.loads(second.stdout)["post_urn"] == POST_URN
    assert json.loads(second.stdout)["replayed"] is True
    ledger = json.loads(Path(env["PUBLISHER_LINKEDIN_LEDGER"]).read_text())
    assert ledger["entries"]["launch-1"]["post_urn"] == POST_URN
    assert FAKE_TOKEN not in Path(env["PUBLISHER_LINKEDIN_LEDGER"]).read_text()
    # A different key publishes again.
    third = run(SCRIPT, publish_args(text_file, "--idempotency-key", "launch-2", "--confirmed"), env)
    assert third.returncode == 0
    assert len([p for p in fake.paths() if p == ("POST", "/rest/posts")]) == 2


def test_dry_run_reports_existing_key(env, fake, text_file):
    run(SCRIPT, publish_args(text_file, "--idempotency-key", "k", "--confirmed"), env)
    proc = run(SCRIPT, publish_args(text_file, "--idempotency-key", "k", "--dry-run"), env)
    assert json.loads(proc.stdout)["existing_post_urn"] == POST_URN


def test_idempotency_key_is_required(env, fake, text_file):
    # M06: the key was optional, so a retry could publish twice.
    args = ["publish", "--platform", "linkedin", "--text-file", str(text_file)]
    for extra in (["--confirmed"], ["--dry-run"], ["--idempotency-key", " ", "--confirmed"]):
        proc = run(SCRIPT, args + extra, env)
        assert proc.returncode == 2, extra
        assert "--idempotency-key" in proc.stderr
    assert fake.requests == []


def test_timeout_leaves_pending_and_blocks_a_second_post(env, fake, text_file):
    # M06: the ledger was written after the POST; a timeout then a retry published twice.
    fake.post_delay = 2.0
    env["LINKEDIN_HTTP_TIMEOUT"] = "0.5"
    args = publish_args(text_file, "--idempotency-key", "launch-1", "--confirmed")
    first = run(SCRIPT, args, env)
    assert first.returncode == 1
    assert "timed out" in first.stderr
    assert ledger(env)["launch-1"]["status"] == "pending"
    fake.post_delay = 0.0
    second = run(SCRIPT, args, env)
    assert second.returncode == 1
    assert "pending" in second.stderr and "resolve" in second.stderr
    assert post_count(fake) == 1


def test_resolve_a_pending_key(env, fake, text_file):
    fake.post_delay = 2.0
    env["LINKEDIN_HTTP_TIMEOUT"] = "0.5"
    args = publish_args(text_file, "--idempotency-key", "launch-1", "--confirmed")
    assert run(SCRIPT, args, env).returncode == 1
    fake.post_delay = 0.0
    resolve = ["resolve", "--idempotency-key", "launch-1"]
    assert run(SCRIPT, resolve + ["--post-urn", POST_URN], env).returncode == 2  # needs --confirmed
    assert run(SCRIPT, resolve + ["--post-urn", POST_URN, "--confirmed"], env).returncode == 0
    replay = run(SCRIPT, args, env)
    assert replay.returncode == 0 and json.loads(replay.stdout)["replayed"] is True
    assert post_count(fake) == 1
    # A key found not published is released and may be posted again.
    fake.post_delay = 2.0
    args2 = publish_args(text_file, "--idempotency-key", "launch-2", "--confirmed")
    assert run(SCRIPT, args2, env).returncode == 1
    fake.post_delay = 0.0
    done = run(SCRIPT, ["resolve", "--idempotency-key", "launch-2", "--not-published", "--confirmed"], env)
    assert done.returncode == 0, done.stderr
    assert "launch-2" not in ledger(env)
    assert run(SCRIPT, args2, env).returncode == 0
    assert post_count(fake) == 3
    # Only a pending key can be resolved.
    assert run(SCRIPT, resolve + ["--not-published", "--confirmed"], env).returncode == 2


def test_two_runs_at_once_publish_once(env, fake, text_file):
    fake.post_delay = 1.0
    args = [sys.executable, str(SCRIPT), *publish_args(text_file, "--idempotency-key", "same", "--confirmed")]
    procs = [subprocess.Popen(args, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
             for _ in range(2)]
    results = [(p.wait(timeout=30), p.stderr.read()) for p in procs]
    for p in procs:
        p.stdout.close()
        p.stderr.close()
    assert sorted(code for code, _ in results) == [0, 1]
    assert any("pending" in err for code, err in results if code == 1)
    assert post_count(fake) == 1
    assert ledger(env)["same"]["status"] == "published"


def test_failure_before_the_post_releases_the_key(env, fake, text_file):
    fake.userinfo_status = 401
    args = publish_args(text_file, "--idempotency-key", "k", "--confirmed")
    assert run(SCRIPT, args, env).returncode == 3
    assert "k" not in ledger(env)
    fake.userinfo_status = 200
    fake.post_status = 400
    assert run(SCRIPT, args, env).returncode == 1
    assert "k" not in ledger(env)
    fake.post_status = 201
    assert run(SCRIPT, args, env).returncode == 0
    assert ledger(env)["k"]["status"] == "published"


def test_ledger_is_private(env, fake, text_file):
    run(SCRIPT, publish_args(text_file, "--confirmed"), env)
    path = Path(env["PUBLISHER_LINKEDIN_LEDGER"])
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700


# --- redirects -----------------------------------------------------------------


def test_redirect_is_not_followed_with_the_token(env, fake, text_file):
    # L04: urllib followed redirects and forwarded the Authorization header.
    fake.redirect_userinfo = True
    proc = run(SCRIPT, publish_args(text_file, "--confirmed"), env)
    assert proc.returncode == 1
    assert "redirect" in proc.stderr
    assert fake.paths() == [("GET", "/v2/userinfo")]
    assert post_count(fake) == 0


# --- check ---------------------------------------------------------------------


def test_check_reports_member_and_expiry(env, fake):
    proc = run(SCRIPT, ["--check"], env)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["ready"] is True
    assert out["member_name"] == "Test Member"
    assert out["person_urn"] == AUTHOR
    assert out["token_expires_in_days"] == 45
    assert "warning" not in out


def test_check_warns_under_seven_days(env, fake):
    env["LINKEDIN_TOKEN_EXPIRES_AT"] = (datetime.now(timezone.utc) + timedelta(days=3, hours=1)).isoformat()
    proc = run(SCRIPT, ["--check"], env)
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["token_expires_in_days"] == 3
    assert "warning" in proc.stderr


def test_check_not_ready_without_token(env, fake):
    del env["LINKEDIN_ACCESS_TOKEN"]
    proc = run(SCRIPT, ["--check"], env)
    assert proc.returncode == 1
    assert proc.stderr.strip()


# --- auth.py -------------------------------------------------------------------


def test_auth_help_documents_setup(env):
    proc = run(AUTH_SCRIPT, ["--help"], env)
    assert proc.returncode == 0
    for word in ("Share on LinkedIn", "OpenID Connect", "http://localhost:8765/callback",
                 "LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET"):
        assert word in proc.stdout


def test_auth_without_client_env_is_not_configured(env):
    proc = run(AUTH_SCRIPT, ["--provider", "linkedin", "--no-browser"], env)
    assert proc.returncode == 3
    assert "LINKEDIN_CLIENT_ID" in proc.stderr


def test_a_scheduled_copy_needs_the_resolver_in_its_snapshot(env, fake, tmp_path):
    """The scheduler runs a copy of this script from <job>/files/; the resolver must be copied with it."""
    import shutil
    files = tmp_path / "job" / "files"
    files.mkdir(parents=True)
    alone = files / "linkedin.py"
    shutil.copyfile(SCRIPT, alone)
    proc = run(alone, ["--check"], env)
    assert proc.returncode != 0 and "snapshot" in proc.stderr
    shutil.copyfile(HERE.parents[1] / "secrets" / "resolver.py", files / "resolver.py")
    proc = run(alone, ["--check"], env)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["ready"] is True
