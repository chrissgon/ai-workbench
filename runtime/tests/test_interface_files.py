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
    used_outside_floor = {}
    for path in own_files():
        if path.suffix != ".js" or path == CLIENT:
            continue
        for name in re.findall(r"\bapi\.(\w+)\(", path.read_text(encoding="utf-8")):
            used.setdefault(name, set()).add(path.name)
            if "floor" not in path.relative_to(INTERFACE / "js").parts[:-1]:
                used_outside_floor.setdefault(name, set()).add(path.name)
    assert {"projects", "status", "agents", "task"} <= set(used), "the City reads the project list, the status, the agents and one task"
    for name, files in used.items():
        assert name in exported or name == "onAuthFailure", f"{sorted(files)} call api.{name}, which api.js does not export"
    # WP-9.3b: the decision cards, the Agent tab and the request line send the page's writes, and they live in js/floor/ (their
    # client is handed to them through their environment); the City, the Building, the frame and the views only read.
    assert not (set(used_outside_floor) & writes), f"only js/floor/ writes: {sorted(set(used_outside_floor) & writes)}"


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


# --- WP-9.3b: the Building and the Floor ----------------------------------------------------------------------------------------

FLOOR_FILES = ("floor-model.js", "floor/actions.js", "floor/agent-tab.js", "floor/cards.js", "floor/desk-tab.js", "floor/inbox.js",
               "floor/viewer.js", "floor/widgets.js", "views/building.js", "views/floor.js",
               "scene/building.js", "scene/room.js", "scene/figure.js", "scene/furniture.js", "scene/plates.js")


def test_the_building_and_the_floor_are_files_of_the_page_and_the_page_routes_to_them():
    for name in FLOOR_FILES:
        assert (INTERFACE / "js" / name).is_file(), f"interface/js/{name} is a file of the page"
    main = (INTERFACE / "js" / "main.js").read_text(encoding="utf-8")
    assert "createBuildingView" in main and "createFloorView" in main, "the page opens the Building and the Floor, not a placeholder"
    router = (INTERFACE / "js" / "router.js").read_text(encoding="utf-8")
    assert "deskHash" in router and "/desk/" in router, "a document of the desk has a hash of its own"
    assert 'import("' not in main and "import(" not in "".join((INTERFACE / "js" / n).read_text(encoding="utf-8") for n in FLOOR_FILES), "no dynamic import: every file is a static module of the page"


def test_only_the_floor_folder_sends_a_write_and_it_takes_every_write_from_one_object():
    writes = {"answer", "release", "approve", "reject", "verdict", "cancel", "setMode", "retry", "handOver"}
    actions = (INTERFACE / "js" / "floor" / "actions.js").read_text(encoding="utf-8")
    assert set(re.findall(r"^\s+(\w+): api\.(\w+),$", actions, re.M)) == {(w, w) for w in writes | {"pollJob"}}, "actions.js names each write once"
    for name in FLOOR_FILES:
        text = (INTERFACE / "js" / name).read_text(encoding="utf-8")
        if name.startswith(("views/", "scene/")) or name == "floor-model.js":
            assert not (set(re.findall(r"\bapi\.(\w+)\(", text)) & writes), f"{name} only reads"
        if name.startswith("floor/") and name not in ("floor/actions.js", "floor/cards.js", "floor/agent-tab.js"):
            sends = re.findall(r"(?:\bapi\(\)|\bapi|\bactions)\.(\w+)\(", text)
            assert not (set(sends) & writes), f"{name} sends no write: only cards.js and agent-tab.js do, through their environment ({sorted(set(sends) & writes)})"
        if name in ("floor/cards.js", "floor/agent-tab.js"):
            assert 'from "../api.js"' not in text, f"{name} sends through its environment (a client it is given), not through a client of its own"
            assert set(re.findall(r"\bapi\(?\)?\.(\w+)\(", text)) <= writes | {"pollJob"}, f"{name} calls only the operations of its panel"


def test_a_card_sends_the_hash_it_shows_read_back_from_its_own_text_and_nothing_decides_for_the_person():
    cards = (INTERFACE / "js" / "floor" / "cards.js").read_text(encoding="utf-8")
    assert cards.count("state.hashNode.textContent") >= 2, "an effect and a plan are approved with the hash read from the page's own text"
    assert re.search(r"shown !== it\.payload_sha256", cards) and re.search(r"shown !== \(it\.payload && it\.payload\.plan_sha256\)", cards), \
        "a hash that is not the decision's is refused before any request"
    assert "api().approve(env.project, it.id, shown)" in cards and "api().approve(env.project, it.id)" in cards, "an acceptance sends no hash"
    assert not re.search(r"\.trim\(\)\s*\)\s*return\s+refuse", cards) or "typed.answer.trim()" in cards, "an empty answer is not sent"
    for forbidden in ("innerHTML", "insertAdjacentHTML", "document.write", "eval("):  # security-scan: allow dynamic-eval -- a pattern that forbids a call; nothing runs it
        assert forbidden not in cards, f"cards.js builds text with textContent only: {forbidden}"


def test_the_ids_the_scenes_register_are_the_ids_the_screens_open():
    building = (INTERFACE / "js" / "scene" / "building.js").read_text(encoding="utf-8")
    room = (INTERFACE / "js" / "scene" / "room.js").read_text(encoding="utf-8")
    floor_view = (INTERFACE / "js" / "views" / "floor.js").read_text(encoding="utf-8")
    building_view = (INTERFACE / "js" / "views" / "building.js").read_text(encoding="utf-8")
    for hit in re.findall(r'id: "([a-z]+)"', room):
        assert f'"{hit}"' in floor_view, f"the Floor opens something for the room's {hit}"
    assert "sheet:" in room and "sheet:" in floor_view
    assert "floor:" in building and "floor:" in building_view and '"door"' in building and '"door"' in building_view


def test_every_wb_class_the_new_modules_build_is_styled_or_a_hook_the_scripts_read():
    css = (INTERFACE / "style.css").read_text(encoding="utf-8")
    hooks = {"wb-tabpanel", "wb-floor-normal", "wb-label-name", "wb-label-sub", "wb-state-box", "wb-cancel-dialog", "wb-share", "wb-request", "wb-chip"}   # a prefix of a built name, or a custom property
    missing = {}
    for name in FLOOR_FILES:
        text = (INTERFACE / "js" / name).read_text(encoding="utf-8")
        for cls in set(re.findall(r"\bwb-[a-z0-9]+(?:-[a-z0-9]+)*", text)):
            if cls.startswith(("wb-icon", "wb-i1")) or cls in hooks:
                continue
            if not re.search(re.escape("." + cls) + r"(?![A-Za-z0-9_-])", css) and f'"{cls}"' not in text.replace("class:", ""):
                missing.setdefault(cls, []).append(name)
    assert not missing, f"classes the modules build that style.css never names: {missing}"


def test_escape_leaves_a_draft_alone_and_leaving_the_inbox_keeps_a_card_whose_job_runs():
    floor = (INTERFACE / "js" / "views" / "floor.js").read_text(encoding="utf-8")
    assert re.search(r'a\.tagName === "TEXTAREA" \|\| a\.tagName === "INPUT"[^\n]*\n?\s*\)? ?return|a\.tagName === "TEXTAREA"[^\n]*return;', floor), \
        "Escape does nothing while the person types in a field"
    assert "!inbox.busy()" in floor, "the Inbox is reset only when no card has a request in flight"
    inbox = (INTERFACE / "js" / "floor" / "inbox.js").read_text(encoding="utf-8")
    cards = (INTERFACE / "js" / "floor" / "cards.js").read_text(encoding="utf-8")
    assert "isBusy()" in inbox and "isBusy()" in cards


# --- the Control room (WP-9.5): what it calls, and that every class it uses is drawn by the stylesheet ---------------------------


def control_modules():
    return sorted((INTERFACE / "js" / "views").glob("control*.js"))


def client_functions():
    """{function name: (method, path template)} of every exported function of the client that makes one call."""
    source = CLIENT.read_text(encoding="utf-8")
    out = {}
    for found in re.finditer(r"export (?:async )?function (\w+)\([^)]*\)\s*\{\s*return send\(\s*\"(GET|POST)\"\s*,\s*(?:\"|`)([^\"`]*)", source):
        out[found.group(1)] = (found.group(2), found.group(3))
    return out


def test_the_control_room_calls_only_the_four_reads_it_needs_and_each_is_a_get_route_of_the_service():
    files = control_modules()
    assert len(files) >= 6, "the Control room's modules are there"
    used = set()
    for path in files:
        used |= set(re.findall(r"\bapi\.(\w+)\(", path.read_text(encoding="utf-8")))
    assert used == {"skills", "costs", "connections", "agents"}, f"the Control room reads skills, costs, connections and agents: {sorted(used)}"
    functions = client_functions()
    routes = [(r["method"], shape(r["pattern"]), r) for r in service.ROUTES]
    for name in sorted(used):
        method, template = functions[name]
        assert method == "GET", f"api.{name} is a read"
        found = [r for m, s, r in routes if m == method and s == shape(template)]
        assert found, f"api.{name} calls {template}, which is not a route of the service"
        assert found[0]["pattern"].rsplit("/", 1)[-1] == name, f"api.{name} is the route of the operation of the same name"
    assert "since" in re.search(r"export function costs\([^)]*\)", CLIENT.read_text(encoding="utf-8")).group(0), "the Costs tab sends the date through the client's one query"
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"\bfetch\(|XMLHttpRequest|\bEventSource\b|\bsendBeacon\b", text), f"{path.name} has a second way to reach the service"
        assert not re.search(r"\bapi\.(?:%s)\(" % "|".join(sorted(["answer", "release", "approve", "reject", "request", "route", "cancel", "retry", "handOver", "verdict", "setMode", "say", "sync", "dispatch"])), text), f"{path.name} writes"


def test_every_wb_class_the_control_room_builds_is_a_rule_of_the_stylesheet():
    css = (INTERFACE / "style.css").read_text(encoding="utf-8")
    defined = set(re.findall(r"\.(wb-[a-z0-9-]+)", css))
    markers = {"is-open", "is-wide", "is-selected"}  # state words, not classes of their own
    for path in control_modules():
        text = path.read_text(encoding="utf-8")
        for group in re.findall(r"class: `?\"?([^\"`]+)[\"`]", text):
            for name in re.findall(r"\bwb-[a-z0-9-]+", group.split("${")[0]):
                if name.endswith("-"):
                    continue
                assert name in defined or name in markers, f"{path.name} builds the class {name}, which style.css does not draw"
    # the three tab words the hash carries are the router's, and the page reaches the screen from its one router
    main = (INTERFACE / "js" / "main.js").read_text(encoding="utf-8")
    assert 'import { createControlView } from "./views/control.js";' in main and 'route.screen === "control"' in main
    model = (INTERFACE / "js" / "views" / "control-model.js").read_text(encoding="utf-8")
    assert re.search(r'TABS = Object\.freeze\(\[\["skills", "Skills"\], \["costs", "Costs"\], \["connections", "Connections"\]\]\)', model)
