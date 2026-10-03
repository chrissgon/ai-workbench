import { useFetch, useState } from "@fennelkit/web";
import { MonthPicker } from "@fennelkit/web/forms";

interface Expense {
  date: string;
  payee: string;
  category: string;
  amount_cents: number;
}

export default function ExpensesPage() {
  const [month, setMonth] = useState("2026-03");
  const expenses = useFetch<Expense[]>(`/expenses?month=${month}`) ?? [];
  return (
    <main>
      <h1>Expenses</h1>
      <MonthPicker value={month} onChange={setMonth} />
      <table>
        <thead>
          <tr><th>Date</th><th>Payee</th><th>Category</th><th>Amount</th></tr>
        </thead>
        <tbody>
          {expenses.map((e) => (
            <tr key={`${e.date}-${e.payee}-${e.amount_cents}`}>
              <td>{e.date}</td><td>{e.payee}</td><td>{e.category}</td><td>{(e.amount_cents / 100).toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
