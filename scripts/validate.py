#!/usr/bin/env python3
"""Validate ai-workbench conventions.

Usage: python3 scripts/validate.py [--strict] [--json] [--spec]

Checks every skill under skills/ and every agent under agents/:
  - folder name equals frontmatter name; name is lowercase, hyphenated, no leading/trailing/double hyphen
  - prefix is one of the area prefixes; metadata.area is valid and consistent with the prefix
  - metadata.kind is capability or flow, and matches the flow- prefix
  - description is 1-1024 characters
  - SKILL.md is at most 500 lines
  - core files contain no harness names, paths or tool names
  - non-empty metadata.side_effects implies a "## Confirmation gate" section
  - every metadata.inputs path is some skill's metadata.outputs (warning unless --strict)
  - relative links in SKILL.md resolve
  - agent frontmatter keys are only name, description, metadata
  - english-only: no tracked text file contains Portuguese-specific diacritics or words, except
    on a line carrying `validate: allow english-only -- <reason>` or a path listed in
    .security-scan-allow with the rule english-only
  - private-term: when a local, git-ignored terms file exists (.private-terms at the repository root, or
    the path in WORKBENCH_PRIVATE_TERMS), no tracked text file contains any of its terms, except on a line
    carrying `validate: allow private-term -- <reason>` or in a path the file excludes. The file lists one
    term per line (case-insensitive; `re:<regex>` for a pattern; `!<path glob>` to exclude a path; `#`
    comments). It keeps a maintainer's own names, projects and accounts out of this shared repository.
  - eval-status (through evals/eval_status.py): a skills/<name>/evals/result.json that exists is valid JSON
    with the record's fields and `skill` equal to the folder name; the generated block between the eval-status
    markers in docs/inventory.md is up to date (fix: python3 evals/eval_status.py inventory --write); skills
    whose status is `stale` (the folder changed since the recorded pass) or `draft` (no passing, complete
    record) are reported as warnings, one line per status, and are errors with --strict; evals/eval-gate.json,
    the gate's configuration (models, adapters, threshold), has its fields
  - scripts/security_scan.py finds no secret, hidden text or unsafe script pattern (its errors
    and warnings are reported here as they are there)

Options:
  --strict   treat warnings as errors
  --json     print a JSON report to stdout (human-readable lines go to stderr either way)
  --spec     also run `skills-ref validate` on each skill if the tool is installed
  --help     show this text

Exit codes: 0 ok, 1 errors found, 2 usage error.
"""
import fnmatch
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
AGENTS = os.path.join(ROOT, "agents")
CORE_DIRS = ["skills", "agents", "shared", "contracts", "templates", "providers"]

PREFIX_TO_AREA = {
    "biz": "business",
    "product": "product",
    "brand": "brand",
    "design": "design",
    "eng": "engineering",
    "ops": "delivery",
    "mkt": "marketing",
    "ai": "ai",
    "core": "core",
    "asst": "assistant",  # optional area, excluded from the default pack
    "flow": None,  # flows declare the area they mostly live in, or "core" for cross-area
}
AREAS = {"business", "product", "brand", "design", "engineering", "delivery", "marketing", "ai", "core", "assistant"}
KINDS = {"capability", "flow"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_LINES = 500
AGENT_KEYS = {"name", "description", "metadata"}

# Patterns that mark a harness dependency inside the core. Product names are matched
# capitalized to avoid false positives on common words (a "cursor" in pagination).
HARNESS_PATTERNS = [
    r"\.claude/", r"\.cursor/", r"\.codex/", r"\.agents/", r"\.github/agents", r"\.github/skills",
    r"\bCLAUDE\.md\b", r"\$\{?CLAUDE_PLUGIN_ROOT\}?", r"\bClaude Code\b", r"\bCopilot\b",
    r"\bCursor\b", r"\bCodex\b", r"\bGemini CLI\b", r"\bOpenCode\b", r"\bCline\b",
]
HARNESS_RE = re.compile("|".join(HARNESS_PATTERNS))

# english-only: diacritics that do not occur in English (a with tilde, o with tilde, c with
# cedilla) and a few unambiguous Portuguese words, written as escapes so this file passes.
PORTUGUESE_WORDS = ["n\u00e3o", "voc\u00ea", "is" + "so", "p" + "ra", "est\u00e1", "tamb\u00e9m"]
PORTUGUESE_RE = re.compile(
    r"[\u00e3\u00f5\u00e7\u00c3\u00d5\u00c7]|(?<!\w)(?:" + "|".join(PORTUGUESE_WORDS) + r")(?!\w)",
    re.IGNORECASE)
# Group 1 is the reason: it must follow "-- " and cannot be only a comment terminator, or
# "english-only -->" would read ">" as the reason. Any other "--" tail matches without group 1,
# so the check reports a missing reason instead of plain Portuguese text.
ENGLISH_ALLOW_RE = re.compile(
    r"validate:\s*allow\s+english-only"
    r"(?:\s+--\s+(?!(?:-->|\*/)\s*$)(\S.*?)|\s*--.*?)?\s*(?:-->|\*/)?\s*$")


# --- minimal YAML subset parser (stdlib only) --------------------------------------
# Handles: `key: value`, `key: >`/`|` blocks, `key: [a, b]`, block lists, one nested map level.
def _scalar(v):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        return [] if not inner else [_scalar(x) for x in inner.split(",")]
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def parse_yaml_subset(text):
    lines = text.splitlines()
    return _parse_map(lines, 0, len(lines), 0)[0]


def _indent(s):
    return len(s) - len(s.lstrip(" "))


def _parse_map(lines, start, end, indent):
    out = {}
    i = start
    while i < end:
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            i += 1
            continue
        if _indent(raw) < indent:
            break
        if _indent(raw) > indent:
            raise ValueError(f"unexpected indentation at line {i + 1}: {raw!r}")
        if ":" not in raw:
            raise ValueError(f"expected key: value at line {i + 1}: {raw!r}")
        key, _, rest = raw.strip().partition(":")
        rest = rest.strip()
        if rest in (">", "|", ">-", "|-"):
            j = i + 1
            block = []
            while j < end and (not lines[j].strip() or _indent(lines[j]) > indent):
                block.append(lines[j].strip())
                j += 1
            sep = " " if rest.startswith(">") else "\n"
            out[key] = sep.join(b for b in block if b).strip()
            i = j
        elif rest == "":
            j = i + 1
            while j < end and not lines[j].strip():
                j += 1
            if j < end and lines[j].strip().startswith("- "):
                items = []
                while j < end and (not lines[j].strip() or lines[j].strip().startswith("- ")):
                    if lines[j].strip():
                        items.append(_scalar(lines[j].strip()[2:]))
                    j += 1
                out[key] = items
                i = j
            elif j < end and _indent(lines[j]) > indent:
                out[key], i = _parse_map(lines, j, end, _indent(lines[j]))
            else:
                out[key] = None
                i = j
        else:
            out[key] = _scalar(rest)
            i += 1
    return out, i


def load_yaml(text):
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text) or {}
    except ImportError:
        return parse_yaml_subset(text)


def split_frontmatter(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    if not content.startswith("---\n"):
        return None, content
    end = content.find("\n---", 4)
    if end == -1:
        return None, content
    return content[4:end], content[end + 4:]


# --- checks ------------------------------------------------------------------------
class Report:
    def __init__(self):
        self.errors, self.warnings = [], []

    def error(self, where, msg):
        self.errors.append({"where": where, "message": msg})

    def warn(self, where, msg):
        self.warnings.append({"where": where, "message": msg})


def check_skill(dirname, report, outputs_index):
    where = f"skills/{dirname}"
    path = os.path.join(SKILLS, dirname, "SKILL.md")
    if not os.path.isfile(path):
        report.error(where, "missing SKILL.md")
        return None
    fm_text, body = split_frontmatter(path)
    if fm_text is None:
        report.error(where, "SKILL.md must start with YAML frontmatter")
        return None
    try:
        fm = load_yaml(fm_text)
    except Exception as e:  # noqa: BLE001
        report.error(where, f"frontmatter is not valid YAML: {e}")
        return None

    name = fm.get("name")
    if name != dirname:
        report.error(where, f"frontmatter name {name!r} must equal folder name {dirname!r}")
    if not isinstance(name, str) or not NAME_RE.match(name or "") or len(name) > 64:
        report.error(where, "name must be 1-64 chars, lowercase a-z0-9 and single hyphens")

    prefix = (name or dirname).split("-")[0]
    if prefix not in PREFIX_TO_AREA:
        report.error(where, f"prefix {prefix!r} is not an area prefix; allowed: {sorted(PREFIX_TO_AREA)}")

    desc = fm.get("description") or ""
    if not (1 <= len(desc) <= 1024):
        report.error(where, f"description must be 1-1024 chars (got {len(desc)})")

    meta = fm.get("metadata") or {}
    if not isinstance(meta, dict):
        report.error(where, "metadata must be a map")
        meta = {}
    area, kind = meta.get("area"), meta.get("kind")
    if area not in AREAS:
        report.error(where, f"metadata.area {area!r} must be one of {sorted(AREAS)}")
    if kind not in KINDS:
        report.error(where, f"metadata.kind {kind!r} must be one of {sorted(KINDS)}")
    if prefix == "flow" and kind != "flow":
        report.error(where, "flow- prefix requires metadata.kind: flow")
    if prefix != "flow" and kind == "flow":
        report.error(where, "metadata.kind: flow requires the flow- prefix")
    expected_area = PREFIX_TO_AREA.get(prefix)
    if expected_area and area and area != expected_area:
        report.error(where, f"prefix {prefix}- implies area {expected_area!r}, got {area!r}")

    for key in ("inputs", "outputs", "requires", "side_effects"):
        if key in meta and meta[key] is not None and not isinstance(meta[key], list):
            report.error(where, f"metadata.{key} must be a list")

    with open(path, encoding="utf-8") as f:
        n_lines = sum(1 for _ in f)
    if n_lines > MAX_LINES:
        report.error(where, f"SKILL.md has {n_lines} lines; limit is {MAX_LINES}. Move depth to references/")

    if meta.get("side_effects") and "## Confirmation gate" not in body:
        report.error(where, "side_effects is non-empty but there is no '## Confirmation gate' section")
    if not meta.get("side_effects") and "## Confirmation gate" in body:
        report.warn(where, "has a Confirmation gate section but declares no side_effects")

    whole = fm_text + body
    if re.search(r"__[A-Z_]+__", whole):
        report.error(where, "template placeholders (__LIKE_THIS__) are still present")
    if "Delete this section" in body:
        report.error(where, "template instruction 'Delete this section...' is still present")

    for link in re.findall(r"\[[^\]]*\]\(([^)#\s]+)\)", body):
        if "://" in link:
            continue
        target = os.path.normpath(os.path.join(SKILLS, dirname, link))
        if not os.path.exists(target):
            report.error(where, f"link target does not exist: {link}")

    for out in meta.get("outputs") or []:
        outputs_index.setdefault(out, []).append(name or dirname)
    return {"name": name, "inputs": meta.get("inputs") or [], "where": where}


def check_inputs_chain(skills, outputs_index, report):
    for s in skills:
        for inp in s["inputs"]:
            if inp not in outputs_index:
                report.warn(s["where"], f"input {inp!r} is not produced by any skill's outputs")


def check_agent(filename, report):
    where = f"agents/{filename}"
    path = os.path.join(AGENTS, filename)
    fm_text, _ = split_frontmatter(path)
    if fm_text is None:
        report.error(where, "agent must start with YAML frontmatter")
        return
    try:
        fm = load_yaml(fm_text)
    except Exception as e:  # noqa: BLE001
        report.error(where, f"frontmatter is not valid YAML: {e}")
        return
    stem = filename[:-3]
    if fm.get("name") != stem:
        report.error(where, f"frontmatter name {fm.get('name')!r} must equal file stem {stem!r}")
    extra = set(fm) - AGENT_KEYS
    if extra:
        report.error(where, f"harness-specific keys belong in adapters/<harness>/overrides/: {sorted(extra)}")


def check_harness_names(report):
    for d in CORE_DIRS:
        base = os.path.join(ROOT, d)
        for dirpath, _, files in os.walk(base):
            for fn in files:
                if not fn.endswith((".md", ".json", ".yaml", ".yml", ".py", ".sh", ".txt")):
                    continue
                p = os.path.join(dirpath, fn)
                with open(p, encoding="utf-8", errors="ignore") as f:
                    for ln, line in enumerate(f, 1):
                        m = HARNESS_RE.search(line)
                        if m:
                            rel = os.path.relpath(p, ROOT)
                            report.error(f"{rel}:{ln}", f"core file references a harness: {m.group(0)!r}")


def load_scanner():
    spec = importlib.util.spec_from_file_location("security_scan", os.path.join(ROOT, "scripts", "security_scan.py"))
    scanner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scanner)
    return scanner


def check_english(report, root=ROOT):
    """english-only: tracked text files carry no Portuguese-specific diacritics or words.

    A line is exempt when it carries `validate: allow english-only -- <reason>`; a whole file
    when .security-scan-allow has `<path glob> english-only -- <reason>`.
    """
    scanner = load_scanner()
    entries, _ = scanner.load_allow_file(root)
    for path in sorted(scanner.list_files(root, None)):
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        if rel.startswith(".git/") or scanner.path_allowed(entries, rel, "english-only"):
            continue
        text = scanner.read_text(path)
        if text is None:
            continue
        for ln, line in enumerate(text.splitlines(), 1):
            m = PORTUGUESE_RE.search(line)
            if not m:
                continue
            allow = ENGLISH_ALLOW_RE.search(line)
            if allow and allow.group(1):
                continue
            if allow:
                report.error(f"{rel}:{ln}", "[english-only] the allow needs a reason: "
                             "validate: allow english-only -- <reason>")
                continue
            report.error(f"{rel}:{ln}", f"[english-only] Portuguese text {m.group(0)!r}; "
                         "every file is written in English (AGENTS.md principle 6)")


PRIVATE_ALLOW_RE = re.compile(r"validate:\s*allow\s+private-term(?:\s+--\s+(\S.*?))?\s*(?:-->|\*/)?\s*$")


def load_private_terms(root=ROOT):
    """Return (patterns, excluded path globs, the file's path) from the local terms file; no patterns when there
    is none."""
    path = os.environ.get("WORKBENCH_PRIVATE_TERMS") or os.path.join(root, ".private-terms")
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError:
        return [], [], path
    patterns, excluded = [], []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("!"):
            excluded.append(line[1:].strip())
        elif line.startswith("re:"):
            patterns.append(re.compile(line[3:], re.I))
        else:
            patterns.append(re.compile(re.escape(line), re.I))
    return patterns, excluded, os.path.abspath(path)


def check_private_terms(report, root=ROOT):
    """private-term: no tracked text file names what the local terms file lists (see the module docstring)."""
    patterns, excluded, terms_file = load_private_terms(root)
    if not patterns:
        return
    scanner = load_scanner()
    for path in sorted(scanner.list_files(root, None)):
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        if (rel.startswith(".git/") or os.path.abspath(path) == terms_file
                or any(fnmatch.fnmatch(rel, g) for g in excluded)):
            continue
        text = scanner.read_text(path)
        if text is None:
            continue
        for ln, line in enumerate(text.splitlines(), 1):
            hit = next((m for p in patterns for m in [p.search(line)] if m), None)
            if not hit:
                continue
            allow = PRIVATE_ALLOW_RE.search(line)
            if allow and allow.group(1):
                continue
            report.error(f"{rel}:{ln}", f"[private-term] {hit.group(0)!r} is listed in the local private terms; "
                         "write it generically, and keep the case in the project that uses it")


def load_eval_status():
    spec = importlib.util.spec_from_file_location("eval_status", os.path.join(ROOT, "evals", "eval_status.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_eval_status(report, root=ROOT):
    """eval-status: records are valid, the inventory block is current, stale and draft skills are warned about."""
    es = load_eval_status()
    by_status = {"stale": [], "draft": []}
    problems = es.gate_problems(root)
    if problems:
        report.error("evals/eval-gate.json", f"[eval-status] {'; '.join(problems)}")
    for name in es.skill_names(root):
        skill_dir = os.path.join(root, "skills", name)
        _, problems = es.load_record(skill_dir)
        if problems:
            report.error(f"skills/{name}/evals/result.json", f"[eval-status] {'; '.join(problems)}")
        status = es.skill_status(skill_dir)["status"]
        if status in by_status:
            by_status[status].append(name)
    try:
        if not es.inventory_current(root):
            report.error("docs/inventory.md", "[eval-status] the generated eval-status block is out of date: "
                         "run python3 evals/eval_status.py inventory --write")
    except ValueError as e:
        report.error("docs/inventory.md", f"[eval-status] {e}")
    if by_status["stale"]:
        report.warn("skills", f"[eval-status] {len(by_status['stale'])} skill(s) are stale, changed since their recorded "
                    f"eval pass; rerun their evals: {', '.join(by_status['stale'])}")
    if by_status["draft"]:
        report.warn("skills", f"[eval-status] {len(by_status['draft'])} skill(s) are draft, with no passing eval record "
                    f"(python3 evals/eval_status.py status): {', '.join(by_status['draft'])}")


def check_security(report):
    scanner = load_scanner()
    _, active, _ = scanner.scan(ROOT)
    for f in active:
        add = report.error if f["severity"] == "error" else report.warn
        add(f"{f['path']}:{f['line']}", f"[{f['rule']}] {f['message']} (see scripts/security_scan.py)")


def run_spec_validator(report):
    tool = shutil.which("skills-ref")
    if not tool:
        report.warn("scripts/validate.py", "--spec requested but skills-ref is not installed; skipped")
        return
    for d in sorted(os.listdir(SKILLS)):
        if os.path.isdir(os.path.join(SKILLS, d)):
            r = subprocess.run([tool, "validate", os.path.join(SKILLS, d)], capture_output=True, text=True)
            if r.returncode != 0:
                report.error(f"skills/{d}", f"skills-ref: {r.stdout.strip() or r.stderr.strip()}")


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    unknown = [a for a in argv if a not in ("--strict", "--json", "--spec")]
    if unknown:
        print(f"Error: unknown option(s) {unknown}. See --help.", file=sys.stderr)
        return 2
    strict, as_json, spec = "--strict" in argv, "--json" in argv, "--spec" in argv
    report = Report()
    outputs_index, skills = {}, []

    if os.path.isdir(SKILLS):
        for d in sorted(os.listdir(SKILLS)):
            if os.path.isdir(os.path.join(SKILLS, d)):
                s = check_skill(d, report, outputs_index)
                if s:
                    skills.append(s)
    check_inputs_chain(skills, outputs_index, report)
    if os.path.isdir(AGENTS):
        for fn in sorted(os.listdir(AGENTS)):
            if fn.endswith(".md"):
                check_agent(fn, report)
    check_harness_names(report)
    check_english(report)
    check_private_terms(report)
    check_eval_status(report)
    check_security(report)
    if spec:
        run_spec_validator(report)

    for e in report.errors:
        print(f"ERROR   {e['where']}: {e['message']}", file=sys.stderr)
    for w in report.warnings:
        print(f"WARNING {w['where']}: {w['message']}", file=sys.stderr)
    failed = bool(report.errors) or (strict and bool(report.warnings))
    summary = {
        "skills": len(skills),
        "errors": len(report.errors),
        "warnings": len(report.warnings),
        "ok": not failed,
    }
    if as_json:
        print(json.dumps({"summary": summary, "errors": report.errors, "warnings": report.warnings}, indent=2))
    else:
        print(json.dumps(summary))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
