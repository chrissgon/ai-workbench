#!/usr/bin/env python3
"""Check a design document against its specification and its ADRs.

Usage: python3 check_design.py --spec <spec.md> --design <design.md> [--adr-dir <dir>]
                               [--report <check.json>] [--json]

--report <path> also writes the record of the run to that file, in the one shape every check script of the
workbench writes: "script", "date", "arguments" (each flag given except --report, as typed), "ok",
"summary" (the line a reply quotes), "errors", "warnings" and "counts" (spec_ids, covered, adrs,
adrs_failed). Each run overwrites it: the file holds the last run. It is written on every run that reaches
the check (exit 0 or 1), never on a usage error.

Checks:
  - every REQ-n, NFR-n, EDGE-n and AC-n id in the specification appears in the design
  - required design sections are present
  - every ADR referenced in the design (ADR-NNNN) exists in --adr-dir
  - every ADR file in --adr-dir has Status, Context, Options with at least two "### Option" entries,
    Decision and Consequences
  - the verification plan has at least one row per AC (an AC id inside the Verification plan section)
  - every item under "## Assumptions to verify before implementation" says how to verify it (a "Verify"
    part), unless the section holds only "none"
  - a warning lists the code identifiers the design and the ADRs name (a dotted name such as `Astro.props`,
    a camelCase name such as `getStaticPaths`, a call such as `glob()`, and in code blocks every call and
    method such as `z.object` or `.int`) that appear neither in the Assumptions section nor in the Sources
    section nor on a line with a URL; names the design itself defines (const, let, var, function, class,
    interface, type) are left out. It is a list to review, not a verdict: a name may be the project's own.

Prints JSON on one line (--json: indented): ok, summary, spec_ids, covered, adrs (one entry per ADR file with
its problems), errors, warnings. Usage errors go to stderr.
Exit codes: 0 ok, 1 problems, 2 usage error.
"""
import datetime
import glob
import json
import os
import re
import sys

DESIGN_SECTIONS = ["## Summary", "## Sources", "## Decisions", "## Components", "## Data or content model", "## Contracts",
                   "## Flows", "## Verification plan", "## Traceability"]
ADR_SECTIONS = ["## Context", "## Options", "## Decision", "## Consequences"]
ID_RE = re.compile(r"\b((?:REQ|NFR|EDGE|AC)-\d+)\b")

DEF_RE = re.compile(r"^\s*-\s*((?:REQ|NFR|EDGE|AC)-\d+)\s*(?:\([^)]*\))?:", re.M)


def defined_ids(spec_text):
    """Ids the specification defines (`- REQ-n:` lines); a definition line saying "withdrawn" is excluded.

    Ids that only appear as citations of another document (\"content-model spec REQ-10\") are not
    this specification's requirements and are not returned. Falls back to every id mentioned when
    the specification defines none in this form.
    """
    ids = set(DEF_RE.findall(spec_text))
    if not ids:
        return set(ID_RE.findall(spec_text))
    for line in spec_text.splitlines():
        m = DEF_RE.match(line)
        if m and "withdrawn" in line.lower():
            ids.discard(m.group(1))
    return ids



ASSUMPTIONS = "## Assumptions to verify before implementation"
FILE_EXT = {"md", "astro", "ts", "tsx", "js", "jsx", "mjs", "cjs", "json", "css", "scss", "html", "yaml", "yml", "py",
            "toml", "txt", "lock", "sh", "svg", "png", "jpg", "webp", "pdf", "csv", "xml", "vue", "svelte", "go", "rs", "rb",
            "java", "kt", "sql", "env", "config"}
KEYWORDS = {"if", "for", "while", "switch", "return", "function", "catch", "typeof", "await", "new", "import", "export",
            "async", "with", "super", "this", "case", "do", "else", "try", "throw", "yield", "delete", "void", "in", "of"}
FENCE_RE = re.compile(r"^```[^\n]*\n(.*?)^```", re.M | re.S)
SPAN_RE = re.compile(r"`([^`\n]+)`")
NAME_RE = re.compile(r"^\.?[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*(?:\(\))?$")
CALL_RE = re.compile(r"(?<![\w$.])([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*\(")
METHOD_RE = re.compile(r"[\)\]]\s*\.([A-Za-z_$][\w$]*)\s*\(")
DEFINED_RE = re.compile(r"\b(?:const|let|var|function|class|interface|type)\s+([A-Za-z_$][\w$]*)")


def is_code_name(span):
    """An inline code span that names code: dotted (not a file name), camelCase, or a call `name()`."""
    s = span.strip()
    if not NAME_RE.match(s):
        return False
    bare = s.lstrip(".").removesuffix("()")
    parts = bare.split(".")
    if len(parts) > 1:
        return parts[-1].lower() not in FILE_EXT
    return s.endswith("()") or bool(re.search(r"[a-z][A-Z]", bare))


def code_names(text):
    """{name: line} of the code identifiers a document names, outside fences and inside them."""
    names = {}
    fenced = FENCE_RE.findall(text)
    defined = set()
    for block in fenced:
        defined.update(DEFINED_RE.findall(block))
    prose = FENCE_RE.sub("", text)
    for line in prose.splitlines():
        for span in SPAN_RE.findall(line):
            if is_code_name(span):
                names.setdefault(span.strip().lstrip(".").removesuffix("()"), line)
    for block in fenced:
        for line in block.splitlines():
            for name in CALL_RE.findall(line):
                if name in KEYWORDS:
                    continue
                if name.split(".")[0] in defined:
                    if "." in name:
                        names.setdefault("." + name.split(".", 1)[1], line)
                    continue
                names.setdefault(name, line)
            for method in METHOD_RE.findall(line):
                names.setdefault("." + method, line)
    for name in list(names):
        if name.split(".")[0] in defined and "." not in name:
            del names[name]
    return names


def is_cited(name, where):
    """A name counts as cited when it, a dotted prefix of two or more parts, or (for a method) its bare name
    appears as a whole word in `where`."""
    bare = name.lstrip(".")
    parts = bare.split(".")
    candidates = {bare} | {".".join(parts[:i]) for i in range(2, len(parts))}
    if len(parts) == 1 or name.startswith("."):
        candidates.add(parts[-1])
    return any(re.search(r"(?<![\w$])" + re.escape(c) + r"(?![\w$])", where) for c in candidates)


def assumption_items(text):
    """The bullet items of the Assumptions section, each joined into one line."""
    items, cur = [], None
    for line in section(text, ASSUMPTIONS).splitlines():
        if re.match(r"^\s*[-*]\s+", line):
            if cur is not None:
                items.append(cur)
            cur = re.sub(r"^\s*[-*]\s+", "", line).strip()
        elif cur is not None and line.strip():
            cur += " " + line.strip()
    if cur is not None:
        items.append(cur)
    return items


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def section(text, heading):
    i = text.find(heading)
    if i == -1:
        return ""
    rest = text[i + len(heading):]
    m = re.search(r"^## ", rest, re.M)
    return rest[: m.start()] if m else rest


def main(argv):
    if not argv:
        print(__doc__, file=sys.stderr)
        print("Error: no arguments. See --help.", file=sys.stderr)
        return 2
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    spec = design = adr_dir = report = None
    as_json = "--json" in argv
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--spec", "--design", "--adr-dir", "--report") and i + 1 >= len(argv):
            print(f"Error: {a} needs a value.", file=sys.stderr)
            return 2
        if a == "--spec": spec = argv[i + 1]; i += 2
        elif a == "--design": design = argv[i + 1]; i += 2
        elif a == "--adr-dir": adr_dir = argv[i + 1]; i += 2
        elif a == "--report": report = argv[i + 1]; i += 2
        elif a == "--json": i += 1
        else:
            print(f"Error: unknown option {a!r}. See --help.", file=sys.stderr)
            return 2
    if not spec or not design or not os.path.isfile(spec) or not os.path.isfile(design):
        print("Error: --spec and --design must be existing files. See --help.", file=sys.stderr)
        return 2
    s, d = read(spec), read(design)
    errors, warnings = [], []
    spec_ids = sorted(defined_ids(s), key=lambda x: (x.split("-")[0], int(x.split("-")[1])))
    design_ids = set(ID_RE.findall(d))
    missing = [i for i in spec_ids if i not in design_ids]
    if missing:
        errors.append(f"ids from the spec not mentioned in the design: {missing}")
    for h in DESIGN_SECTIONS:
        if h not in d:
            errors.append(f"design lacks section {h!r}")
    plan = section(d, "## Verification plan")
    plan_acs = set(re.findall(r"\bAC-\d+\b", plan))
    spec_acs = [i for i in spec_ids if i.startswith("AC-")]
    unplanned = [a for a in spec_acs if a not in plan_acs]
    if unplanned:
        errors.append(f"acceptance criteria without a row in the verification plan: {unplanned}")
    referenced = sorted(set(re.findall(r"\bADR-(\d{4})\b", d)))
    adr_files = sorted(glob.glob(os.path.join(adr_dir, "*.md"))) if adr_dir and os.path.isdir(adr_dir) else []
    existing = {os.path.basename(f)[:4] for f in adr_files}
    for n in referenced:
        if n not in existing:
            errors.append(f"ADR-{n} referenced but no file {n}-*.md in {adr_dir or '(no --adr-dir)'}")
    adr_report = []
    for f in adr_files:
        t = read(f)
        probs = [h for h in ADR_SECTIONS if h not in t]
        if "- Status:" not in t:
            probs.append("Status line")
        n_opts = len(re.findall(r"^### Option", t, re.M))
        if n_opts < 2:
            probs.append(f"only {n_opts} option(s)")
        adr_report.append({"file": os.path.basename(f), "ok": not probs, "problems": probs})
        if probs:
            errors.append(f"{os.path.basename(f)}: {', '.join(probs)}")
    items = [i for i in assumption_items(d) if i.strip(" .").lower() != "none"]
    unverified = [i[:60] for i in items if not re.search(r"\bverif(y|ied|ication)\b", i, re.I)]
    if unverified:
        errors.append(f"assumptions that do not say how to verify them (a \"Verify:\" part): {unverified}")
    cited = section(d, ASSUMPTIONS) + "\n" + section(d, "## Sources")
    names = code_names(d)
    for f in adr_files:
        for name, line in code_names(read(f)).items():
            names.setdefault(name, line)
    unlisted = sorted(n for n, line in names.items()
                      if not is_cited(n, cited) and not re.search(r"https?://", line))
    if unlisted:
        warnings.append("code identifiers named in the design or the ADRs that neither the Assumptions section, "
                        f"the Sources section nor a URL on their line cites: {unlisted}")
    ok = not errors
    covered = len(spec_ids) - len(missing)
    adrs_failed = sum(1 for a in adr_report if not a["ok"])
    if ok:
        summary = f"check_design ok: {covered}/{len(spec_ids)} ids covered, {len(adr_report)} ADR(s) valid"
    else:
        summary = (f"check_design FAILED: {len(errors)} error(s); {covered}/{len(spec_ids)} ids covered, "
                   f"{adrs_failed} of {len(adr_report)} ADR(s) with problems")
    result = {"ok": ok, "summary": summary, "spec_ids": len(spec_ids), "covered": covered, "adrs": adr_report,
              "errors": errors, "warnings": warnings}
    if report:
        arguments = {"--spec": spec, "--design": design}
        if adr_dir is not None:
            arguments["--adr-dir"] = adr_dir
        if as_json:
            arguments["--json"] = True
        record = {"script": os.path.basename(__file__), "date": datetime.date.today().isoformat(),
                  "arguments": arguments, "ok": ok, "summary": summary, "errors": errors, "warnings": warnings,
                  "counts": {"spec_ids": len(spec_ids), "covered": covered, "adrs": len(adr_report),
                             "adrs_failed": adrs_failed}}
        try:
            with open(report, "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2)
                f.write("\n")
        except OSError as e:
            print(f"Error: cannot write the report: {e}", file=sys.stderr)
            return 2
    print(json.dumps(result, indent=2 if as_json else None))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
