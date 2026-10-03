// The label printed on an invoice for its due date, e.g. "2026-09-25".
export function dueLabel(isoDate) {
  const date = new Date(isoDate);
  return date.toLocaleDateString("en-CA");
}

// Days left until the due date, from `now`.
export function daysLeft(isoDate, now = new Date()) {
  const due = new Date(isoDate);
  return Math.ceil((due - now) / 86_400_000);
}
