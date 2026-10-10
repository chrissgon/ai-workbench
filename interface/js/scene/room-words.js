// The words a room's three objects say when the pointer is on them (round 4, `floor.html` and `lobby.html`): the dark tooltip over the owl, the board and the bookcase. Pure: no three.js
// and no document. The owl names its agent and its state from the model's tip, and says where a click goes when it is asking something (R-31); the board counts its notes by state;
// the bookcase counts its documents.

/** What the owl's tooltip says: the agent and its state (the model's words), and `open the Inbox` when it asks something. */
export function agentTip(words, asks) {
  const base = words || "";
  return asks ? `${base}${base ? " · " : ""}open the Inbox` : base;
}

/** The board's tooltip: `Tasks · 1 running, 1 left`, counting the notes by state in the order done, running, left; none yet when it has none. */
export function tasksTip(notes) {
  const list = Array.isArray(notes) ? notes : [];
  const count = (state) => list.filter((n) => n === state).length;
  const parts = [[count("done"), "done"], [count("run"), "running"], [count("left"), "left"]].filter(([n]) => n > 0).map(([n, word]) => `${n} ${word}`);
  return parts.length ? `Tasks · ${parts.join(", ")}` : "Tasks · none yet";
}

/** The bookcase's tooltip: `Documents · 7`, or `Documents · none yet`; `Documents` while they are unread (`null`). */
export function documentsTip(count) {
  if (typeof count !== "number") return "Documents";
  return count > 0 ? `Documents · ${count}` : "Documents · none yet";
}

/** True when the owl is asking something: its agent waits and has a decision open, so a click on it goes to the Inbox. */
export function asking(floor) {
  return floor.state === "waiting" && floor.decisions > 0;
}
