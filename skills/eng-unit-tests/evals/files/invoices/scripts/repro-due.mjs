// Reproduction for docs/engineering/plans/due-date-one-day-early.md.
// Run it once per time zone: TZ=America/Sao_Paulo node scripts/repro-due.mjs
import { dueLabel } from "../src/due.js";

for (const input of ["2026-09-25", "2026-09-25T00:00"]) {
  console.log(`dueLabel(${JSON.stringify(input)}) -> ${dueLabel(input)}`);
}
