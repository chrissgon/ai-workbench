"""Tests of the page's live sync (WP-9.13): the watcher that asks the service for the change signal every second while the
tab is visible and reloads when it moves, the reload that every screen takes (the reads each view makes on a change), the
reload after any write the page sends, and the forced read of the snapshot. No browser and no model: the modules run
under Node with a fake clock, a fake document and a fake `fetch`, so what each screen asks the service is checked
(the paths, their number) without a service. The served page was looked at in a browser pane by the package's report.

Run: uv run --with pytest==9.1.1 pytest runtime/tests/test_interface_live.py
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import standin_tree as st
from test_interface_control import FAKE_DOM as CONTROL_DOM
from test_interface_floor import FAKE_DOM as FLOOR_DOM
from test_interface_lobby import VIEW_EXTRA

INTERFACE = st.REPO / "interface"
JS = INTERFACE / "js"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node is not installed: the modules are tested only by their text")
P = "0123456789ab"


def run_node(tmp_path: Path, body: str, dom: str | None = None) -> dict:
    """Run `body` (an ES module that prints one JSON line) with Node and return what it printed."""
    script = tmp_path / "check.mjs"
    script.write_text(body.replace("@JS@", JS.as_uri()).replace("@FAKE@", (tmp_path / "fake-dom.mjs").as_uri()), encoding="utf-8")
    (tmp_path / "fake-dom.mjs").write_text(dom or "", encoding="utf-8")
    done = subprocess.run([NODE, str(script)], capture_output=True, text=True, timeout=90)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout.strip().splitlines()[-1])


# --- the watcher: a fake clock ----------------------------------------------------------------------------------------------

CLOCK = r"""
// A clock that runs the timers due by hand, and lets the promises they start settle before it goes on.
export function makeClock() {
  let at = 0;
  let next = 1;
  const timers = new Map();
  const flush = async () => { for (let i = 0; i < 25; i++) await Promise.resolve(); };
  return {
    now: () => at,
    setTimer: (fn, ms) => { const id = next++; timers.set(id, { fn, due: at + ms }); return id; },
    clearTimer: (id) => { timers.delete(id); },
    pending: () => timers.size,
    async advance(ms) {
      const end = at + ms;
      await flush();
      for (;;) {
        const due = [...timers.entries()].filter(([, t]) => t.due <= end).sort((a, b) => a[1].due - b[1].due || a[0] - b[0])[0];
        if (!due) break;
        at = Math.max(at, due[1].due);
        timers.delete(due[0]);
        due[1].fn();
        await flush();
      }
      at = end;
      await flush();
    },
  };
}
"""

WATCH = CLOCK + r"""
import { createWatcher, coalesce } from "@JS@/watch.js";

function rig(options = {}) {
  const clock = makeClock();
  const log = { reads: [], reloads: [] };
  const state = { key: "1", hidden: false, fail: null, latency: 0 };
  const watcher = createWatcher({
    read: async () => {
      log.reads.push(clock.now());
      if (state.latency) await new Promise((resolve) => clock.setTimer(resolve, state.latency));
      if (state.fail) throw state.fail;
      return state.key;
    },
    reload: async (reason) => { log.reloads.push([clock.now(), reason]); watcher.reloaded(); },
    hidden: () => state.hidden,
    setTimer: clock.setTimer, clearTimer: clock.clearTimer, now: clock.now, ...options,
  });
  return { clock, log, state, watcher };
}

const out = {};

// 1. one read at once (the baseline), then one every second, and no reload while the number does not move
{
  const { clock, log, watcher } = rig();
  watcher.start();
  await clock.advance(0);
  await clock.advance(5000);
  out.cadence = { reads: log.reads, reloads: log.reloads };
  watcher.stop();
}
// 2. the number moves: one reload, at the read that saw it, and none after it
{
  const { clock, log, state, watcher } = rig();
  watcher.start();
  await clock.advance(2500);
  state.key = "2";
  await clock.advance(1000);
  const afterChange = log.reloads.map((r) => r[1]);
  await clock.advance(4000);
  out.change = { afterChange, total: log.reloads.length, reason: log.reloads[0] && log.reloads[0][1] };
  watcher.stop();
}
// 3. hidden: no read, no timer; visible again: one reload at once, then the cadence goes on, and a change made while hidden is not reloaded twice
{
  const { clock, log, state, watcher } = rig();
  watcher.start();
  await clock.advance(1000);
  const before = log.reads.length;
  state.hidden = true;
  watcher.visibilityChanged();
  const timersWhileHidden = clock.pending();
  await clock.advance(120000);
  const readsWhileHidden = log.reads.length - before;
  state.key = "9";
  state.hidden = false;
  watcher.visibilityChanged();
  await clock.advance(0);
  const reloadsOnReturn = log.reloads.map((r) => r[1]);
  const readsAfterReturn = log.reads.length;
  await clock.advance(3000);
  out.hidden = { timersWhileHidden, readsWhileHidden, reloadsOnReturn, reloadsAfter: log.reloads.length, moreReads: log.reads.length - readsAfterReturn };
  watcher.stop();
}
// 4. the safety net: 30 s with no reload at all is one full reload; a reload of any other cause starts the 30 s again
{
  const { clock, log, state, watcher } = rig();
  watcher.start();
  await clock.advance(29000);
  const early = log.reloads.length;
  await clock.advance(2000);
  const first = log.reloads.map((r) => [r[0], r[1]]);
  await clock.advance(20000);
  state.key = "2";                         // a change at about 51 s resets the clock of the net
  await clock.advance(1000);
  await clock.advance(25000);
  const quiet = log.reloads.length;
  await clock.advance(6000);
  out.safety = { early, first, quiet, last: log.reloads.slice(-1)[0][1], total: log.reloads.length };
  watcher.stop();
}
// 5. a read that fails: one reload so that the page says so, the next read after 10 s, and a reload when it answers again
{
  const { clock, log, state, watcher } = rig();
  watcher.start();
  await clock.advance(1000);
  state.fail = Object.assign(new Error("down"), { name: "ApiError", status: 0 });
  await clock.advance(1000);
  const failedAt = log.reads.slice(-1)[0];
  await clock.advance(9000);
  const between = log.reads.filter((t) => t > failedAt && t < failedAt + 10000).length;
  state.fail = null;
  await clock.advance(1000);
  out.failing = { reloads: log.reloads.map((r) => r[1]), between, nextAt: log.reads.filter((t) => t > failedAt)[0] - failedAt };
  watcher.stop();
}
// 6. the token was refused: the client already sent the page back to the prompt, so the watcher stops for good
{
  const { clock, log, state, watcher } = rig();
  watcher.start();
  await clock.advance(1000);
  state.fail = Object.assign(new Error("no"), { name: "ApiError", status: 401, unauthorized: true });
  await clock.advance(1000);
  const reads = log.reads.length;
  await clock.advance(60000);
  out.unauthorized = { reloads: log.reloads.length, moreReads: log.reads.length - reads, timers: clock.pending() };
}
// 7. a slow read does not overlap the next: the next waits a second after it ended
{
  const { clock, log, state, watcher } = rig();
  state.latency = 3000;
  watcher.start();
  await clock.advance(10000);
  out.slow = log.reads;
  watcher.stop();
}
// 8. stop: nothing is read afterwards
{
  const { clock, log, watcher } = rig();
  watcher.start();
  await clock.advance(1000);
  watcher.stop();
  const reads = log.reads.length;
  await clock.advance(60000);
  out.stopped = { moreReads: log.reads.length - reads, timers: clock.pending() };
}
// 8b. a reload that read the signal before its data rebases the watcher: the page's own write, answered and reloaded at once, is not
// reloaded a second time by the next read; a write after that read still is
{
  const { clock, log, state, watcher } = rig();
  const real = log;
  watcher.start();
  await clock.advance(2000);
  state.key = "2";                       // the page wrote; its reload read the signal ("2") before its data
  watcher.reloaded("2");
  await clock.advance(1000);
  const afterOwnWrite = real.reloads.length;
  state.key = "3";                       // a writer outside the page, after that
  await clock.advance(1000);
  out.rebase = { afterOwnWrite, afterOther: real.reloads.map((r) => r[1]) };
  watcher.stop();
}
// 9. coalesce: calls made while a run is in progress make one run more, and every caller waits for the last
{
  let running = 0;
  let max = 0;
  const runs = [];
  const gate = [];
  const run = coalesce(async (reason) => {
    running += 1;
    max = Math.max(max, running);
    runs.push(reason);
    await new Promise((resolve) => gate.push(resolve));
    running -= 1;
  });
  const done = [];
  const first = run("a").then(() => done.push("first"));
  const second = run("b").then(() => done.push("second"));
  const third = run("c").then(() => done.push("third"));
  await Promise.resolve();
  gate.shift()();
  await new Promise((r) => setTimeout(r, 0));
  const midway = { runs: runs.slice(), done: done.slice() };
  gate.shift()();
  await Promise.all([first, second, third]);
  out.coalesce = { midway, runs, max, done };
}
console.log(JSON.stringify(out));
"""


@needs_node
def test_the_watcher_reads_every_second_while_visible_and_reloads_only_when_the_number_moves(tmp_path):
    got = run_node(tmp_path, WATCH)
    assert got["cadence"]["reads"] == [0, 1000, 2000, 3000, 4000, 5000], "a baseline at once, then one read a second"
    assert got["cadence"]["reloads"] == [], "the number did not move: nothing is reloaded"
    assert got["change"]["afterChange"] == ["change"] and got["change"]["total"] == 1, "one reload, at the read that saw the new number"


@needs_node
def test_the_watcher_asks_nothing_while_hidden_and_reloads_once_on_return(tmp_path):
    hidden = run_node(tmp_path, WATCH)["hidden"]
    assert hidden["timersWhileHidden"] == 0 and hidden["readsWhileHidden"] == 0
    assert hidden["reloadsOnReturn"] == ["return"], "one reload on return, though the number moved while hidden"
    assert hidden["reloadsAfter"] == 1 and hidden["moreReads"] == 3, "the cadence goes on and the number read on return is the new baseline"


@needs_node
def test_the_watcher_makes_one_full_reload_after_thirty_quiet_seconds_and_a_reload_starts_the_count_again(tmp_path):
    safety = run_node(tmp_path, WATCH)["safety"]
    assert safety["early"] == 0, "nothing is reloaded before 30 s"
    assert safety["first"] == [[30000, "safety"]], "the net is one reload at 30 s"
    assert safety["last"] == "safety" and safety["quiet"] == 2, "a change reloads once; the net waits 30 s after it, not after the last net"
    assert safety["total"] == 3


@needs_node
def test_the_watcher_says_a_failed_read_backs_off_to_ten_seconds_and_reloads_when_the_service_is_back(tmp_path):
    failing = run_node(tmp_path, WATCH)["failing"]
    assert failing["reloads"] == ["unreachable", "recovered"], "the page is told once, and told again when it can read"
    assert failing["between"] == 0 and failing["nextAt"] == 10000, "the next read is ten seconds after the failed one"


@needs_node
def test_the_watcher_stops_for_good_when_the_token_is_refused_and_when_it_is_stopped_and_never_overlaps_a_slow_read(tmp_path):
    got = run_node(tmp_path, WATCH)
    assert got["unauthorized"] == {"reloads": 0, "moreReads": 0, "timers": 0}
    assert got["stopped"] == {"moreReads": 0, "timers": 0}
    assert got["slow"] == [0, 4000, 8000], "the next read waits a second after the last one ended"


@needs_node
def test_a_reload_that_read_the_signal_first_rebases_the_watcher_so_the_pages_own_write_is_not_reloaded_twice(tmp_path):
    got = run_node(tmp_path, WATCH)["rebase"]
    assert got["afterOwnWrite"] == 0, "the signal moved, but the reload that answered the write had read it"
    assert got["afterOther"] == ["change"], "a write by someone else after that read is still reloaded"


@needs_node
def test_calls_to_reload_made_during_a_reload_make_one_more_and_every_caller_waits_for_the_last(tmp_path):
    got = run_node(tmp_path, WATCH)["coalesce"]
    assert got["midway"]["runs"] == ["a", "c"] and got["midway"]["done"] == ["first"], "the second run is started when the first ends"
    assert got["runs"] == ["a", "c"] and got["max"] == 1, "never two at once; the second call is merged into the third"
    assert sorted(got["done"]) == ["first", "second", "third"]


# --- the client: the version reads and the reload after a write ------------------------------------------------------------------

CLIENT = r"""
import { setToken } from "@JS@/token.js";
import * as api from "@JS@/api.js";

setToken("t".repeat(40));
const seen = [];
let answer = { status: 200, body: {} };
let failNetwork = false;
globalThis.fetch = async (url, init) => {
  seen.push(`${init.method} ${url}`);
  if (failNetwork) throw new TypeError("failed to fetch");
  return { ok: answer.status < 400, status: answer.status, json: async () => answer.body };
};
const out = {};
const hooks = [];
api.onWrite((info) => hooks.push([info.method, info.status, seen.length]));

answer = { status: 200, body: { version: 3, changed_at: "x" } };
out.version = await api.version("0123456789ab");
out.versions = await api.versions();
out.afterReads = hooks.length;
answer = { status: 200, body: { request: 9 } };
await api.request("0123456789ab", { text: "hello" });
out.afterRequest = hooks.slice();
answer = { status: 202, body: { job: 4 } };
await api.route("0123456789ab", 9, {});
out.afterJob = hooks.slice(-1)[0];
answer = { status: 409, body: { error: "refused", message: "no" } };
try { await api.answer("0123456789ab", 5, { text: "x" }); } catch (e) { out.refused = e.status; }
out.afterRefused = hooks.slice(-1)[0];
failNetwork = true;
const before = hooks.length;
try { await api.request("0123456789ab", { text: "hello" }); } catch (e) { out.network = e.status; }
out.afterNetwork = hooks.length - before;
out.seen = seen;
console.log(JSON.stringify(out));
"""


@needs_node
def test_the_client_reads_the_version_and_calls_the_reload_after_a_write_answered_never_after_a_read(tmp_path):
    got = run_node(tmp_path, CLIENT)
    assert got["version"] == {"version": 3, "changed_at": "x"} and got["versions"] == {"version": 3, "changed_at": "x"}
    assert got["seen"][0] == f"GET /api/v1/projects/{P}/version" and got["seen"][1] == "GET /api/v1/versions"
    assert got["afterReads"] == 0, "a read is not a write"
    assert got["afterRequest"] == [["POST", 200, 3]], "called once the answer came back, not before the request left"
    assert got["afterJob"][:2] == ["POST", 202], "the start of a job is answered at once: the page reloads then and the job poll goes on"
    assert got["refused"] == 409 and got["afterRefused"][:2] == ["POST", 409], "a refusal says the state may have moved elsewhere: reload"
    assert got["network"] == 0 and got["afterNetwork"] == 0, "a request that got no answer changed nothing that is known"


# --- the snapshot: a forced read ignores the cached task bodies -------------------------------------------------------------------

DATA = r"""
import { setToken } from "@JS@/token.js";
import { emptySnapshot, refresh, versionKey } from "@JS@/data.js";

setToken("t".repeat(40));
const P = "0123456789ab";
const seen = [];
let runs = [{ id: 1 }];
let versionsNow = { b: { error: "not accepted" }, a: { version: 3, changed_at: "x" } };
globalThis.fetch = async (url, init) => {
  const path = url.replace("/api/v1", "");
  seen.push(path);
  let body = {};
  if (path === "/projects") body = { projects: [{ id: P, name: "northwind-shop", config: { accepted: true } }] };
  else if (path === `/projects/${P}/status`) body = { config: {}, pending: [], documents: [], requests: [{ id: 1, title: "t", state: "ready", flow: null, tasks: [{ id: 2, key: "a", title: "A", agent: "business", skill: "s", state: "running", note: null }] }] };
  else if (path === `/projects/${P}/agents`) body = { agents: [] };
  else if (path === "/versions") body = { versions: versionsNow };
  else if (path === `/projects/${P}/tasks/2`) body = { task: { id: 2, state: "running" }, runs, pending: [] };
  return { ok: true, status: 200, json: async () => body };
};
const out = {};
const first = await refresh(emptySnapshot(), P);
out.first = seen.filter((p) => p.endsWith("/tasks/2")).length;
runs = [{ id: 1 }, { id: 2 }];
seen.length = 0;
const cached = await refresh(first, P);
out.cached = { reads: seen.filter((p) => p.endsWith("/tasks/2")).length, runs: cached.tasks[Object.keys(cached.tasks)[0]].runs.length };
seen.length = 0;
const forced = await refresh(first, P, { force: true });
out.forced = { reads: seen.filter((p) => p.endsWith("/tasks/2")).length, runs: forced.tasks[Object.keys(forced.tasks)[0]].runs.length };
const key = await versionKey();
versionsNow = { b: { error: "not accepted" }, a: { version: 4, changed_at: "later" } };
out.key = [key, await versionKey(), await versionKey()];
console.log(JSON.stringify(out));
"""


@needs_node
def test_a_forced_read_of_the_snapshot_reads_the_running_task_again_though_its_state_is_the_same(tmp_path):
    got = run_node(tmp_path, DATA)
    assert got["first"] == 1
    assert got["cached"] == {"reads": 0, "runs": 1}, "unchanged behaviour: without force the body is reused while the state is the same"
    assert got["forced"] == {"reads": 1, "runs": 2}, "a change in the store is a change in the task's runs even when its state stays"
    first, second, third = got["key"]
    assert json.loads(first) == [["a", 3], ["b", "not accepted"]], "one string for every project, in a fixed order, the number or the sentence"
    assert first != second and second == third, "equal while nothing was written, different when one number moved"


# --- the views: what each reads when the page reloads --------------------------------------------------------------------------------
# Every screen takes the page's reload stamp in the data it is given; when the stamp moves it reads again everything it shows, and
# when it does not move (a redraw from a hash change, a tab) it reads only what it did before. A view is built under the fake document
# with a fake client below it (`fetch`), and the paths it asked for are the evidence.

VIEW_HEAD = r"""
import { FakeNode, settle, find, all } from "@FAKE@";
import { setToken } from "@JS@/token.js";
import * as router from "@JS@/router.js";

setToken("t".repeat(40));
globalThis.ResizeObserver = class { observe() {} disconnect() {} };
window.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
document.removeEventListener = (type, fn) => { document.listeners[type] = (document.listeners[type] || []).filter((f) => f !== fn); };
const P = "0123456789ab";
const NOW = new Date("2026-10-08T12:00:00Z");
const seen = [];
globalThis.fetch = async (url, init) => {
  const path = url.replace(`/api/v1/projects/${P}`, "");
  seen.push(`${init.method} ${path}`);
  let body = {};
  if (path.startsWith("/artifacts")) body = { artifacts: [{ path: "docs/notes/a.md", owner: null, agent: null, size: 4, modified_at: "2026-10-08T09:00:00Z", bound: false }], truncated: false };
  else if (path.startsWith("/tasks/")) body = { task: { id: Number(path.split("/")[2]), state: "running", title: "T" }, runs: [], pending: [] };
  else if (path.startsWith("/conversation")) body = { messages: [] };
  else if (path.startsWith("/skills")) body = { skills: [], checks: { measurement: "ok", image: "ok" } };
  else if (path.startsWith("/connections")) body = { classes: [], secrets: [], image: {} };
  else if (path.startsWith("/costs")) body = { since: "2026-09-08", rows: [], caps: [] };
  else if (path.startsWith("/agents")) body = { agents: [] };
  else if (path.startsWith("/flows")) body = { flows: [] };
  return { ok: true, status: 200, json: async () => body };
};
const agent = (name) => ({ name, pack: "x", enabled: true, mode: "supervised", acting_mode: "supervised", max_runs_per_day: 8, max_usd_per_day: 4, runs_today: 1, usd_today: 0.1, runs_without_cost: 0, queued: 0 });
const task = (id, state, agentName) => ({ id, key: `k${id}`, title: `Task ${id}`, skill: "s", state, note: null, agent: agentName });
const snapshot = { loaded: true, tasks: {}, projects: [{ id: P, name: "northwind-shop", config: { accepted: true } }], details: { [P]: {
  agents: [agent("planning"), agent("engineering"), agent("marketing")],
  status: { requests: [{ id: 2, title: "Sale page", state: "planned", flow: null, tasks: [task(4, "running", "engineering"), task(5, "waiting", "marketing")] }],
    pending: [{ id: 8, kind: "question", title: "Which colour?", task_id: 5, agent: "marketing", created_at: "2026-10-08T08:00:00Z", actions: ["answered"] }], documents: [] } } } };
const makeFrame = () => ({ el: new FakeNode("div"), main: new FakeNode("main"), sceneHost: new FakeNode("div"), track: { el: new FakeNode("div") }, noticeBox: new FakeNode("div"),
  insets: () => ({ left: 0, right: 0, top: 0, bottom: 0, pad: 1 }), isPhone: () => false, sceneUnavailable() {}, announce() {},
  acquireWorld: () => new Proxy({ flyTo: () => Promise.resolve(false), stats: () => ({}) }, { get: (t, k) => (k in t ? t[k] : () => {}) }), kpis: { el: new FakeNode("div") } });
const taken = () => { const got = seen.slice().sort(); seen.length = 0; return got; };
const out = {};
"""

FLOOR = VIEW_HEAD + r"""
import { createFloorView } from "@JS@/views/floor.js";

const route = (tail) => router.parse(`#/p/${P}/floor/engineering${tail}`);
let refreshed = 0;
const view = createFloorView(makeFrame(), { refresh: () => { refreshed += 1; } });
const show = (stamp, tail = "") => view.update({ snapshot, route: route(tail), now: NOW, reload: stamp });
show(1);
await settle();
out.first = taken();
show(1);
await settle();
out.sameStamp = taken();
show(2);
await settle();
out.reloaded = taken();
show(2, "/desk");
await settle();
out.onDesk = taken();
show(3, "/desk");
await settle();
out.deskReloaded = taken();
show(4, "/inbox");
await settle();
out.inboxReloaded = taken();
view.dispose();
console.log(JSON.stringify(out));
"""

BUILDING = VIEW_HEAD + r"""
import { createBuildingView } from "@JS@/views/building.js";

const view = createBuildingView(makeFrame(), { refresh: () => {} });
const route = router.parse(`#/p/${P}`);
const show = (stamp) => view.update({ snapshot, route, now: NOW, reload: stamp });
show(1);
await settle();
out.first = taken();
show(1);
await settle();
out.sameStamp = taken();
show(2);
await settle();
out.reloaded = taken();
view.dispose();
console.log(JSON.stringify(out));
"""

LOBBY = VIEW_HEAD + r"""
import { createLobbyView } from "@JS@/views/lobby.js";

const route = (tail) => router.parse(`#/p/${P}/lobby${tail}`);
const view = createLobbyView(makeFrame(), { project: P, onChanged: async () => {} });
const show = (stamp, tail = "") => view.update({ snapshot, route: route(tail), now: NOW, projectName: "northwind-shop", reload: stamp });
show(1);
await new Promise((r) => setTimeout(r, 200));
out.first = taken();
show(1);
await settle();
out.sameStamp = taken();
show(2);
await new Promise((r) => setTimeout(r, 200));
out.reloaded = taken();
show(3, "/desk");
await new Promise((r) => setTimeout(r, 200));
out.deskReloaded = taken();
await new Promise((r) => setTimeout(r, 11000));      // the old idle poll was every ten seconds
out.idle = taken();
view.dispose();
console.log(JSON.stringify(out));
process.exit(0);
"""

CONTROL = r"""
import { FakeNode, has, settle } from "@FAKE@";
import { setToken } from "@JS@/token.js";
import { createControlView } from "@JS@/views/control.js";

setToken("t".repeat(40));
const seen = [];
globalThis.fetch = async (url, init) => {
  const path = new URL(url, "http://127.0.0.1").pathname.replace("/api/v1/projects/aaaaaaaaaaaa/", "");
  seen.push(`${init.method} ${path}`);
  const bodies = { skills: { skills: [], checks: { measurement: "ok", image: "ok" } }, costs: { since: "2026-09-08", rows: [], caps: [] },
    agents: { agents: [] }, connections: { classes: [], secrets: [], image: {} } };
  return { ok: true, status: 200, json: async () => bodies[path] || {} };
};
const taken = () => { const got = seen.slice().sort(); seen.length = 0; return got; };
const frame = { main: new FakeNode("main"), sceneHost: new FakeNode("div"), noticeBox: new FakeNode("div"), insets: () => ({}), sceneUnavailable() {} };
const view = createControlView(frame);
const state = (stamp, tab) => ({ loaded: true, known: true, accepted: true, projectId: "aaaaaaaaaaaa", tab, reload: stamp });
const out = {};
view.update(state(1, "skills"));
await settle();
out.first = taken();
view.update(state(1, "skills"));
await settle();
out.sameStamp = taken();
view.update(state(2, "skills"));
await settle();
out.reloadedOnSkills = taken();
view.update(state(3, "connections"));
await settle();
out.reloadedOnConnections = taken();
view.update(state(4, "costs"));
await settle();
out.reloadedOnCosts = taken();
document.fireVisible();
await settle();
out.visible = taken();
view.dispose();
console.log(JSON.stringify(out));
"""


@needs_node
def test_the_floor_reads_the_current_tasks_body_and_the_documents_again_when_the_page_reloads_and_not_otherwise(tmp_path):
    got = run_node(tmp_path, FLOOR, FLOOR_DOM + VIEW_EXTRA)
    task, docs = "GET /tasks/4", "GET /artifacts"
    assert got["first"] == sorted([task, docs]), "its first reads: the running task's body and the documents"
    assert got["sameStamp"] == [], "the stamp did not move (a redraw): nothing is read"
    assert got["reloaded"] == sorted([task, docs]), "a reload reads the current task's body and the documents again, whatever their age"
    assert got["onDesk"] == [], "a tab change reads nothing by itself"
    assert got["deskReloaded"] == sorted([task, docs]), "the same on the Desk"
    assert got["inboxReloaded"] == sorted([task, docs]), "and on the Inbox, whose cards are the snapshot's decisions and whose resolved lines are the bodies"


@needs_node
def test_the_building_reads_the_documents_again_when_the_page_reloads_and_not_otherwise(tmp_path):
    got = run_node(tmp_path, BUILDING, FLOOR_DOM + VIEW_EXTRA)
    assert got["first"] == ["GET /artifacts"] and got["sameStamp"] == []
    assert got["reloaded"] == ["GET /artifacts"], "the floors list is the snapshot's; the sheets and drawers are the documents"


@needs_node
def test_the_lobby_reads_the_conversation_the_request_bodies_and_the_documents_again_when_the_page_reloads_and_has_no_idle_poll(tmp_path):
    got = run_node(tmp_path, LOBBY, FLOOR_DOM + VIEW_EXTRA)
    conversation = [p for p in got["first"] if p.startswith("GET /conversation")]
    assert conversation, "the first read of the conversation"
    assert got["sameStamp"] == []
    reloaded = got["reloaded"]
    assert [p for p in reloaded if p.startswith("GET /conversation")], "a reload reads the conversation (above the newest message it holds)"
    assert "GET /tasks/2" in reloaded, "and the body of each request it shows: a request's runs and decisions move while its state does not"
    assert "GET /artifacts" in reloaded, "and the documents of the Desk"
    assert "GET /artifacts" in got["deskReloaded"], "the Desk's documents are read again on a reload while the Desk is open"
    assert got["idle"] == [], "no standing poll: eleven quiet seconds ask the service nothing"


@needs_node
def test_the_control_room_reads_the_open_tab_and_the_costs_again_when_the_page_reloads_not_every_tab(tmp_path):
    got = run_node(tmp_path, CONTROL, CONTROL_DOM)
    assert got["first"] == sorted(["GET skills", "GET costs", "GET agents", "GET connections"]), "unchanged: the first read is all three tabs"
    assert got["sameStamp"] == []
    assert got["reloadedOnSkills"] == sorted(["GET skills", "GET costs", "GET agents"]), "skills is 0.8 s of work and connections as much: only the tab that is open"
    assert got["reloadedOnConnections"] == sorted(["GET connections", "GET costs", "GET agents"])
    assert got["reloadedOnCosts"] == sorted(["GET costs", "GET agents"])
    assert got["visible"] == [], "the page reloads on return; the view does not read by itself"
