"""Offline tests of the key proxy (evals/container/keyproxy/keyproxy.py), against a stand-in provider on this
machine that speaks HTTPS with a certificate made for the test. No docker, no real provider, no real key.

Run: uv run --with pytest pytest evals/tests/test_keyproxy.py
"""
from __future__ import annotations

import http.client
import http.server
import importlib.util
import io
import json
import shutil
import socket
import socketserver
import ssl
import subprocess
import sys
import threading
from pathlib import Path

import pytest

FOLDER = Path(__file__).resolve().parents[1] / "container" / "keyproxy"
_spec = importlib.util.spec_from_file_location("keyproxy", FOLDER / "keyproxy.py")
kp = importlib.util.module_from_spec(_spec)
_writes = sys.dont_write_bytecode
sys.dont_write_bytecode = True  # a cache folder in evals/container/ would change the definition's hash
try:
    _spec.loader.exec_module(kp)
finally:
    sys.dont_write_bytecode = _writes

KEY = "fake-floor-key-held-by-the-proxy-0001"
FROM_THE_RUN = "fake-value-a-run-sends-0002"


@pytest.fixture(scope="module")
def tls(tmp_path_factory):
    """A certificate for 127.0.0.1, made for the test: (certificate, private key)."""
    if not shutil.which("openssl"):
        pytest.skip("openssl is needed to make the stand-in provider's certificate")
    folder = tmp_path_factory.mktemp("tls")
    cert, key = folder / "cert.pem", folder / "key.pem"
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1", "-subj", "/CN=127.0.0.1",
                    "-addext", "subjectAltName=IP:127.0.0.1", "-keyout", str(key), "-out", str(cert)],
                   check=True, capture_output=True)
    return cert, key


class Provider(http.server.ThreadingHTTPServer):
    """The stand-in provider: it records each request and answers by path."""
    daemon_threads = True

    def __init__(self, tls):
        super().__init__(("127.0.0.1", 0), ProviderHandler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(tls[0]), str(tls[1]))
        self.socket = context.wrap_socket(self.socket, server_side=True)
        self.seen, self.release, self.released_in_time = [], threading.Event(), None


class ProviderHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def answer(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        self.server.seen.append({"method": self.command, "path": self.path, "headers": dict(self.headers.items()),
                                 "authorization": self.headers.get_all("Authorization"), "body": body})
        if self.path.startswith("/api/v1/stream"):  # an answer in two events, the second held until the test says
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            first = b"data: first\n\n"
            self.wfile.write(b"%x\r\n%s\r\n" % (len(first), first))
            self.wfile.flush()
            self.server.released_in_time = self.server.release.wait(10)
            last = b"data: [DONE]\n\n"
            self.wfile.write(b"%x\r\n%s\r\n0\r\n\r\n" % (len(last), last))
            return
        out = json.dumps({"path": self.path, "authorization": self.headers.get("Authorization")}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    do_GET = do_POST = answer


def serve(server):
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    return server


@pytest.fixture
def provider(tls):
    server = serve(Provider(tls))
    yield server
    server.shutdown()
    server.server_close()


def start(provider_port, cafile, egress=None, upstream=None):
    """A key proxy on 127.0.0.1 in front of the stand-in, with its log kept: (server, log)."""
    route = kp.load_route(kp.ROUTE, upstream or f"https://127.0.0.1:{provider_port}")
    log = io.StringIO()
    server = serve(kp.KeyProxy(("127.0.0.1", 0), route, KEY, str(cafile) if cafile else None, egress, log))
    return server, log


@pytest.fixture
def proxied(provider, tls):
    server, log = start(provider.server_address[1], tls[0])
    yield server, log
    server.shutdown()
    server.server_close()


def call(server, method, path, body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=20)
    conn.request(method, path, body=body, headers=headers or {})
    resp = conn.getresponse()
    data = resp.read()
    conn.close()
    return resp, data


def raw(server, request):
    """Send a request exactly as written and return the status line."""
    with socket.create_connection(("127.0.0.1", server.server_address[1]), timeout=20) as s:
        s.sendall(request.encode())
        return s.makefile("rb").readline().decode()


def test_the_proxy_adds_the_key_and_removes_the_authorization_a_run_sends(provider, proxied):
    server, _ = proxied
    body = json.dumps({"model": "vendor/model", "messages": [{"role": "user", "content": "hi"}]}).encode()
    resp, data = call(server, "POST", "/api/v1/chat/completions?x=1", body,
                      {"Authorization": f"Bearer {FROM_THE_RUN}", "Content-Type": "application/json", "X-Title": "eval",
                       "Host": "elsewhere.example", "Proxy-Authorization": f"Basic {FROM_THE_RUN}"})
    assert resp.status == 200
    seen = provider.seen[-1]
    assert seen["authorization"] == [f"Bearer {KEY}"]  # one header, the proxy's own
    assert seen["path"] == "/api/v1/chat/completions?x=1" and seen["body"] == body
    assert seen["headers"]["Host"] == f"127.0.0.1:{provider.server_address[1]}"  # never the Host the run sent
    assert seen["headers"]["X-Title"] == "eval" and seen["headers"]["Content-Type"] == "application/json"
    assert not any(FROM_THE_RUN in v for v in seen["headers"].values())
    assert json.loads(data)["authorization"] == f"Bearer {KEY}"


@pytest.mark.parametrize("request_line, status", [
    ("GET /api/v2/models HTTP/1.1", 403),
    ("GET / HTTP/1.1", 403),
    ("GET /api/v1/../../admin HTTP/1.1", 403),
    ("GET /api/v1/%2e%2e/admin HTTP/1.1", 403),
    ("GET /api/v1/./models HTTP/1.1", 403),
    ("GET http://elsewhere.example/api/v1/models HTTP/1.1", 403),
    ("GET https://openrouter.ai/api/v1/models HTTP/1.1", 403),
    ("CONNECT elsewhere.example:443 HTTP/1.1", 405),
])
def test_another_path_another_host_and_a_tunnel_are_refused_and_nothing_is_forwarded(provider, proxied, request_line, status):
    server, _ = proxied
    line = raw(server, f"{request_line}\r\nHost: elsewhere.example\r\nAuthorization: Bearer {FROM_THE_RUN}\r\n\r\n")
    assert line.split()[1] == str(status)
    assert provider.seen == []


def test_the_host_a_run_names_never_moves_the_call(provider, proxied):
    server, _ = proxied
    line = raw(server, "GET /api/v1/models HTTP/1.1\r\nHost: elsewhere.example\r\n\r\n")
    assert line.split()[1] == "200" and len(provider.seen) == 1
    assert provider.seen[0]["headers"]["Host"] == f"127.0.0.1:{provider.server_address[1]}"


def test_the_log_holds_no_header_and_no_key(provider, proxied, tls):
    server, log = proxied
    call(server, "POST", "/api/v1/chat/completions", b"{}", {"Authorization": f"Bearer {FROM_THE_RUN}"})
    call(server, "GET", "/api/v2/other", headers={"Authorization": f"Bearer {FROM_THE_RUN}"})
    down, down_log = start(1, tls[0])  # nothing listens on port 1: the provider cannot be reached
    try:
        resp, data = call(down, "POST", "/api/v1/chat/completions", b"{}", {"Authorization": f"Bearer {FROM_THE_RUN}"})
    finally:
        down.shutdown()
        down.server_close()
    assert resp.status == 502 and KEY.encode() not in data
    text = log.getvalue() + down_log.getvalue()
    assert "POST /api/v1/chat/completions 200" in text and "GET /api/v2/other 403" in text
    assert "POST /api/v1/chat/completions 502" in text
    for absent in (KEY, FROM_THE_RUN, "Authorization", "Bearer"):
        assert absent not in text


def test_a_streamed_answer_passes_through_as_it_arrives(provider, proxied):
    server, _ = proxied
    conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=20)
    conn.request("POST", "/api/v1/stream", body=b"{}", headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    assert resp.status == 200 and resp.getheader("Content-Type") == "text/event-stream"
    got = b""
    while b"first" not in got:  # the provider holds its second event until this arrives
        block = resp.read1(1024)
        assert block, "the stream ended before its first event"
        got += block
    assert provider.released_in_time is None  # the provider is still waiting: nothing was buffered to the end
    provider.release.set()
    got += resp.read()
    conn.close()
    assert got == b"data: first\n\ndata: [DONE]\n\n" and provider.released_in_time is True


class Tunnel(socketserver.ThreadingTCPServer):
    """A stand-in egress proxy: it records the target of each CONNECT and relays the bytes."""
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self):
        self.targets = []
        super().__init__(("127.0.0.1", 0), TunnelHandler)


class TunnelHandler(socketserver.StreamRequestHandler):
    def handle(self):
        line = self.rfile.readline().decode()
        while self.rfile.readline() not in (b"\r\n", b"\n", b""):
            pass
        method, target, _ = line.split()
        self.server.targets.append((method, target))
        host, port = target.rsplit(":", 1)
        upstream = socket.create_connection((host, int(port)), timeout=20)
        self.wfile.write(b"HTTP/1.1 200 Connection established\r\n\r\n")

        def pipe(src, dst):
            try:
                while data := src.recv(65536):
                    dst.sendall(data)
            except OSError:
                pass
            finally:
                for s in (src, dst):
                    try:
                        s.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
        back = threading.Thread(target=pipe, args=(upstream, self.connection), daemon=True)
        back.start()
        pipe(self.connection, upstream)
        back.join(5)


def test_through_the_egress_proxy_the_call_is_a_tunnel_to_the_one_provider(provider, tls):
    tunnel = serve(Tunnel())
    server, _ = start(provider.server_address[1], tls[0], egress=("127.0.0.1", tunnel.server_address[1]))
    try:
        resp, data = call(server, "GET", "/api/v1/models", headers={"Host": "elsewhere.example"})
    finally:
        server.shutdown()
        server.server_close()
        tunnel.shutdown()
        tunnel.server_close()
    assert resp.status == 200 and json.loads(data)["authorization"] == f"Bearer {KEY}"
    assert tunnel.targets == [("CONNECT", f"127.0.0.1:{provider.server_address[1]}")]


def test_the_providers_certificate_is_verified(provider, tls):
    server, _ = start(provider.server_address[1], None)  # the system's certificates do not know the stand-in
    try:
        resp, _ = call(server, "GET", "/api/v1/models")
    finally:
        server.shutdown()
        server.server_close()
    assert resp.status == 502 and provider.seen == []


def test_the_route_is_the_floor_providers_api_over_https_with_the_egress_proxys_timeout():
    route = kp.load_route()
    assert route["secret"] == "OPENROUTER_API_KEY" and route["upstream"] == "https://openrouter.ai"
    assert route["prefix"] == "/api/v1/" and route["base_url_env"] == "OPENROUTER_BASE_URL"
    conf = (FOLDER.parent / "proxy" / "tinyproxy.conf").read_text()
    timeout = [int(l.split()[1]) for l in conf.splitlines() if l.startswith("Timeout ")]
    assert timeout == [route["timeout_seconds"]]
    allow = (FOLDER.parent / "proxy" / "allow.txt").read_text().split()
    assert "^openrouter\\.ai$" in allow  # the egress proxy lets the key proxy's one host through
    for upstream in ("http://openrouter.ai", "https://openrouter.ai/other", "https://user@openrouter.ai", "ftp://x"):
        with pytest.raises(kp.RouteError):
            kp.load_route(kp.ROUTE, upstream)


def test_without_its_key_the_proxy_does_not_start(monkeypatch, capsys):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    monkeypatch.delenv("https_proxy", raising=False)
    assert kp.main(["--port", "1"]) == 2
    assert "OPENROUTER_API_KEY is not set" in capsys.readouterr().err
    monkeypatch.setenv("OPENROUTER_API_KEY", "two\nlines")
    assert kp.main(["--listen", "127.0.0.1", "--port", "0"]) == 2
    err = capsys.readouterr().err
    assert "cannot start" in err and "two" not in err
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    assert kp.main(["--upstream", "http://insecure.example"]) == 2  # the provider is reached over HTTPS only
