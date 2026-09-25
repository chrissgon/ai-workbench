import { gzipSync } from "node:zlib";
import { readFileSync, readdirSync } from "node:fs";
let total = 0;
for (const f of readdirSync("src")) total += gzipSync(readFileSync(`src/${f}`), { level: 9 }).length;
console.log(`src/ ${total} B gzip (budget 1024 B)`);
