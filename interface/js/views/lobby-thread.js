// The conversation's log: the messages, oldest first (the person's on the right, the planning agent's on the left, each with
// its age), and under the message that produced a request that request's block. It is drawn by keys, not wholesale: a message
// is built once, a block again only when what it shows changed, so a poll that changed nothing touches no element and the focus
// and a typed note stay where they are. The message text is text, never markup.

import { h } from "../dom.js";
import { createBlock } from "./lobby-request.js";
import { EMPTY_TEXT, metaOf, nameOf, placeBlocks, signatureOf } from "./lobby-model.js";

/** The log. options: {api, project, signal, onChanged, onCancel, onRoute, announce}. Returns {el, update(state)}. */
export function createThread({ api, project, signal, onChanged, onCancel, onRoute, announce }) {
  const el = h("div", { class: "wb-thread", role: "log", "aria-live": "polite", "aria-label": "Conversation with the planning agent", tabindex: "0" });
  const messages = new Map();     // id -> {el, meta, message}
  const blocks = new Map();       // request id -> {el, sig, block}
  const empty = h("p", { class: "wb-empty", text: "" });

  function messageNode(message, now) {
    const meta = h("time", { class: "wb-msg-meta", datetime: message.created_at || false, title: message.created_at || false, text: metaOf(message, now) });
    const bubble = h("div", { class: `wb-bubble ${message.role === "user" ? "pui-soft pui-theme" : "wb-bubble-agent"}`, text: message.text });
    const node = h("div", { class: `wb-msg ${message.role === "user" ? "is-user" : "is-agent"}`, role: "article", "aria-label": nameOf(message, now) }, meta, bubble);
    return { el: node, meta, message };
  }

  return {
    el,
    /**
     * state: {messages, requests (status.requests), pending (status.pending), bodies ({[requestId]: task answer}), now,
     * loading, routing (a Set of request ids being routed)}.
     */
    update({ messages: list, requests, pending, bodies, now, loading, routing }) {
      const nearEnd = el.scrollHeight - el.scrollTop - el.clientHeight < 48;
      const placed = placeBlocks(list, requests);
      const desired = [];
      const byId = new Map((requests || []).map((r) => [r.id, r]));

      function blockFor(requestId, viaMessage) {
        const request = byId.get(requestId);
        if (!request) return null;
        const body = bodies[requestId] || null;
        const bodySig = body ? (body.pending || []).map((p) => `${p.id}:${p.status}:${p.resolution || ""}`).join(",") : "-";
        const open = (pending || []).filter((p) => p.task_id === requestId).length;
        const sig = `${signatureOf(request, pending)}|${bodySig}|${routing && routing.has(requestId) ? "r" : ""}|${viaMessage ? "m" : "t"}|${request.title}`;
        const held = blocks.get(requestId);
        if (held && held.sig === sig) return held.el;
        const block = createBlock({ api, project, request, body, open, now, signal, onChanged, onCancel, onRoute, announce, routing: routing && routing.has(requestId), viaMessage });
        blocks.set(requestId, { el: block.el, sig, block });
        return block.el;
      }

      for (const message of list) {
        let held = messages.get(message.id);
        if (!held) {
          held = messageNode(message, now);
          messages.set(message.id, held);
        } else {
          held.meta.textContent = metaOf(message, now);
          held.el.setAttribute("aria-label", nameOf(message, now));
        }
        desired.push(held.el);
        const request = placed.byMessage.get(message.id);
        if (request !== undefined) {
          const node = blockFor(request, true);
          if (node) desired.push(node);
        }
      }
      for (const request of placed.trailing) {
        const node = blockFor(request, false);
        if (node) desired.push(node);
      }
      for (const [id, held] of blocks) {
        if (!desired.includes(held.el)) blocks.delete(id);
      }
      empty.textContent = loading ? "Loading the conversation..." : EMPTY_TEXT;
      if (!list.length && !desired.length) desired.push(empty);
      desired.forEach((node, i) => {
        if (el.children[i] !== node) el.insertBefore(node, el.children[i] || null);
      });
      while (el.children.length > desired.length) el.lastElementChild.remove();
      if (nearEnd || (list.length && !el.dataset.scrolled)) {
        el.scrollTop = el.scrollHeight;       // the first draw with messages, and any draw while the person is at the end
        if (list.length) el.dataset.scrolled = "1";
      }
    },
    /** Move the focus to the title of a decision's card, when it is drawn. */
    focusDecision(requestId, decisionId) {
      const held = blocks.get(requestId);
      if (held) held.block.focusCard(decisionId);
    },
  };
}
