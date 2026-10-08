// The Lobby (handoff lobby.md): the planning agent's floor. A room (lobby-scene.js) beside a 420 px panel whose Conversation tab
// holds the messages, each request's line and its decisions (the plan card under the message that produced it), and at the bottom
// the "New request" disclosure and the composer. The page decides nothing: it sends what the person typed (`say`, or `request`
// then `route`), reads `conversation` and `task` and draws what came. The conversation is read every 2 seconds while a job of
// this screen runs, never while the document is hidden, and again, with the request bodies, the documents and the planning agent's
// task bodies, whenever the page reloads because the store changed (the stamp `reload` of what `update` is given). The Inbox, Desk and Agent tabs are the
// Floor's modules (floor/inbox.js, desk-tab.js, viewer.js, agent-tab.js) given the planning agent: lobby-inbox.js, lobby-desk.js
// and lobby-agent.js hand them their data, and every write they send goes through floor/actions.js.

import * as api from "../api.js";
import { failureText } from "../cards/plan-rows.js";
import { h } from "../dom.js";
import * as fm from "../floor-model.js";
import { createPanel } from "../frame/panel.js";
import * as router from "../router.js";
import { createRequest, routeRequest, sendTurn, waitFor, worthSending } from "./lobby-actions.js";
import { createLobbyAgent } from "./lobby-agent.js";
import { createComposer } from "./lobby-composer.js";
import { createLobbyDesk, createLobbyViewer } from "./lobby-desk.js";
import { createForm } from "./lobby-form.js";
import { createLobbyInbox } from "./lobby-inbox.js";
import {
  NOT_ACCEPTED_TEXT, cancelCount, canvasLabel, inboxParts, isNamed, lastId, lobbyDecisions, mergeMessages, noticeFor, notRoutedNotice, placeBlocks,
  pollInterval, roomModel, signatureOf, tabOf, wantedBodies,
} from "./lobby-model.js";
import { createCancelDialog } from "./lobby-request.js";
import { mountLobbyScene } from "./lobby-scene.js";
import { createTabs } from "./lobby-tabs.js";
import { createThread } from "./lobby-thread.js";
import * as model from "../model.js";
import { worldModel } from "../world-model.js";

/**
 * Create the Lobby of `project` in `frame`. options: {project, onChanged(): Promise (the page reads the project again)}.
 * Returns {update({snapshot, route, now, projectName, reload}), dispose()}.
 */
export function createLobbyView(frame, { project, onChanged }) {
  const abort = new AbortController();
  const signal = abort.signal;
  let disposed = false;
  let messages = [];
  let loaded = false;
  let turn = null;                    // the job of a `say` that is running, or null
  const routing = new Set();          // request ids whose `route` job is running
  const chosenFlow = new Map();       // request id -> the flow chosen in the form (for "Route it" after a busy answer)
  const bodies = new Map();           // request id -> {sig, body}
  const reading = new Map();          // request id -> the read of its `task` body that is running
  let last = { snapshot: null, route: null, now: new Date(), projectName: "" };
  let notice = null;
  let timer = null;
  let readingConversation = false;
  let flowsAsked = false;
  let accepted = true;
  let again = false;                  // a read of the conversation was asked for while one was running
  let conversationRead = Promise.resolve();    // the read that is running, and the one more that was asked for
  let viewerWas = false;
  let lastOpened = null;              // the document the person opened last: the focus goes back to its row when the viewer closes
  let leftInbox = true;               // the Inbox was left since it was last drawn: a resolved card goes
  let reloaded = null;                // the page's reload stamp last seen: when it moves the store changed, and everything shown is read again
  let changes = 0;                    // how many times it moved: a read that began before the last move is not fresh when it ends

  // --- the pieces ---------------------------------------------------------------------------------------------------------
  const panel = createPanel({ title: "Lobby · Planning agent", subtitle: "", icon: "message-square", tone: "theme", width: "lobby" });
  panel.el.classList.add("wb-panel-lobby");
  const tabs = createTabs();
  const refresh = async () => {
    invalidate();
    await onChanged();
    await readConversation();
    await settled();      // the cards are drawn from the bodies read again before the caller goes on
  };
  const thread = createThread({
    api, project, signal, onChanged: refresh,
    onCancel: (request) => openCancel(request),
    onRoute: (request) => routeAgain(request), announce: (text) => frame.announce(text),
  });
  const waiting = h("p", { class: "wb-empty wb-lobby-waiting", hidden: true, text: NOT_ACCEPTED_TEXT });
  const conversationPanel = h("div", { class: "wb-lobby-tabpanel", role: "tabpanel", id: tabs.panelId("conversation"), "aria-labelledby": tabs.tabId("conversation") }, waiting, thread.el);
  // the Inbox, Desk and Agent tabs: the Floor's modules with the planning agent (lobby-inbox.js, lobby-desk.js, lobby-agent.js)
  const waitingLine = () => h("p", { class: "wb-empty-line wb-lobby-waiting", hidden: true, text: NOT_ACCEPTED_TEXT });
  const inbox = createLobbyInbox({ project, now: () => new Date(), refresh: () => { refresh(); } });
  const desk = createLobbyDesk({
    project, open: (path) => { lastOpened = path; window.location.hash = router.lobbyDeskHash(project, path); }, changed: () => { drawTabs(); drawRoom(); },
  });
  const agent = createLobbyAgent({ project, now: () => new Date(), refresh: () => { refresh(); }, changed: () => drawTabs() });
  const sections = { inbox: { waiting: waitingLine(), body: inbox.el }, desk: { waiting: waitingLine(), body: desk.el }, agent: { waiting: waitingLine(), body: agent.el } };
  const tabPanels = {};
  for (const [id, part] of Object.entries(sections)) {
    tabPanels[id] = h("div", { class: "wb-lobby-tabpanel wb-lobby-scroll", role: "tabpanel", id: tabs.panelId(id), "aria-labelledby": tabs.tabId(id), hidden: true }, part.waiting, part.body);
  }
  const form = createForm({ onCreate: (values) => create(values) });
  const composer = createComposer({ onSend: (text) => send(text) });
  // The keyboard order is the field, "Send", then the "New request" summary (lobby.md, Keyboard); the form is drawn above the field by the grid.
  const footer = h("div", { class: "wb-lobby-footer" }, composer.el, h("div", { class: "wb-form-scroll" }, form.el));
  const cancelDialog = createCancelDialog({ api, project, onChanged: refresh });
  panel.body.classList.add("wb-lobby-body");
  panel.body.append(conversationPanel, tabPanels.inbox, tabPanels.desk, tabPanels.agent);
  panel.el.insertBefore(tabs.el, panel.body);
  panel.el.append(footer);
  frame.main.append(panel.el, cancelDialog.el);
  const viewer = createLobbyViewer({ frame, panel: panel.el, project, onClose: () => { window.location.hash = router.lobbyHash(project, "desk"); } });
  const panelHead = panel.el.querySelector(".wb-panel-head");
  const scene = mountLobbyScene(frame, panel.el, { onDoor: () => { window.location.hash = router.controlHash(project); }, onSelect: (id) => openFromScene(id) });

  // --- reading ------------------------------------------------------------------------------------------------------------
  /** A body that was drawn stays drawn (a card keeps its note and its focus) but is read again: its signature no longer matches. */
  function invalidate() {
    for (const entry of bodies.values()) entry.sig = null;
  }

  function redraw() {
    if (disposed) return;
    const status = last.snapshot && last.snapshot.details[project] && last.snapshot.details[project].status;
    const requests = status ? status.requests || [] : [];
    const pending = status ? status.pending || [] : [];
    const held = {};
    for (const [id, entry] of bodies) held[id] = entry.body;
    thread.update({ messages, requests, pending, bodies: held, now: last.now, loading: !loaded, routing });
  }

  /**
   * Read the conversation after the newest message. A call made while a read runs asks for one more and returns the promise of the
   * read that is running, which ends when that one more has been done too: the caller (the end of a route) then knows the messages.
   */
  function readConversation() {
    if (disposed) return Promise.resolve();
    if (readingConversation) {
      again = true;
      return conversationRead;
    }
    conversationRead = readOnce();
    return conversationRead;
  }

  async function readOnce() {
    readingConversation = true;
    try {
      const got = await api.conversation(project, { after: lastId(messages), signal });
      const next = mergeMessages(messages, got.messages);
      const changed = next.length !== messages.length;
      messages = next;
      if (changed || !loaded) {
        loaded = true;
        redraw();
        drawTabs();
        drawRoom();
      }
    } catch (e) {
      if (e && e.name === "AbortError") return;
      // a project not accepted yet, or a service that did not answer: the frame says so; the next read tries again
    } finally {
      readingConversation = false;
    }
    if (again) {
      again = false;
      await readConversation();
    }
  }

  function schedule() {
    clearTimeout(timer);
    timer = null;
    if (disposed) return;
    const ms = pollInterval({ jobRunning: turn !== null || routing.size > 0, hidden: document.hidden });
    if (ms !== null) timer = setTimeout(tick, ms);
  }

  async function tick() {
    await readConversation();
    schedule();
  }

  function readBody(id, sig) {
    if (reading.has(id)) return;
    const began = changes;
    const run = (async () => {
      try {
        const body = await api.task(project, id, { signal });
        bodies.set(id, { sig: began === changes ? sig : null, body });     // null: the store changed meanwhile, read again below
        redraw();
      } catch (e) {
        if (e && e.name === "AbortError") return;
        if (e && e.status === 404) bodies.delete(id);
      } finally {
        reading.delete(id);
        if (began !== changes && !disposed) {
          const status = last.snapshot && last.snapshot.details[project] && last.snapshot.details[project].status;
          if (status) readBodies(status.requests || [], status.pending || []);
        }
      }
    })();
    reading.set(id, run);
  }

  /** Wait for the reads of request bodies that are running. */
  async function settled() {
    while (reading.size) await Promise.all([...reading.values()]);
  }

  function readBodies(requests, pending) {
    const placed = placeBlocks(messages, requests);
    for (const id of wantedBodies(placed, requests, pending)) {
      const request = requests.find((r) => r.id === id);
      const sig = signatureOf(request, pending);
      const held = bodies.get(id);
      if (!held || held.sig !== sig) readBody(id, sig);
    }
  }

  function drawRoom() {
    const status = last.snapshot && last.snapshot.details[project] && last.snapshot.details[project].status;
    const requestRow = status ? model.pickRequest(status, model.requestChoice(project)) : null;
    const room = roomModel({
      working: turn !== null || routing.size > 0, decisions: status ? lobbyDecisions(status).length : 0, hasMessages: messages.length > 0,
      accepted, request: requestRow, ready: Boolean(status), documents: desk.rows(),
    });
    const words = {
      tips: room.tips, board: room.board, door: true, doorTip: room.tips.door, state: room.state, window: room.window, decisions: room.decisions,
      sheets: room.sheets, drawers: room.drawers,
    };
    scene.update(worldModel(last.snapshot, last.now, { selectedId: project, focus: project, floor: "planning", room: words, ready: Boolean(status) }), canvasLabel(last.projectName, room));
  }

  function drawComposer() {
    composer.set({ sending: turn !== null, notice, disabled: !accepted });
  }

  /** A click in the room: the tray opens the Inbox, the desk the Desk tab, a sheet its document, the figure the Agent tab. */
  function openFromScene(id) {
    if (disposed) return;
    if (id === "tray") window.location.hash = router.lobbyHash(project, "inbox");
    else if (id === "desk") window.location.hash = router.lobbyHash(project, "desk");
    else if (id === "agent") window.location.hash = router.lobbyHash(project, "agent");
    else if (String(id).startsWith("sheet:")) window.location.hash = router.lobbyDeskHash(project, String(id).slice(6));
  }

  /** The Inbox, Desk and Agent tabs from what the page last read. Each module redraws only what changed. */
  function drawTabs() {
    if (disposed || !last.snapshot) return;
    const { snapshot, route, now } = last;
    const tab = tabOf(route);
    const detail = snapshot.details[project];
    const status = detail && detail.status;
    const model = agent.update({ snapshot, tab });
    desk.update({ tab, ready: Boolean(snapshot.loaded && accepted) });
    if (tab !== "inbox" && !leftInbox && !inbox.busy()) {      // a card whose job still runs keeps its state until it ends
      inbox.reset();
      leftInbox = true;
    }
    if (tab !== "inbox") return;
    leftInbox = false;
    if (!accepted) return;
    // Which plans have their card under a message is known only once the conversation was read: until then no plan is drawn as a card
    // (it would be drawn here, then be replaced by a line, and lose a note typed in it).
    const whole = status ? inboxParts(status, messages) : { cards: [], pointers: [] };
    const cards = loaded ? whole.cards : whole.cards.filter((item) => item.kind !== "plan");
    const withheld = whole.cards.length - cards.length;
    const parts = { cards, pointers: whole.pointers };
    const held = {};
    for (const [id, entry] of bodies) if (entry.body) held[id] = entry.body;
    const ids = [...(status ? status.requests || [] : []).map((r) => r.id), ...(model ? model.tasks.map((t) => t.id) : [])];
    inbox.update({
      cards: parts.cards, pointers: parts.pointers, requests: status ? status.requests || [] : [],
      resolved: fm.resolvedLines({ ...held, ...agent.bodies() }, ids, now), selected: route.pending, loading: !snapshot.loaded || (withheld > 0 && cards.length === 0),
    });
  }

  // --- what the person does -------------------------------------------------------------------------------------------------
  async function send(text) {
    if (!worthSending(text) || turn !== null || !accepted) return;
    notice = null;
    composer.set({ sending: true, notice: null, disabled: false });
    let started;
    try {
      started = await sendTurn(api, project, text, { signal });
    } catch (e) {
      if (e && e.name === "AbortError") return;
      notice = noticeFor(e, "post");        // the text stays in the field
      drawComposer();
      composer.focus();
      return;
    }
    composer.clear();
    turn = started.job;
    drawComposer();
    drawRoom();
    schedule();
    readConversation();                     // at once: the operation stores the person's line before the router runs
    let done = null;
    try {
      done = await waitFor(api, started, { signal });
    } catch (e) {
      if (e && e.name === "AbortError") return;
      notice = { title: "The turn failed", text: failureText(e) };
    }
    turn = null;
    if (done && done.state === "failed") {
      const failure = done.error || {};
      notice = noticeFor({ status: failure.status, word: failure.error, message: failure.message }, "job");
    }
    drawComposer();
    drawRoom();
    schedule();
    await refresh();
    if (!disposed) composer.focus();
  }

  async function followRoute(id, started) {
    routing.add(id);
    schedule();
    redraw();
    drawRoom();
    let done = null;
    let problem = null;
    try {
      done = await waitFor(api, started, { signal });
    } catch (e) {
      if (e && e.name === "AbortError") return null;
      problem = failureText(e);
    }
    routing.delete(id);
    if (done && done.state === "failed") problem = (done.error && done.error.message) || "The job failed.";
    const result = done && done.result ? done.result : null;
    if (!problem && result && result.routed === false) {
      problem = (result.failure && result.failure.reason) ? `The router could not run: ${result.failure.reason}.` : "The request could not be planned.";
    }
    notice = problem ? notRoutedNotice(id, problem) : null;
    drawComposer();
    drawRoom();
    schedule();
    await refresh();
    await settled();
    if (!problem && result && result.pending_id) frame.announce(`A decision waits for you: request ${id}`);
    if (!disposed && result && result.pending_id) {
      // a request a message names has its plan under that message; one made from the form has its card in the Inbox (OPEN-24)
      if (isNamed(messages, id)) thread.focusDecision(id, result.pending_id);
      else window.location.hash = router.lobbyHash(project, "inbox", result.pending_id);
    }
    return result;
  }

  async function create(values) {
    if (!worthSending(values.text)) {
      form.markEmpty();
      return;
    }
    notice = null;
    drawComposer();
    form.set({ creating: true, error: "", disabled: false });
    let result;
    try {
      result = await createRequest(api, project, values, { signal });
    } catch (e) {
      if (e && e.name === "AbortError") return;
      form.set({ creating: false, error: failureText(e), disabled: false });     // the typed text stays
      return;
    }
    if (values.flow) chosenFlow.set(result.request, values.flow);
    if (result.error) {
      notice = notRoutedNotice(result.request, failureText(result.error));
      drawComposer();
    } else {
      await followRoute(result.request, result.started);
    }
    form.reset();
    form.set({ creating: false, error: "", disabled: false });
    form.open(false);
    if (result.error) await refresh();
  }

  async function routeAgain(request) {
    if (routing.has(request.id)) return;
    notice = null;
    const outcome = await routeRequest(api, project, request.id, chosenFlow.get(request.id), { signal });
    if (outcome.error) {
      notice = notRoutedNotice(request.id, failureText(outcome.error));
      drawComposer();
      return;
    }
    await followRoute(request.id, outcome.started);
  }

  function openCancel(request) {
    cancelDialog.open(request, cancelCount(request));
  }

  // --- the page's poll ------------------------------------------------------------------------------------------------------
  function onVisibility() {
    if (document.hidden) {
      clearTimeout(timer);
      timer = null;
    } else {
      schedule();       // the busy poll of a job that still runs; the page reloads on return, which reads the rest
    }
  }
  document.addEventListener("visibilitychange", onVisibility);

  return {
    /** Called by the page after every read of the projects: snapshot (js/data.js), route (router.parse), now, the project's name. */
    update({ snapshot, route, now, projectName, reload }) {
      if (disposed) return;
      last = { snapshot, route, now, projectName: projectName || "" };
      if (reloaded !== null && reload !== reloaded) {     // the store changed: everything shown is stale, whatever its age
        changes += 1;
        invalidate();
        desk.reload();
        agent.reload();
        viewer.reload();
        readConversation();
      }
      reloaded = reload;
      const listed = (snapshot.projects || []).find((p) => p.id === project);
      const detail = snapshot.details[project];
      // Before the first read nothing is known: the screen is not declared unaccepted until the projects came.
      accepted = !snapshot.loaded || (Boolean(listed && listed.config && listed.config.accepted) && !(detail && detail.error && detail.error.status === 412));
      const status = detail && detail.status;
      const tab = tabOf(route);
      panel.el.querySelector(".wb-panel-sub").textContent = `${projectName || ""} · floor 0`;
      tabs.set({ project, selected: tab, counts: { inbox: status ? lobbyDecisions(status).length : 0 } });
      const onConversation = tab === "conversation";
      conversationPanel.hidden = !onConversation;
      conversationPanel.setAttribute("aria-labelledby", tabs.tabId("conversation"));
      for (const [id, part] of Object.entries(sections)) {
        tabPanels[id].hidden = tab !== id;
        part.waiting.hidden = accepted;
        part.body.hidden = !accepted;
      }
      // a document opened on the Desk takes the panel's place (a phone: a dialog)
      const showing = tab === "desk" && accepted && route.path ? viewer.show(route.path) : viewer.show(null);
      const inline = showing === "inline";
      panel.el.classList.toggle("is-viewing", inline);
      panelHead.hidden = inline;
      tabs.el.hidden = inline;
      panel.body.hidden = inline;
      footer.hidden = !onConversation || inline;
      if (viewerWas && !showing && lastOpened !== null) {     // the viewer was closed: the focus goes back to the row that opened it
        const back = lastOpened;
        setTimeout(() => desk.focusRow(back), 0);
      }
      viewerWas = Boolean(showing);
      waiting.hidden = accepted;
      thread.el.hidden = !accepted;
      form.set({ disabled: !accepted });
      drawComposer();
      if (accepted && !flowsAsked) {
        flowsAsked = true;
        api.flows(project, { signal }).then((got) => form.setFlows(got.flows)).catch(() => { flowsAsked = false; });
      }
      if (status) readBodies(status.requests || [], status.pending || []);
      redraw();
      drawTabs();
      drawRoom();
      if (!loaded && accepted) tick();
      else if (timer === null) schedule();
    },
    dispose() {
      disposed = true;
      abort.abort();
      clearTimeout(timer);
      document.removeEventListener("visibilitychange", onVisibility);
      viewer.dispose();
      desk.dispose();
      agent.dispose();
      scene.dispose();
      panel.el.remove();
      cancelDialog.el.remove();
    },
    stats() {
      return scene.stats();
    },
    /** What a click on an object of the room opens (also what a test presses): the tray, the cabinet, a sheet, the desk, the board, the figure. */
    open(id) {
      openFromScene(id);
    },
  };
}
