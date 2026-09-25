// invoices 1.2.0, as published, before the customer time-zone change.
export function dueLabel(isoDate) {
  const date = new Date(isoDate);
  return date.toLocaleDateString("en-CA");
}

export function daysLeft(isoDate, now = new Date()) {
  const due = new Date(isoDate);
  return Math.ceil((due - now) / 86_400_000);
}
