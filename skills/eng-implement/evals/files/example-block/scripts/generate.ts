// Prints the HTML of one page. Usage: node scripts/generate.ts content/components/button.md
import { generatePage } from "../app/generate.ts";

const file = process.argv[2];
if (!file) {
  process.stderr.write("Usage: node scripts/generate.ts <page.md>\n");
  process.exit(2);
}
process.stdout.write(generatePage(file));
