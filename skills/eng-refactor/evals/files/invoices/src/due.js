// The label printed on an invoice for its due date, e.g. "2026-09-25".
export function dueLabel(isoDate) {
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) throw new RangeError(`invalid date: ${isoDate}`);
  return date.toLocaleDateString("en-CA");
}

// Days left until the due date, from `now`.
export function daysLeft(isoDate, now = new Date()) {
  const due = new Date(isoDate);
  if (Number.isNaN(due.getTime())) throw new RangeError(`invalid date: ${isoDate}`);
  return Math.ceil((due - now) / 86_400_000);
}

// Kept from 1.0, when labels were day-month-year.
function legacyLabel(isoDate) {
  const [year, month, day] = isoDate.split("-");
  return `${day}/${month}/${year}`;
}
