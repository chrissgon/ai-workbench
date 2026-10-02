#!/usr/bin/env python3
"""Validate ai-workbench conventions.

Usage: python3 scripts/validate.py [--strict] [--json] [--spec] [--flags]

Checks every skill under skills/ and every agent under agents/:
  - folder name equals frontmatter name; name is lowercase, hyphenated, no leading/trailing/double hyphen
  - prefix is one of the area prefixes; metadata.area is valid and consistent with the prefix
  - metadata.kind is capability or flow, and matches the flow- prefix
  - description is 1-1024 characters
  - SKILL.md is at most 500 lines
  - core files, packs/ included, contain no harness names, paths or tool names
  - non-empty metadata.side_effects implies a "## Confirmation gate" section: the heading on a line of its
    own, outside a code fence
  - every metadata.inputs path is some skill's metadata.outputs (warning unless --strict)
  - relative links resolve, with or without an anchor, in SKILL.md, in a skill's references/, in agents/,
    contracts/ and templates/ (a code fence or a code span holds an example and is not read; neither is a
    link to a place in the same file or one written with a placeholder)
  - agent frontmatter keys are only name, description, metadata
  - frontmatter is read by this file's own parser on every machine, whatever library is installed
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

Rules reported as warnings, one line per skill and rule, each starting with the rule's name in brackets.
They say what a skill or its cases still have to change; none reads a skill's score or band:
  - [meta-keys] metadata carries inputs, outputs, requires, side_effects and version; the frontmatter
    carries license
  - [requires-vocabulary] every metadata.requires value is a class of the table in contracts/environment.md
    (a class the table writes with a placeholder, publisher:<platform>, is legal as written or with a value)
  - [side-effects-vocabulary] every metadata.side_effects value is one of publish, send, schedule, deploy,
    create, push, dismiss
  - [description-when] the description says when to use the skill (it has the word "when")
  - [description-length] the description has at most 900 characters (every session loads every description)
  - [skill-tokens] SKILL.md has at most about 5,000 tokens (characters divided by 4)
  - [eval-cases-count] evals/evals.json holds at least two cases
  - [eval-keys] evals/evals.json has known keys only (top level: skill_name, evals, allow_web; a case: id,
    prompt, expected_output, files, assertions, grader_files, skills, setup, allow_web, workbench_files,
    absent_on_purpose, platforms, tags; an assertion is a text, or an object with `text` and `tags`, each
    tag being guard, guard:<effect> or format); skill_name equals the folder; every case has an id of its own
  - [eval-assertions-count] a case has at least three assertions
  - [eval-conditional-assertion] no assertion starts with "If": it holds whenever its condition is false
  - [eval-run-assertion] no assertion says a command "is run" with no word on what the grader can read
    (output that is quoted, printed or reported)
  - [eval-prompt-names-skill] no prompt names the skill under test
  - [eval-product-names] no eval case and no fixture names an AI product or a design tool
  - [skill-name] a backticked skill name in a skill's Markdown (outside evals/) is a built skill, or its line
    says "planned", or carries `validate: allow skill-name -- <reason>` (an invented example)
  - [routing-table] every built skill is in skills/core-orchestrator/references/routing.md, and a name in
    that table is built or marked (planned), never both
  - [test-file-names] test file names are unique across the folders scripts/test_dirs.py lists
A rule whose file is not in the tree being validated (the class table, the routing table, test_dirs.py) is
skipped and says so in a NOTE line on stderr, which counts as neither an error nor a warning.

Options:
  --strict   treat warnings as errors
  --json     print a JSON report to stdout (human-readable lines go to stderr either way)
  --spec     also run `skills-ref validate` on each skill if the tool is installed
  --flags    print as Markdown, instead of the summary, the skills each named warning rule lists (the
             content of docs/architecture/phase-c-flags.md)
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
CORE_DIRS = ["skills", "agents", "shared", "contracts", "templates", "providers", "packs"]

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

# --- the rules reported as warnings (see the module docstring) -----------------------
REQUIRED_META = ("inputs", "outputs", "requires", "side_effects", "version")  # area and kind are errors already
SIDE_EFFECTS = ("publish", "send", "schedule", "deploy", "create", "push", "dismiss")
DESCRIPTION_WARN = 900  # characters
TOKEN_WARN = 5000       # characters / 4
MIN_CASES, MIN_ASSERTIONS = 2, 3
EVALS_KEYS = {"skill_name", "evals", "allow_web"}
CASE_KEYS = {"id", "prompt", "expected_output", "files", "assertions", "grader_files", "skills", "setup",
             "allow_web", "workbench_files", "absent_on_purpose", "platforms", "tags"}
ASSERTION_KEYS = {"text", "tags"}
ASSERTION_TAG_RE = re.compile(r"^(?:guard|format|guard:[a-z][a-z0-9-]*)$")
CONDITIONAL_RE = re.compile(r"^\s*if\b", re.I)
IS_RUN_RE = re.compile(r"\b(?:is|are|was|were)\s+(?:re-?)?run\b", re.I)
VISIBLE_RE = re.compile(r"quot|output|print|report", re.I)
_PREFIXES = "|".join(PREFIX_TO_AREA)
SKILL_NAME_RE = re.compile(r"`((?:" + _PREFIXES + r")-[a-z0-9]+(?:-[a-z0-9]+)*)`")
SKILL_NAME_ALLOW_RE = re.compile(r"validate:\s*allow\s+skill-name\s+--\s+\S")
ROUTE_RE = re.compile(r"(?<![\w/.-])((?:" + _PREFIXES + r")-[a-z0-9]+(?:-[a-z0-9]+)*)(?![\w/.-])(\s*\(planned\))?")
ROUTER = "core-orchestrator"
ROUTING_TABLE = f"skills/{ROUTER}/references/routing.md"
CLASS_TABLE = "contracts/environment.md"
# AI products and design tools: a case that names one tests a product, not the class the skill requires.
# The names of harnesses are an error of their own (HARNESS_PATTERNS below).
PRODUCT_RE = re.compile(r"\b(Claude(?: Design)?|Anthropic|ChatGPT|OpenAI|GPT-\d[\w.]*|Gemini|Midjourney|DALL-E|"
                        r"Stable Diffusion|Figma(?: Make)?|Framer|Canva|Lovable)\b")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
GATE_HEADING_RE = re.compile(r"^## Confirmation gate[ \t]*$", re.M)

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
    """Frontmatter is read by the subset parser above on every machine: a library installed on one machine
    and not on another would read the same file in two ways."""
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
        self.errors, self.warnings, self.notes = [], [], []

    def error(self, where, msg):
        self.errors.append({"where": where, "message": msg})

    def warn(self, where, msg, rule=None):
        """A named rule's warning starts with [rule] and carries the name, so that --flags lists it by skill."""
        if rule:
            self.warnings.append({"where": where, "message": f"[{rule}] {msg}", "rule": rule})
        else:
            self.warnings.append({"where": where, "message": msg})

    def note(self, msg):
        """A rule skipped because its file is not in this tree: said, and counted as nothing."""
        self.notes.append(msg)


def strip_code(text):
    """The text with code fences and code spans blanked, line numbers kept: what they hold is an example."""
    out, fence = [], None
    for line in text.split("\n"):
        m = FENCE_RE.match(line)
        if fence is None and m:
            fence = m.group(1)
            out.append("")
        elif fence is not None:
            closes = m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and line.strip() == m.group(1)
            fence = None if closes else fence
            out.append("")
        else:
            out.append(re.sub(r"`[^`\n]*`", "``", line))
    return "\n".join(out)


def check_links(report, where, base_dir, text):
    """Every relative link of a Markdown text resolves from base_dir. The anchor is dropped before the check;
    a link to a place in the same file and a link written with a placeholder (<file>, __NAME__) are skipped."""
    for link in LINK_RE.findall(strip_code(text)):
        target = link.split("#", 1)[0]
        if "://" in link or link.startswith("mailto:") or not target or re.search(r"[<>{}]|__", target):
            continue
        if not os.path.exists(os.path.normpath(os.path.join(base_dir, target))):
            report.error(where, f"link target does not exist: {link}")


def check_doc_links(report, root=ROOT):
    """Links inside agents/, contracts/ and templates/. A skill template's links are read from the folder a
    skill made from it will have, skills/<name>/."""
    for d in ("agents", "contracts", "templates"):
        for dirpath, _, files in sorted(os.walk(os.path.join(root, d))):
            for fn in sorted(f for f in files if f.endswith(".md")):
                p = os.path.join(dirpath, fn)
                base = os.path.join(root, "skills", "_") if d == "templates" and fn.endswith(".SKILL.md") else dirpath
                with open(p, encoding="utf-8", errors="ignore") as f:
                    check_links(report, os.path.relpath(p, root).replace(os.sep, "/"), base, f.read())


def has_gate_heading(body):
    """The heading "## Confirmation gate" on a line of its own, outside a code fence."""
    return bool(GATE_HEADING_RE.search(strip_code(body)))


def load_classes(report, root=ROOT):
    """The requirement classes of the table in contracts/environment.md (first column, backticked); None, with
    a note, when the contract is not in this tree."""
    path = os.path.join(root, CLASS_TABLE)
    if not os.path.isfile(path):
        report.note(f"[requires-vocabulary] skipped: {CLASS_TABLE} is not in this tree")
        return None
    with open(path, encoding="utf-8") as f:
        text = f.read()
    start = re.search(r"^\|\s*Class\s*\|.*$", text, re.M)
    if not start:
        report.note(f"[requires-vocabulary] skipped: {CLASS_TABLE} has no table whose first column is Class")
        return None
    classes = []
    for line in text[start.end():].lstrip("\n").split("\n"):
        if not line.startswith("|"):
            break
        m = re.match(r"\|\s*`([^`]+)`", line)
        if m:
            classes.append(m.group(1))
    return classes


def known_class(value, classes):
    """A class of the table, or a class the table writes with a placeholder (publisher:<platform>) given as
    written or with a value in the placeholder's place."""
    for c in classes:
        if value == c:
            return True
        head, sep, tail = c.partition(":")
        if sep and tail.startswith("<") and re.match(re.escape(head) + r":[a-z0-9][a-z0-9-]*$", value):
            return True
    return False


def check_skill(dirname, report, outputs_index, classes=None):
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

    if meta.get("side_effects") and not has_gate_heading(body):
        report.error(where, "side_effects is non-empty but there is no '## Confirmation gate' section")
    if not meta.get("side_effects") and has_gate_heading(body):
        report.warn(where, "has a Confirmation gate section but declares no side_effects")

    missing = [f"metadata.{k}" for k in REQUIRED_META if k not in meta] + ([] if fm.get("license") else ["license"])
    if missing:
        report.warn(where, f"missing: {', '.join(missing)}", "meta-keys")
    strings = lambda key: [v for v in meta[key] if isinstance(v, str)] if isinstance(meta.get(key), list) else []
    unknown = [v for v in strings("side_effects") if v not in SIDE_EFFECTS]
    if unknown:
        report.warn(where, f"side_effects {', '.join(unknown)}: not in the vocabulary ({', '.join(SIDE_EFFECTS)})",
                    "side-effects-vocabulary")
    unknown = [v for v in strings("requires") if classes is not None and not known_class(v, classes)]
    if unknown:
        report.warn(where, f"requires {', '.join(unknown)}: not a class of {CLASS_TABLE}", "requires-vocabulary")
    if desc and not re.search(r"\bwhen\b", desc, re.I):
        report.warn(where, "the description does not say when to use the skill (it has no \"when\")", "description-when")
    if DESCRIPTION_WARN < len(desc) <= 1024:
        report.warn(where, f"the description has {len(desc)} characters, over {DESCRIPTION_WARN}", "description-length")
    n_chars = len(fm_text) + len(body) + 8  # the two frontmatter fences
    if n_chars / 4 > TOKEN_WARN:
        report.warn(where, f"SKILL.md has about {n_chars // 4} tokens ({n_chars} characters / 4), over {TOKEN_WARN}: "
                    "move depth to references/", "skill-tokens")

    whole = fm_text + body
    if re.search(r"__[A-Z_]+__", whole):
        report.error(where, "template placeholders (__LIKE_THIS__) are still present")
    if "Delete this section" in body:
        report.error(where, "template instruction 'Delete this section...' is still present")

    check_links(report, where, os.path.join(SKILLS, dirname), body)
    for dirpath, _, files in sorted(os.walk(os.path.join(SKILLS, dirname, "references"))):
        for fn in sorted(f for f in files if f.endswith(".md")):
            p = os.path.join(dirpath, fn)
            with open(p, encoding="utf-8", errors="ignore") as f:
                check_links(report, os.path.relpath(p, ROOT).replace(os.sep, "/"), dirpath, f.read())

    for out in meta.get("outputs") or []:
        outputs_index.setdefault(out, []).append(name or dirname)
    return {"name": name, "inputs": meta.get("inputs") or [], "where": where}


def built_skills(root=ROOT):
    base = os.path.join(root, "skills")
    return sorted(d for d in os.listdir(base) if os.path.isfile(os.path.join(base, d, "SKILL.md"))) if os.path.isdir(base) else []


def assertion_text(a):
    return a if isinstance(a, str) else str(a.get("text") or "") if isinstance(a, dict) else ""


def check_evals(name, report, root=ROOT):
    """The warning rules on skills/<name>/evals/evals.json and on the case fixtures beside it."""
    where = f"skills/{name}"
    path = os.path.join(root, "skills", name, "evals", "evals.json")
    if not os.path.isfile(path):
        report.warn(where, f"no evals/evals.json; a skill has at least {MIN_CASES} cases", "eval-cases-count")
        return
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        report.warn(where, f"evals/evals.json is not valid JSON: {e}", "eval-keys")
        return
    if not isinstance(data, dict):
        report.warn(where, "evals/evals.json must be an object with skill_name and evals", "eval-keys")
        return
    cases = data.get("evals")
    cases = [c for c in cases if isinstance(c, dict)] if isinstance(cases, list) else []
    keys, few, conditional, is_run, named = [], [], [], [], []
    extra = sorted(set(data) - EVALS_KEYS)
    if extra:
        keys.append(f"unknown top-level key(s) {', '.join(extra)}")
    if data.get("skill_name") != name:
        keys.append(f"skill_name {data.get('skill_name')!r} is not the folder name")
    if not isinstance(data.get("evals"), list) or len(cases) != len(data["evals"]):
        keys.append("evals must be a list of objects")
    ids = [c.get("id") for c in cases]
    if any(i is None for i in ids):
        keys.append("a case has no id")
    repeated = sorted({str(i) for i in ids if i is not None and ids.count(i) > 1})
    if repeated:
        keys.append(f"case id(s) used more than once: {', '.join(repeated)}")
    for c in cases:
        cid = c.get("id")
        extra = sorted(set(c) - CASE_KEYS)
        if extra:
            keys.append(f"case {cid}: unknown key(s) {', '.join(extra)}")
        if "tags" in c and not (isinstance(c["tags"], list) and all(isinstance(t, str) for t in c["tags"])):
            keys.append(f"case {cid}: tags must be a list of texts")
        assertions = c.get("assertions") if isinstance(c.get("assertions"), list) else []
        for n, a in enumerate(assertions, 1):
            if isinstance(a, str):
                continue
            tags = a.get("tags", []) if isinstance(a, dict) else None
            if (not isinstance(a, dict) or set(a) - ASSERTION_KEYS or not isinstance(a.get("text"), str)
                    or not isinstance(tags, list)):
                keys.append(f"case {cid}, assertion {n}: an assertion is a text, or an object with text and tags only")
                continue
            bad = [str(t) for t in tags if not (isinstance(t, str) and ASSERTION_TAG_RE.match(t))]
            if bad:
                keys.append(f"case {cid}, assertion {n}: tag(s) {', '.join(bad)} not among guard, guard:<effect>, format")
        if len(assertions) < MIN_ASSERTIONS:
            few.append(f"case {cid} has {len(assertions)}")
        for n, a in enumerate(assertions, 1):
            text = assertion_text(a)
            if CONDITIONAL_RE.search(text):
                conditional.append(f"case {cid}, assertion {n}")
            if IS_RUN_RE.search(text) and not VISIBLE_RE.search(text):
                is_run.append(f"case {cid}, assertion {n}")
        if isinstance(c.get("prompt"), str) and re.search(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", c["prompt"]):
            named.append(f"case {cid}")
    if len(cases) < MIN_CASES:
        report.warn(where, f"{len(cases)} case(s) in evals/evals.json; a skill has at least {MIN_CASES}", "eval-cases-count")
    for found, rule, text in (
            (keys, "eval-keys", "evals/evals.json: {}"),
            (few, "eval-assertions-count", "fewer than %d assertions: {}" % MIN_ASSERTIONS),
            (conditional, "eval-conditional-assertion", "an assertion that starts with \"If\" holds whenever its "
             "condition is false; state what the output shows: {}"),
            (is_run, "eval-run-assertion", "the grader reads the reply and the files, not the commands; say what "
             "output is quoted or reported: {}"),
            (named, "eval-prompt-names-skill", "the prompt names the skill under test, which the run without the "
             "skill cannot follow: {}")):
        if found:
            report.warn(where, text.format("; ".join(found)), rule)
    scanner, hits = load_scanner(), {}
    evals_dir = os.path.dirname(path)
    for dirpath, dirs, files in os.walk(evals_dir):
        if dirpath == evals_dir:  # the cases and their fixtures; records and evidence name their adapter by design
            dirs[:] = [d for d in dirs if d != "evidence"]
            files = [f for f in files if f != "result.json"]
        dirs[:] = sorted(d for d in dirs if d not in scanner.SKIP_DIRS)
        for fn in sorted(files):
            text = scanner.read_text(os.path.join(dirpath, fn))
            found = sorted(set(PRODUCT_RE.findall(text))) if text else []
            if found:
                hits[os.path.relpath(os.path.join(dirpath, fn), os.path.dirname(evals_dir)).replace(os.sep, "/")] = found
    if hits:
        report.warn(where, "an eval case or fixture names an AI product or a design tool; name the class of tool: "
                    + "; ".join(f"{p} ({', '.join(n)})" for p, n in sorted(hits.items())), "eval-product-names")


def check_skill_names(name, report, built, root=ROOT):
    """skill-name: a backticked skill name in the skill's Markdown, outside evals/, is built or marked planned."""
    base, found = os.path.join(root, "skills", name), []
    for dirpath, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if not (dirpath == base and d == "evals"))
        for fn in sorted(f for f in files if f.endswith(".md")):
            p = os.path.join(dirpath, fn)
            with open(p, encoding="utf-8", errors="ignore") as f:
                for ln, line in enumerate(f, 1):
                    if re.search(r"\bplanned\b", line, re.I) or SKILL_NAME_ALLOW_RE.search(line):
                        continue
                    for cited in SKILL_NAME_RE.findall(line):
                        if cited not in built:
                            found.append(f"{cited} ({os.path.relpath(p, base).replace(os.sep, '/')}:{ln})")
    if found:
        report.warn(f"skills/{name}", "cites a skill that is not built, with no \"planned\" on the line: "
                    + "; ".join(found), "skill-name")


def check_routing(report, built, root=ROOT):
    """routing-table: the router's table names every built skill, and each name in it is built or (planned)."""
    path = os.path.join(root, ROUTING_TABLE)
    if not os.path.isfile(path):
        if ROUTER in built:
            report.warn(ROUTING_TABLE, "the router has no routing table", "routing-table")
        else:
            report.note(f"[routing-table] skipped: {ROUTING_TABLE} is not in this tree")
        return
    listed, planned = set(), set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.startswith("|"):
                continue
            for cited, mark in ROUTE_RE.findall(line):
                (planned if mark else listed).add(cited)
    problems = []
    missing = [s for s in built if s != ROUTER and s not in listed | planned]
    if missing:
        problems.append(f"built and not in the table: {', '.join(missing)}")
    if sorted(listed - set(built)):
        problems.append(f"in the table, not built and not marked (planned): {', '.join(sorted(listed - set(built)))}")
    if sorted(planned & set(built)):
        problems.append(f"marked (planned) and built: {', '.join(sorted(planned & set(built)))}")
    if problems:
        report.warn(ROUTING_TABLE, "; ".join(problems), "routing-table")


def check_test_names(report, root=ROOT):
    """test-file-names: pytest imports a test file by its base name, so two files of one name in two of the
    folders the checks run fail collection, far from the cause."""
    path = os.path.join(root, "scripts", "test_dirs.py")
    if not os.path.isfile(path):
        report.note("[test-file-names] skipped: scripts/test_dirs.py is not in this tree")
        return
    spec = importlib.util.spec_from_file_location("test_dirs", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    seen = {}
    for d in module.test_dirs(root):
        for fn in sorted(os.listdir(os.path.join(root, d))):
            if fn.startswith("test_") and fn.endswith(".py"):
                seen.setdefault(fn, []).append(d.replace(os.sep, "/"))
    for fn, dirs in sorted(seen.items()):
        if len(dirs) > 1:
            report.warn(f"{dirs[1]}/{fn}", f"the test file name {fn} is also in {dirs[0]}"
                        + (f" and {len(dirs) - 2} more" if len(dirs) > 2 else "")
                        + "; names are unique across the test folders", "test-file-names")


def flags_markdown(report, skills):
    """The named warning rules and the skills each one lists, as the Markdown of docs/architecture/phase-c-flags.md."""
    by_rule = {}
    for w in report.warnings:
        if w.get("rule"):
            by_rule.setdefault(w["rule"], []).append(w)
    lines = ["# What the validator's warning rules list, by rule", "",
             "Generated by `python3 scripts/validate.py --flags`; never edited by hand. It is a snapshot of the tree "
             "it was generated on: a row of phase C reads the lines of its skill here, and the current list is "
             "always what the command prints. Each rule is described in the docstring of `scripts/validate.py`.", "",
             f"Skills validated: {skills}.", "", "| Rule | Skills listed |", "|------|---------------|"]
    skill_of = lambda w: w["where"].split("/")[1] if w["where"].startswith("skills/") else w["where"]
    for rule in WARNING_RULES:
        lines.append(f"| `{rule}` | {len({skill_of(w) for w in by_rule.get(rule, [])})} |")
    for rule in WARNING_RULES:
        lines += ["", f"## `{rule}`", ""]
        found = by_rule.get(rule, [])
        if not found:
            lines.append("Nothing listed.")
        for w in sorted(found, key=lambda w: w["where"]):
            lines.append(f"- `{skill_of(w)}`: {w['message'][len(rule) + 3:]}")
    return "\n".join(lines) + "\n"


WARNING_RULES = ("meta-keys", "requires-vocabulary", "side-effects-vocabulary", "description-when",
                 "description-length", "skill-tokens", "eval-cases-count", "eval-keys", "eval-assertions-count",
                 "eval-conditional-assertion", "eval-run-assertion", "eval-prompt-names-skill",
                 "eval-product-names", "skill-name", "routing-table", "test-file-names")


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
    # Beside this file, whatever tree is being validated.
    spec = importlib.util.spec_from_file_location(
        "security_scan", os.path.join(os.path.dirname(os.path.abspath(__file__)), "security_scan.py"))
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


def check_eval_cases(report, root=ROOT):
    """Every skill's eval cases pass the runner's preflight (evals/eval_run.py --check-cases; no model call):
    a file a prompt cites is shipped at the path it names, grader files and dependency skills exist."""
    from concurrent.futures import ThreadPoolExecutor
    runner = os.path.join(root, "evals", "eval_run.py")
    base = os.path.join(root, "skills")
    if not os.path.isfile(runner) or not os.path.isdir(base):
        return
    names = sorted(d for d in os.listdir(base) if os.path.isfile(os.path.join(base, d, "evals", "evals.json")))

    def one(name):
        return name, subprocess.run([sys.executable, runner, "--skill", name, "--check-cases"],
                                    capture_output=True, text=True, cwd=root)
    with ThreadPoolExecutor(max_workers=8) as pool:  # independent checks, run together (principle 7)
        results = list(pool.map(one, names))
    for name, r in results:
        if r.returncode != 0:
            lines = [l for l in r.stderr.strip().splitlines() if l.strip()]
            report.error(f"skills/{name}/evals/evals.json", "[eval-cases] " + ("; ".join(lines[-6:]) or "the preflight failed")
                         + f" (python3 evals/eval_run.py --skill {name} --check-cases)")


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
    unknown = [a for a in argv if a not in ("--strict", "--json", "--spec", "--flags")]
    if unknown:
        print(f"Error: unknown option(s) {unknown}. See --help.", file=sys.stderr)
        return 2
    strict, as_json, spec, flags = "--strict" in argv, "--json" in argv, "--spec" in argv, "--flags" in argv
    if as_json and flags:
        print("Error: --json and --flags both print to stdout; give one. See --help.", file=sys.stderr)
        return 2
    report = Report()
    outputs_index, skills = {}, []

    built = built_skills()
    if os.path.isdir(SKILLS):
        classes = load_classes(report)
        for d in sorted(os.listdir(SKILLS)):
            if os.path.isdir(os.path.join(SKILLS, d)):
                s = check_skill(d, report, outputs_index, classes)
                if s:
                    skills.append(s)
                if d in built:
                    check_evals(d, report)
                    check_skill_names(d, report, built)
        check_routing(report, built)
    check_inputs_chain(skills, outputs_index, report)
    if os.path.isdir(AGENTS):
        for fn in sorted(os.listdir(AGENTS)):
            if fn.endswith(".md"):
                check_agent(fn, report)
    check_doc_links(report)
    check_test_names(report)
    check_harness_names(report)
    check_english(report)
    check_private_terms(report)
    check_eval_status(report)
    check_eval_cases(report)
    check_security(report)
    if spec:
        run_spec_validator(report)

    for e in report.errors:
        print(f"ERROR   {e['where']}: {e['message']}", file=sys.stderr)
    for w in report.warnings:
        print(f"WARNING {w['where']}: {w['message']}", file=sys.stderr)
    for n in report.notes:
        print(f"NOTE    {n}", file=sys.stderr)
    failed = bool(report.errors) or (strict and bool(report.warnings))
    summary = {
        "skills": len(skills),
        "errors": len(report.errors),
        "warnings": len(report.warnings),
        "ok": not failed,
    }
    if flags:
        print(flags_markdown(report, len(skills)), end="")
    elif as_json:
        print(json.dumps({"summary": summary, "errors": report.errors, "warnings": report.warnings}, indent=2))
    else:
        print(json.dumps(summary))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
