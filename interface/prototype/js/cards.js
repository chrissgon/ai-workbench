// Decision cards and the conversation: HTML over the scene. Buttons only show what they would call.
import { esc } from "./iso.js";
import { store, relTime } from "./data.js";
import { toast, wouldCall } from "./ui.js";

const LABEL = { approve: "Approve", reject: "Reject", release: "Release", answer: "Answer" };

function callFor(p, x, action, text) {
  const base = { project: p.id, pending_id: x.id };
  if (action === "approve") {
    if (x.kind === "effect") return wouldCall("approve", { ...base, sha256: x.effect.sha256 });
    if (x.kind === "plan") return wouldCall("approve", { ...base, sha256: x.plan.plan_sha256 });
    return wouldCall("approve", base);
  }
  if (action === "reject") return wouldCall("reject", base);
  if (action === "release") return wouldCall("release", base);
  return wouldCall("answer", { ...base, text: text || "(empty)" });
}

export function decisionCard(p, x) {
  const el = document.createElement("div");
  el.className = `dcard kind-${x.kind}`;
  const hasAnswer = x.actions.includes("answer");
  let extra = "";
  if (x.kind === "plan") {
    extra = `<div class="plan-tasks">${x.plan.tasks.map((t) => `<span class="t">${esc(t.skill)}</span>`).join("&rarr;")}</div>
      <div class="hint">Plan hash</div><div class="hash">${esc(x.plan.plan_sha256)}</div>`;
  }
  if (x.kind === "effect") {
    extra = `<div class="hint">The exact content that will go out</div><pre class="effect-content"></pre>
      <div class="hint">sha256 you approve</div><div class="hash">${esc(x.effect.sha256)}</div>
      <div class="hint">Today the runtime approves an effect from the terminal, with this hash. Any change to the content voids it.</div>`;
  }
  el.innerHTML = `<div class="head"><span class="kind k-${esc(x.kind)}">${esc(x.kind)}</span><span class="title">${esc(x.title)}</span></div>
    <div class="body">${esc(x.body)}</div>${extra}
    <div class="hint">#${x.id} · ${esc(x.agent)} · ${esc(relTime(x.created_at))}</div>
    <div class="actions">${hasAnswer ? '<input type="text" placeholder="Your answer or comment" aria-label="Answer text">' : ""}
      ${x.actions.map((a) => `<button class="btn small ${a === "reject" ? "danger" : a === "answer" ? "ghost" : ""}" data-a="${a}">${LABEL[a]}${a === "approve" && x.kind === "effect" ? " with hash" : ""}</button>`).join("")}</div>`;
  if (x.kind === "effect") el.querySelector(".effect-content").textContent = x.effect.content; // plain text
  el.querySelectorAll("button").forEach((b) => {
    b.onclick = () => toast(callFor(p, x, b.dataset.a, el.querySelector("input")?.value));
  });
  return el;
}

export function inboxCard(p, items) {
  const card = document.createElement("div");
  card.className = "card";
  card.id = "inbox";
  card.innerHTML = `<h3>Inbox <span class="count">${items.length}</span></h3>`;
  if (!items.length) card.insertAdjacentHTML("beforeend", '<div class="hint">Nothing waits for you on this floor.</div>');
  items.forEach((x) => card.append(decisionCard(p, x)));
  return card;
}

export function chatCard(p, chat) {
  const card = document.createElement("div");
  card.className = "card";
  card.innerHTML = `<h3>Conversation with the planning agent</h3><div class="chat"></div>
    <form class="composer"><input type="text" placeholder="A request, an answer, or /pending" aria-label="Message"><button class="btn small" type="submit">Send</button></form>`;
  const box = card.querySelector(".chat");
  const add = (m) => {
    const d = document.createElement("div");
    d.className = `msg ${m.from}`;
    const t = document.createElement("span");
    t.textContent = m.text; // plain text
    const s = document.createElement("small");
    s.textContent = `${m.from === "person" ? store.ws.person : "Atlas"} · ${m.at ? relTime(m.at) : "now"}`;
    d.append(t, s);
    box.append(d);
    if (m.plan_pending_id) {
      const plan = p.pending.find((x) => x.id === m.plan_pending_id);
      if (plan) { const wrap = document.createElement("div"); wrap.style.alignSelf = "stretch"; wrap.append(decisionCard(p, plan)); box.append(wrap); }
    }
    box.scrollTop = box.scrollHeight;
  };
  (chat?.messages || []).forEach(add);
  card.querySelector("form").onsubmit = (e) => {
    e.preventDefault();
    const input = card.querySelector("input");
    const text = input.value.trim();
    if (!text) return;
    add({ from: "person", text });
    toast(wouldCall("say", { project: p.id, text }));
    input.value = "";
  };
  return card;
}
