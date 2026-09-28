// Fails when a source file has a trailing space: the project's whole lint for now.
import { readdirSync, readFileSync } from "node:fs";
const bad = readdirSync("src").filter((f) => /[ \t]$/m.test(readFileSync(`src/${f}`, "utf8")));
if (bad.length) { console.error(`trailing spaces: ${bad.join(", ")}`); process.exit(1); }
console.log("lint ok");
