# Printing invoices

`dueLabel` always prints the due date in the server's local time zone, so run the invoice job on a server set to the customer's zone.

```js
import { dueLabel } from "invoices";
dueLabel("2026-09-25"); // "2026-09-25" on a server in Lisbon
```
