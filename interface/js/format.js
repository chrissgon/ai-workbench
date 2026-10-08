// Display words and numbers: pure functions with no document, so they run under a test.

export const KIND_WORDS = Object.freeze({
  plan: "Plan", question: "Question", review: "Review", effect: "Effect", acceptance: "Acceptance", your_document: "Your document",
});

/** The word a decision kind is shown with; an unknown kind is shown as it came. */
export function kindWord(kind) {
  return KIND_WORDS[kind] || (typeof kind === "string" && kind ? kind : "Decision");
}

/** "marketing" -> "Marketing": the display form of an agent's name (the planning agent is the Lobby). */
export function agentWord(name) {
  if (!name || name === "planning") return "Lobby";
  return name.charAt(0).toUpperCase() + name.slice(1);
}

/** "$3.82": a dollar amount with two decimals; a value that is not a number is "$0.00". */
export function dollars(value) {
  const n = typeof value === "number" && Number.isFinite(value) ? value : 0;
  return "$" + n.toFixed(2);
}

/** A number for a count; a value that is not a finite number is 0. */
export function count(value) {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

/** The share of `used` in `cap` between 0 and 1 for a meter; 0 when the cap is not a positive number. */
export function share(used, cap) {
  const c = count(cap);
  return c > 0 ? Math.max(0, Math.min(1, count(used) / c)) : 0;
}

/** The age of a stamp as "now", "12 min", "5 h" or "2 d"; the stamp is ISO text, `now` a Date. Unknown is "". */
export function age(stamp, now) {
  const then = Date.parse(typeof stamp === "string" ? stamp : "");
  if (!Number.isFinite(then)) return "";
  const seconds = Math.max(0, Math.floor((now.getTime() - then) / 1000));
  if (seconds < 60) return "now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} h`;
  return `${Math.floor(seconds / 86400)} d`;
}

/** The age spelled for a screen reader: "2 days", "5 hours", "12 minutes". */
export function ageWords(stamp, now) {
  const short = age(stamp, now);
  if (!short) return "";
  if (short === "now") return "just now";
  const [n, unit] = short.split(" ");
  const word = { min: "minute", h: "hour", d: "day" }[unit];
  return `${n} ${word}${n === "1" ? "" : "s"}`;
}

/** "14:02" in the browser's time zone for an ISO stamp, or "". */
export function clock(stamp) {
  const when = new Date(typeof stamp === "string" ? stamp : "");
  if (!Number.isFinite(when.getTime())) return "";
  return `${String(when.getHours()).padStart(2, "0")}:${String(when.getMinutes()).padStart(2, "0")}`;
}

/** "1 decision" / "5 decisions". */
export function decisions(n) {
  return `${n} decision${n === 1 ? "" : "s"}`;
}
