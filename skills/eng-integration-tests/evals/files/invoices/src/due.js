// The label printed on an invoice for its due date, e.g. "2026-09-25".
// `timeZone` is the customer's IANA zone; without it the date is printed as written.
export function dueLabel(isoDate, timeZone = "UTC") {
  const date = new Date(`${isoDate}T12:00:00Z`);
  return new Intl.DateTimeFormat("en-CA", { timeZone }).format(date);
}

// Days left until the due date, from `now`.
export function daysLeft(isoDate, now = new Date()) {
  const due = new Date(isoDate);
  return Math.ceil((due - now) / 86_400_000);
}
