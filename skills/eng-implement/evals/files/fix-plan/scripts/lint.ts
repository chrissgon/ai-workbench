// Dependency-free lint for the conventions in AGENTS.md. Usage: node scripts/lint.ts
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const ROOTS = ["app", "tests", "scripts"];

function walk(dir: string): string[] {
  let names: string[];
  try {
    names = readdirSync(dir);
  } catch {
    return [];
  }
  const files: string[] = [];
  for (const name of names.sort()) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) files.push(...walk(path));
    else if (path.endsWith(".ts")) files.push(path);
  }
  return files;
}

const files = ROOTS.flatMap(walk);
const problems: string[] = [];

for (const file of files) {
  const text = readFileSync(file, "utf8");
  if (!text.endsWith("\n")) problems.push(`${file}: missing final newline`);
  text.split("\n").forEach((line, index) => {
    const at = `${file}:${index + 1}`;
    if (line.includes("\t")) problems.push(`${at}: tab character`);
    if (/\s+$/.test(line)) problems.push(`${at}: trailing whitespace`);
    if (/^export default\b/.test(line)) problems.push(`${at}: default export (use named exports)`);
    const from = line.match(/\bfrom "(\.{1,2}\/[^"]+)"/);
    if (from && !/\.(ts|json)$/.test(from[1])) problems.push(`${at}: relative import without a file extension`);
    if (file.startsWith("app") && /\bconsole\.log\(/.test(line)) problems.push(`${at}: console.log under app/`);
  });
}

for (const problem of problems) process.stderr.write(problem + "\n");
process.stdout.write(`lint: ${files.length} files, ${problems.length} problems\n`);
process.exit(problems.length === 0 ? 0 : 1);
