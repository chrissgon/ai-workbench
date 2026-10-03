// Reads an invoice date string. Private to this module: not exported.
function toDate(isoDate) {
  return new Date(isoDate);
}

// The label printed on an invoice for its due date, e.g. "2026-09-25".
export function dueLabel(isoDate) {
  return toDate(isoDate).toLocaleDateString("en-CA");
}

// Days left until the due date, from `now`.
export function daysLeft(isoDate, now = new Date()) {
  return Math.ceil((toDate(isoDate) - now) / 86_400_000);
}
