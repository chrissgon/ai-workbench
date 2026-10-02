# invoices

## dueLabel(isoDate, timeZone = "UTC")

Returns the due date as printed on the invoice, `YYYY-MM-DD`, in the IANA time zone `timeZone` (the customer's). The server's time zone does not change it.

## daysLeft(isoDate, now = new Date())

Whole days until the due date, rounded up.
