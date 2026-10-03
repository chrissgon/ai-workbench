import { createRouter } from "@fennelkit/server";
import { expensesOfMonth } from "../store/expenses";

export const router = createRouter();

// The Expenses page lists one month at a time.
router.get("/expenses", (request, response) => {
  const month = String(request.query.month ?? "");
  if (!/^\d{4}-\d{2}$/.test(month)) {
    response.status(400).json({ error: "month must be YYYY-MM" });
    return;
  }
  response.json(expensesOfMonth(month));
});
