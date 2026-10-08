"""Tests of the files of the local interface (interface/): what the page's own files call and load, the rules they keep
about the token and the markup, and the vendored libraries' hashes. The files are static: nothing here starts a server
or a browser. The service's own rules are tested in test_service.py.

Run: uv run --with pytest==9.1.1 pytest runtime/tests/test_interface_files.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

import standin_tree as st

service = st.load("service")

INTERFACE = st.REPO / "interface"
VENDOR = INTERFACE / "vendor"
CLIENT = INTERFACE / "js" / "api.js"
SUFFIXES = (".html", ".css", ".js")
SCHEME = re.compile(r"^(?:[A-Za-z][A-Za-z0-9+.-]*:|//)")


def own_files():
    """The page's own html, css and js files: everything under interface/ that is not vendored."""
    return sorted(p for p in INTERFACE.rglob("*") if p.is_file() and p.suffix in SUFFIXES and VENDOR not in p.parents)


def vendored_files():
    return sorted(p for p in VENDOR.rglob("*") if p.is_file() and p.suffix in SUFFIXES)


def rel(path: Path) -> str:
    return str(path.relative_to(st.REPO))


def inside_interface(target: Path) -> bool:
    root = os.path.realpath(INTERFACE)
    real = os.path.realpath(target)
    return real == root or real.startswith(root + os.sep)


def resolves(source: Path, reference: str) -> bool:
    """True when a relative reference from `source` names an existing file inside interface/."""
    path = reference.split("#", 1)[0].split("?", 1)[0]
    if not path:
        return True  # a hash link to the same page
    target = (source.parent / path)
    return inside_interface(target) and target.is_file()


def call_text(source: str, start: int) -> str:
    """The text of the call whose opening parenthesis is at `start`, up to its matching closing one."""
    depth = 0
    for i in range(start, len(source)):
        if source[i] == "(":
            depth += 1
        elif source[i] == ")":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    return source[start:]


# --- the client and the service's routes -------------------------------------------------------------------------------


def client_calls():
    """Every call `send("<METHOD>", <path>, ...)` of the client: [(method, path template, whole call text)]."""
    source = CLIENT.read_text(encoding="utf-8")
    out = []
    for found in re.finditer(r'\bsend\(\s*"(GET|POST)"\s*,\s*(["`])([^"`]*)\2', source):
        out.append((found.group(1), found.group(3), call_text(source, source.index("(", found.start()))))
    return source, out


def shape(path: str) -> tuple:
    """A path as its segments, each parameter (`{p}` of a route, `${...}` of the client) as a star."""
    return tuple("*" if re.fullmatch(r"\{\w+\}|\$\{.*\}", part) else part for part in path.split("/"))


def test_every_route_the_interface_files_call_is_a_route_of_the_service():
    source, calls = client_calls()
    prefix = re.search(r'const PREFIX = "([^"]+)"', source)
    assert prefix and prefix.group(1) == service.PREFIX, "the client's prefix is the service's"
    assert len(calls) >= 20, "the client's calls were not found: did the form of `send(...)` change?"
    routes = [(r["method"], shape(r["pattern"]), r) for r in service.ROUTES]
    seen = set()
    for method, template, text in calls:
        found = [r for m, s, r in routes if m == method and s == shape(template)]
        assert found, f"api.js calls {method} {template}, which is not a route of the service"
        route = found[0]
        seen.add((method, route["pattern"]))
        if re.search(r"\bquery\s*:", text):
            assert method == "GET" and not route["own"] and route["take"] != (), \
                f"api.js sends a query to {method} {template}, a route that takes none"
        for part in re.findall(r"\$\{([^}]*)\}", template):
            assert re.fullmatch(r"enc\(\w+\)", part), f"a path part of {template} is not encoded with enc(): {part}"
    assert ("GET", "/projects") in seen and ("GET", "/jobs/{id}") in seen, "the project list and the job route are called"


def test_the_client_sends_the_token_only_as_a_bearer_header_and_a_post_as_json():
    source = CLIENT.read_text(encoding="utf-8")
    assert "`Bearer ${token}`" in source and '"Content-Type"] = "application/json"' in source
    assert 'credentials: "omit"' in source and 'cache: "no-store"' in source
    assert not re.search(r"\btoken\b[^\n]*(?:url|query)\b", source.replace("const token = getToken();", "")), \
        "the token is not put in the url or the query"
    for name in ("token.js", "api.js"):
        assert "console." not in (INTERFACE / "js" / name).read_text(encoding="utf-8"), f"{name} logs nothing"


# --- nothing from another host -----------------------------------------------------------------------------------------


def references(path: Path, text: str):
    """What a file of the page loads or links: [(kind, reference)]."""
    out = []
    if path.suffix == ".html":
        out += [("html attribute", m.group(2)) for m in re.finditer(r'\b(src|href|action|poster|data)\s*=\s*"([^"]*)"', text)]
        out += [("html attribute", m.group(2)) for m in re.finditer(r"\b(src|href|action|poster|data)\s*=\s*'([^']*)'", text)]
        for block in re.findall(r'<script[^>]*type\s*=\s*"importmap"[^>]*>(.*?)</script>', text, re.S):
            imports = json.loads(block).get("imports", {})
            out += [("import map entry", v) for v in imports.values()]
    if path.suffix == ".css":
        out += [("css import", m.group(1)) for m in re.finditer(r'@import\s+(?:url\()?\s*["\']?([^"\')\s;]+)', text)]
        out += [("css url", m.group(1)) for m in re.finditer(r'url\(\s*["\']?([^"\')]+)', text)]
    if path.suffix == ".js":
        out += [("js import", m.group(1)) for m in re.finditer(r'\bimport\s*(?:[^"\';()]*?\sfrom\s*)?["\']([^"\']+)["\']', text)]
        out += [("js export from", m.group(1)) for m in re.finditer(r'\bexport\s[^"\';]*?\sfrom\s*["\']([^"\']+)["\']', text)]
        out += [("js dynamic import", m.group(1)) for m in re.finditer(r'\bimport\(\s*["\']([^"\']+)["\']', text)]
        out += [("js fetch", m.group(1)) for m in re.finditer(r'\bfetch\(\s*["\'`]([^"\'`]+)', text)]
        out += [("js worker or socket", m.group(1)) for m in re.finditer(r'\bnew\s+(?:Worker|SharedWorker|WebSocket|EventSource)\(\s*["\'`]([^"\'`]+)', text)]
    return out


def test_the_interface_files_load_nothing_from_another_host():
    files = own_files()
    assert {p.name for p in files} >= {"index.html", "style.css", "main.js", "api.js"}, "the page's files are there"
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"https?://|(?<![:\w])//[A-Za-z0-9.-]+\.[A-Za-z]", text), \
            f"{rel(path)} names a host: the page's own files load nothing from another host"
        for kind, reference in references(path, text):
            assert not SCHEME.match(reference), f"{rel(path)}: {kind} {reference!r} is not a relative path"
            if kind in ("js import", "js export from", "js dynamic import"):
                assert reference.startswith(("./", "../")), f"{rel(path)}: {kind} {reference!r} is a bare name (no import map is possible)"
                assert resolves(path, reference), f"{rel(path)}: {kind} {reference!r} is not a file inside interface/"
            elif kind == "js fetch":
                assert reference.startswith(("/api/", "./", "../")) or reference == "/api", f"{rel(path)}: fetch of {reference!r}"
            elif kind in ("html attribute", "css import", "css url", "import map entry"):
                assert resolves(path, reference), f"{rel(path)}: {kind} {reference!r} is not a file inside interface/"
    # The vendored libraries are not read line by line (they are not ours), but they must not load a script or fetch
    # from another host, and what they import by a path stays in their folder.
    other_host = re.compile(r"""<script[^>]*\ssrc\s*=\s*["']?(?:https?:)?//|\bfetch\(\s*["'`](?:https?:)?//|\bnew\s+(?:Worker|WebSocket|EventSource)\(\s*["'`](?:https?:|wss?:)?//|@import\s+(?:url\()?\s*["']?(?:https?:)?//""")
    for path in vendored_files():
        text = path.read_text(encoding="utf-8")
        assert not other_host.search(text), f"{rel(path)} loads from another host"
        for match in re.finditer(r"^import\s[^\n]*?from\s*['\"]([^'\"]+)['\"]", text, re.M):
            assert match.group(1).startswith("./") and resolves(path, match.group(1)), f"{rel(path)} imports {match.group(1)}"


# --- the vendored files and their hashes -------------------------------------------------------------------------------

ROW = re.compile(r"^\| `([^`]+)` \| (\d+) \| `([0-9a-f]{64})` \|$", re.M)


def vendored_folders():
    return sorted(p for p in VENDOR.iterdir() if p.is_dir())


def test_the_vendored_files_match_the_hashes_their_readmes_record():
    folders = vendored_folders()
    assert len(folders) >= 2, "two libraries are vendored, each in a folder of its own"
    for folder in folders:
        readme = folder / "README.md"
        assert readme.is_file(), f"{rel(folder)} has no README.md"
        text = readme.read_text(encoding="utf-8")
        assert re.search(r"^- Package: ", text, re.M) and re.search(r"^- Version: \*\*[0-9][^*]*\*\*", text, re.M) \
            and re.search(r"^- Licence: MIT", text, re.M), f"{rel(readme)} says its package, exact version and licence"
        rows = ROW.findall(text)
        assert rows, f"{rel(readme)} records no hash"
        recorded = {name: (int(size), digest) for name, size, digest in rows}
        assert len(recorded) == len(rows), f"{rel(readme)} lists a file twice"
        present = {str(p.relative_to(folder)) for p in folder.rglob("*") if p.is_file()} - {"README.md"}
        assert present == set(recorded), \
            f"{rel(folder)}: files without a recorded hash {sorted(present - set(recorded))}, hashes without a file {sorted(set(recorded) - present)}"
        for name, (size, digest) in recorded.items():
            data = (folder / name).read_bytes()
            assert len(data) == size, f"{rel(folder / name)} has {len(data)} bytes; its README records {size}"
            assert hashlib.sha256(data).hexdigest() == digest, f"{rel(folder / name)} is not the file its README records"
        assert any(name.upper().startswith("LICENSE") for name in recorded), f"{rel(folder)} holds the licence text"


# --- the page's markup and the token -----------------------------------------------------------------------------------

FORBIDDEN_IN_MODULES = (
    (r"\blocalStorage\b", "localStorage"), (r"\bdocument\.cookie\b", "document.cookie"), (r"\binnerHTML\b", "innerHTML"),
    (r"\bouterHTML\b", "outerHTML"), (r"\binsertAdjacentHTML\b", "insertAdjacentHTML"), (r"\bdocument\.write", "document.write"),
    (r"\bnew\s+Function\b", "new Function"), (r"[?&]token\b", "a token in a query"),
    (r"\beval\s*\(", "eval("),  # security-scan: allow dynamic-eval -- a pattern that forbids a call of the page's modules; nothing runs it
    (r"\btoken=", "token= in a url"), (r"""setAttribute\(\s*["']style["']""", "an inline style"), (r"\.cssText\b", "cssText"),
    (r"\bindexedDB\b", "indexedDB"),
)


def test_the_page_sets_no_inline_script_and_no_token_in_a_url_or_storage_other_than_session():
    html = (INTERFACE / "index.html").read_text(encoding="utf-8")
    for tag in re.findall(r"<script\b[^>]*>", html):
        assert re.search(r'\ssrc\s*=\s*"\./', tag), f"index.html has a script with no relative src (an inline script is refused by the policy): {tag}"
    for block in re.findall(r"<script\b[^>]*>(.*?)</script>", html, re.S):
        assert not block.strip(), "index.html has inline script text"
    assert not re.search(r"<style\b|\sstyle\s*=|\son[a-z]+\s*=", html), "index.html has an inline style or an event attribute"
    for path in own_files():
        if path.suffix != ".js":
            continue
        text = path.read_text(encoding="utf-8")
        for pattern, name in FORBIDDEN_IN_MODULES:
            assert not re.search(pattern, text), f"{rel(path)} uses {name}"
        if path.name != "token.js":
            assert "sessionStorage" not in text, f"{rel(path)}: the token module is the only one that touches sessionStorage"
    token = (INTERFACE / "js" / "token.js").read_text(encoding="utf-8")
    assert "sessionStorage" in token and "document.cookie" not in token
    # Text of the service is put in the page as text: the builder never takes markup, and refuses a style or an event attribute.
    dom = (INTERFACE / "js" / "dom.js").read_text(encoding="utf-8")
    assert "textContent" in dom and "FORBIDDEN" in dom


def test_the_page_is_one_policy_safe_html_document_with_the_library_and_its_own_modules():
    html = (INTERFACE / "index.html").read_text(encoding="utf-8")
    assert 'name="viewport"' in html and "<title>" in html
    assert re.search(r'href="\./vendor/[a-z]+/[a-z]+\.css"', html) and 'src="./js/main.js"' in html
    assert not (INTERFACE / "package.json").exists() and not (INTERFACE / "node_modules").exists(), "no build step, no package"
    css = (INTERFACE / "style.css").read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in css and "16px" in css
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(", css), "style.css sets no colour of its own: the library's tokens decide"


# --- what the screens call, and when they read ---------------------------------------------------------------------------------


def test_every_client_function_the_screens_call_exists_and_the_city_only_reads():
    exported = set(re.findall(r"^export (?:async )?function (\w+)", CLIENT.read_text(encoding="utf-8"), re.M))
    writes = {"answer", "release", "approve", "reject", "request", "route", "cancel", "retry", "handOver", "verdict", "setMode", "say", "sync", "dispatch"}
    used = {}
    for path in own_files():
        if path.suffix != ".js" or path == CLIENT:
            continue
        for name in re.findall(r"\bapi\.(\w+)\(", path.read_text(encoding="utf-8")):
            used.setdefault(name, set()).add(str(path.relative_to(INTERFACE / "js")))
    assert {"projects", "status", "agents", "task"} <= set(used), "the City reads the project list, the status, the agents and one task"
    for name, files in used.items():
        assert name in exported or name == "onAuthFailure", f"{sorted(files)} call api.{name}, which api.js does not export"
    # Only the modules of a screen that acts (the Lobby's views and the decision cards) write; the City, the frame and the page read.
    writers = {f for name in writes for f in used.get(name, set())}
    assert all(f.startswith(("views/lobby", "cards/")) for f in writers), f"a module that only reads calls a route that writes: {sorted(writers)}"


def test_the_page_reads_every_five_seconds_while_visible_and_never_while_hidden():
    main = (INTERFACE / "js" / "main.js").read_text(encoding="utf-8")
    assert "const POLL_MS = 5000;" in main and "const RETRY_MS = 10000;" in main
    assert re.search(r"function schedule\(ms\) \{[^}]*!document\.hidden", main, re.S), "a poll is scheduled only while the document is visible"
    assert 'addEventListener("visibilitychange"' in main and "stopPolling()" in main, "hiding the document stops the poll; showing it reads once"
    assert "setInterval" not in main


def test_the_screens_keep_no_state_in_a_global_and_the_token_stays_in_the_token_module():
    for path in own_files():
        if path.suffix != ".js":
            continue
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"\bwindow\.__|\bglobalThis\.\w+\s*=", text), f"{rel(path)} keeps state in a global"
        if path.name not in ("token.js", "api.js", "main.js"):
            assert not re.search(r"\b(?:getToken|setToken)\(", text), f"{rel(path)} touches the token"


# --- the Lobby (WP-9.4): its own checks are in test_interface_lobby.py; these are the rules read from the files --------------------


def test_the_lobby_calls_only_routes_of_the_service_and_every_hash_it_links_to_is_a_form_of_the_router():
    names = ("lobby.js", "lobby-actions.js", "lobby-request.js", "plan.js")
    files = [p for p in own_files() if p.name in names]
    assert {p.name for p in files} == set(names), "the Lobby's modules are where the package puts them"
    exported = set(re.findall(r"^export (?:async )?function (\w+)", CLIENT.read_text(encoding="utf-8"), re.M))
    wanted = {"say", "conversation", "request", "route", "cancel", "approve", "reject", "flows", "task", "pollJob"}
    assert wanted <= exported, "the client has the Lobby's calls"
    routes = {(r["method"], r["pattern"]) for r in service.ROUTES}
    for route in (("POST", "/projects/{p}/conversation"), ("GET", "/projects/{p}/conversation"), ("POST", "/projects/{p}/requests"),
                  ("POST", "/projects/{p}/requests/{id}/route"), ("POST", "/projects/{p}/requests/{id}/cancel"), ("GET", "/projects/{p}/flows"),
                  ("GET", "/projects/{p}/tasks/{id}"), ("POST", "/projects/{p}/pending/{id}/approve"), ("POST", "/projects/{p}/pending/{id}/reject")):
        assert route in routes, f"{route} is not a route of the service"
    for path in files:
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r'href: ([^,}]+)', text):
            assert target.strip().startswith("router.") or target.strip().startswith('"#'), f"{path.name}: a link that is not built by the router: {target}"


def test_the_lobby_shows_what_came_as_text_only_and_keeps_no_state_outside_its_view():
    for name in ("lobby.js", "lobby-thread.js", "lobby-request.js", "lobby-composer.js", "lobby-form.js", "plan.js"):
        path = next(p for p in own_files() if p.name == name)
        text = path.read_text(encoding="utf-8")
        assert "innerHTML" not in text and "insertAdjacentHTML" not in text and "createContextualFragment" not in text, name
        assert not re.search(r"\.style\b|setAttribute\(\s*[\"']style", text), f"{name} writes no style"
    lobby = (INTERFACE / "js" / "views" / "lobby.js").read_text(encoding="utf-8")
    assert "setInterval" not in lobby, "the conversation is read by a timeout that the visibility rule can stop"
    assert "localStorage" not in lobby and "sessionStorage" not in lobby
