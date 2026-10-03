import { openDatabase } from "@fennelkit/sqlite";

const db = openDatabase("data/books.sqlite");

export interface Expense {
  date: string; // YYYY-MM-DD
  payee: string;
  category: string;
  amount_cents: number;
}

/** The expenses of one month (YYYY-MM), in the order they were entered. */
export function expensesOfMonth(month: string): Expense[] {
  return db.all<Expense>(
    "SELECT date, payee, category, amount_cents FROM expenses WHERE substr(date, 1, 7) = ?",
    [month],
  );
}
