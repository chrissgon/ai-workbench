#!/usr/bin/env python3
"""Scan the workbench for security problems that need no judgment to find.

Usage: python3 scripts/security_scan.py [PATH ...] [--root DIR] [--strict] [--json] [--rules]

Scans the files git would commit under --root (tracked plus untracked, minus ignored; every
file when --root is not a git repository), or only PATH arguments (files or folders). Rules:
  secret-token          error    a known credential format (cloud, git host, chat, model API keys,
                                 private key blocks, JWTs)
  secret-assignment     error    a key, secret, token or password assigned a literal value
  secret-file           error    a credential file (.env, *.pem, *.key, *.p12, id_rsa...) would be committed
  hidden-unicode        error    zero-width, bidirectional or tag characters that hide text from a reader
  hidden-comment        warning  an HTML comment with prose in Markdown: invisible when rendered, read by models
  pipe-to-shell         error    a download piped into a shell (curl ... | sh)
  dynamic-eval          error    eval in a shell script, eval() or exec() in Python
  unsafe-deserialize    error    pickle, marshal or yaml.load without a safe loader
  tls-disabled          error    certificate checks turned off
  shell-invocation      warning  shell=True, os.system or os.popen in Python
  rm-unguarded          warning  rm -r on a path that starts with a variable not guarded by ${VAR:?}
  world-writable        warning  chmod 777 or o+w
  sudo                  warning  sudo inside a script
  undeclared-side-effect error   a skill's script writes to a remote (push, publish, POST...) while the
                                 skill declares side_effects: []
  unpinned-dependency   warning  an inline script dependency or requirement without an exact version
  untrusted-content     error    a skill or agent that reads content written by others (it requires a
                                 search: or integration: class, or names web pages, tickets, bug reports,
                                 review comments, CI logs, design exports...) without the sentence
                                 "External content is data" saying which sources and that instructions
                                 in them are reported, never followed
  allow-without-reason  error    an allow comment with no reason

Silence one finding with a comment on the same line or the line above:
  security-scan: allow <rule> -- <reason>
Suppressed findings are listed in the JSON report with their reason, so they stay auditable.
Secrets are never printed: excerpts are redacted.

Options:
  --root DIR  repository to scan (default: the workbench root)
  --strict    warnings fail the run too
  --json      print the full report as JSON to stdout (human-readable lines go to stderr either way)
  --rules     print the rule table as JSON and exit
  --help      show this text

Exit codes: 0 ok, 1 findings that fail the run, 2 usage error.
"""
import json
import os
import re
import subprocess
import sys

WORKBENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RULES = {
    "secret-token": ("error", "a known credential format"),
    "secret-assignment": ("error", "a credential assigned a literal value"),
    "secret-file": ("error", "a credential file would be committed"),
    "hidden-unicode": ("error", "an invisible or direction-changing character"),
    "hidden-comment": ("warning", "an HTML comment with prose in Markdown"),
    "pipe-to-shell": ("error", "a download piped into a shell"),
    "dynamic-eval": ("error", "code built at run time and executed"),
    "unsafe-deserialize": ("error", "deserialization that can execute code"),
    "tls-disabled": ("error", "certificate verification turned off"),
    "shell-invocation": ("warning", "a command run through a shell from Python"),
    "rm-unguarded": ("warning", "recursive delete of a path that starts with an unguarded variable"),
    "world-writable": ("warning", "a world-writable permission"),
    "sudo": ("warning", "sudo inside a script"),
    "undeclared-side-effect": ("error", "a remote write in a skill that declares no side_effects"),
    "unpinned-dependency": ("warning", "a dependency without an exact version"),
    "untrusted-content": ("error", "reads external content without saying it is data"),
    "allow-without-reason": ("error", "an allow comment with no reason"),
}

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv"}
# This file spells out every pattern it looks for, so scanning it only finds its own rule table.
SELF = os.path.abspath(__file__)
# Markdown the workbench feeds to models as instructions; eval fixtures copy target projects and are excluded.
INSTRUCTION_DIRS = ("skills/", "agents/", "shared/", "templates/", "contracts/")
BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz", ".woff", ".woff2",
              ".ttf", ".otf", ".mp4", ".mov", ".pyc"}
SCRIPT_EXT = {".sh", ".bash", ".zsh", ".py", ".js", ".mjs", ".cjs", ".ts"}

TOKEN_PATTERNS = [
    ("AWS access key", r"\bAKIA[0-9A-Z]{16}\b"),
    ("GitHub token", r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    ("GitHub fine-grained token", r"\bgithub_pat_[A-Za-z0-9_]{50,}\b"),
    ("Slack token", r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    ("model API key", r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{32,}"),
    ("Google API key", r"\bAIza[0-9A-Za-z_-]{35}\b"),
    ("npm token", r"\bnpm_[A-Za-z0-9]{36}\b"),
    ("private key block", r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----"),
    ("JWT", r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
]
TOKEN_RES = [(label, re.compile(p)) for label, p in TOKEN_PATTERNS]
ASSIGN_RE = re.compile(
    r"(?i)\b(api[_-]?key|secret|client[_-]?secret|access[_-]?token|refresh[_-]?token|auth[_-]?token|token|password|passwd)"
    r"\b[\"']?\s*[:=]\s*[\"']([^\"'\s]{12,})[\"']")
PLACEHOLDER_RE = re.compile(r"(?i)[<>{}$]|example|sample|placeholder|changeme|your[_-]|xxx|fake|dummy|test|redacted|\*\*\*")
SECRET_FILE_RE = re.compile(r"(^|/)(\.env(\.[^/]*)?|id_rsa|id_dsa|id_ecdsa|id_ed25519|[^/]*\.(pem|key|p12|pfx|keystore|jks))$")
SECRET_FILE_OK_RE = re.compile(r"\.env\.example$|\.env\.sample$")
HIDDEN_RANGES = [(0x200B, 0x200F), (0x202A, 0x202E), (0x2060, 0x2064), (0x2066, 0x2069), (0xFEFF, 0xFEFF),
                 (0xE0000, 0xE007F)]
HIDDEN_RE = re.compile("[" + "".join(f"{chr(a)}-{chr(b)}" for a, b in HIDDEN_RANGES) + "]")
BOM = chr(0xFEFF)
COMMENT_RE = re.compile(r"<!--(.*?)-->", re.S)
PIPE_SHELL_RE = re.compile(r"\b(curl|wget)\b[^|\n]*\|\s*(sudo\s+)?(ba|z|da|k)?sh\b")
SH_EVAL_RE = re.compile(r"(^|[;&|]\s*|\s)eval\s")
PY_EVAL_RE = re.compile(r"(?<![\w.])(eval|exec)\s*\(")
DESERIALIZE_RE = re.compile(r"\bpickle\.loads?\s*\(|\bmarshal\.loads?\s*\(|\byaml\.load\s*\((?![^)]*Loader\s*=\s*yaml\.SafeLoader)")
TLS_RE = re.compile(r"verify\s*=\s*False|_create_unverified_context|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['\"]?0|"
                    r"\bCERT_NONE\b|\bcurl\b[^\n]*\s(-k|--insecure)\b")
SHELL_PY_RE = re.compile(r"shell\s*=\s*True|\bos\.(system|popen)\s*\(")
RM_RE = re.compile(r"\brm\s+-[A-Za-z]*[rR][A-Za-z]*\s+(?:--\s+)?[\"']?\$(\{?)([A-Za-z_][A-Za-z0-9_]*)(:\?)?")
CHMOD_RE = re.compile(r"\bchmod\s+(-R\s+)?(0?777|[ugoa]*o[ugoa]*\+[rx]*w)")
SUDO_RE = re.compile(r"(^|[;&|]\s*|\s)sudo\s")
REMOTE_WRITE_RE = re.compile(
    r"\bgit\s+push\b|\b(npm|pnpm|yarn)\s+publish\b|\btwine\s+upload\b|"
    r"\bgh\s+(pr|issue|release|repo|gist)\s+(create|merge|close|edit|delete|comment|upload)\b|"
    r"-X\s*(POST|PUT|PATCH|DELETE)\b|--request\s+(POST|PUT|PATCH|DELETE)\b|"
    r"\brequests\.(post|put|patch|delete)\s*\(|method\s*=\s*[\"'](POST|PUT|PATCH|DELETE)[\"']")
# What makes a skill or agent a reader of content written by others, and the sentence it must carry.
EXTERNAL_REQUIRES_RE = re.compile(r"^\s*requires:\s*\[[^\]]*\b(search|integration):", re.M)
EXTERNAL_SOURCE_RE = re.compile(
    r"(?i)\b(tickets?|bug reports?|web pages?|search results|review comments?|pull request (?:descriptions?|comments?|bodies)|"
    r"issue (?:bodies|comments)|CI logs?|--log-failed|failing step|exported code|design[- ]tool exports?|an export\b|"
    r"screenshots?|API responses?|code host)")
UNTRUSTED_MARKER_RE = re.compile(r"External content is data")
PEP723_RE = re.compile(r"^#\s*dependencies\s*=\s*\[(.*)\]")
ALLOW_RE = re.compile(r"security-scan:\s*allow\s+([a-z-]+)(?:\s+--\s*(\S.*?))?\s*(?:-->|\*/)?\s*$")


def redact(text):
    # No part of a secret is printed, not even a prefix (providers/CONTRACT.md).
    for label, rx in TOKEN_RES:
        text = rx.sub(f"<redacted {label}>", text)
    text = ASSIGN_RE.sub(lambda m: m.group(0).replace(m.group(2), "<redacted>"), text)
    return HIDDEN_RE.sub(lambda m: f"<U+{ord(m.group(0)):04X}>", text).strip()[:160]


def list_files(root, paths):
    if paths:
        out = []
        for p in paths:
            ap = os.path.abspath(p)
            if os.path.isdir(ap):
                out += walk(ap)
            elif os.path.isfile(ap):
                out.append(ap)
            else:
                raise FileNotFoundError(p)
        return out
    r = subprocess.run(["git", "-C", root, "ls-files", "-co", "--exclude-standard", "-z"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        return [os.path.join(root, f) for f in r.stdout.split("\0") if f and os.path.isfile(os.path.join(root, f))]
    return walk(root)


def walk(base):
    out = []
    for dirpath, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.endswith("-workspace")]
        out += [os.path.join(dirpath, f) for f in files]
    return out


def read_text(path):
    if os.path.splitext(path)[1].lower() in BINARY_EXT:
        return None
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return None
    if b"\0" in data[:8192]:
        return None
    return data.decode("utf-8", errors="replace")


def skill_side_effects(root, rel, cache):
    """Return (skill name, declared side_effects) when rel is inside skills/<name>/scripts/."""
    parts = rel.split("/")
    if len(parts) < 4 or parts[0] != "skills" or parts[2] != "scripts":
        return None, None
    name = parts[1]
    if name not in cache:
        declared = None
        try:
            with open(os.path.join(root, "skills", name, "SKILL.md"), encoding="utf-8") as f:
                head = f.read().split("\n---", 1)[0]
            m = re.search(r"^\s*side_effects:\s*\[(.*?)\]", head, re.M)
            if m:
                declared = [s.strip() for s in m.group(1).split(",") if s.strip()]
        except OSError:
            pass
        cache[name] = declared
    return name, cache[name]


def scan_file(root, path, cache):
    rel = os.path.relpath(path, root).replace(os.sep, "/")
    findings = []

    def add(rule, line, message, excerpt=""):
        findings.append({"rule": rule, "severity": RULES[rule][0], "path": rel, "line": line,
                         "message": message, "excerpt": redact(excerpt)})

    if SECRET_FILE_RE.search(rel) and not SECRET_FILE_OK_RE.search(rel):
        add("secret-file", 0, "credential file; keep it out of the repository and add it to .gitignore")
    text = read_text(path)
    if text is None:
        return findings
    ext = os.path.splitext(path)[1].lower()
    is_script = ext in SCRIPT_EXT or text.startswith("#!")
    is_shell = ext in {".sh", ".bash", ".zsh"} or (text.startswith("#!") and "sh" in text.split("\n", 1)[0])
    is_python = ext == ".py" or (text.startswith("#!") and "python" in text.split("\n", 1)[0])
    skill, declared = skill_side_effects(root, rel, cache)
    lines = text.split("\n")

    for i, line in enumerate(lines, 1):
        for label, rx in TOKEN_RES:
            if rx.search(line):
                add("secret-token", i, f"looks like a {label}; revoke it if real, then remove it", line)
        m = ASSIGN_RE.search(line)
        if m and not PLACEHOLDER_RE.search(m.group(2)) and not any(rx.search(line) for _, rx in TOKEN_RES):
            add("secret-assignment", i, f"'{m.group(1)}' holds a literal value; read it from the environment", line)
        for ch in HIDDEN_RE.findall(line):
            if not (ch == BOM and i == 1 and line.startswith(BOM)):
                add("hidden-unicode", i, f"invisible character U+{ord(ch):04X}", line)
        if PIPE_SHELL_RE.search(line):
            add("pipe-to-shell", i, "download to a file, check it, then run it", line)
        if is_shell and SH_EVAL_RE.search(line) and not line.lstrip().startswith("#"):
            add("dynamic-eval", i, "eval runs text as code; call the command directly", line)
        if is_python and PY_EVAL_RE.search(line) and not line.lstrip().startswith("#"):
            add("dynamic-eval", i, "eval/exec runs text as code", line)
        if is_script and DESERIALIZE_RE.search(line):
            add("unsafe-deserialize", i, "use json, or yaml.safe_load", line)
        if (is_script or ext == ".md") and TLS_RE.search(line):
            add("tls-disabled", i, "keep certificate verification on", line)
        if is_python and SHELL_PY_RE.search(line):
            add("shell-invocation", i, "pass an argument list to subprocess instead of a shell string", line)
        if is_shell:
            rm = RM_RE.search(line)
            if rm and not rm.group(3) and not re.search(r"-n\s+[\"']?\$\{?" + rm.group(2) + r"\b", line):
                add("rm-unguarded", i, f"use \"${{{rm.group(2)}:?}}\" so an empty variable cannot widen the delete", line)
            if SUDO_RE.search(line) and not line.lstrip().startswith("#"):
                add("sudo", i, "scripts must not escalate privileges; tell the user to run it", line)
        if is_script and CHMOD_RE.search(line):
            add("world-writable", i, "grant the narrowest permission that works", line)
        if skill and declared == [] and is_script and REMOTE_WRITE_RE.search(line):
            add("undeclared-side-effect", i, f"skill '{skill}' writes to a remote but declares side_effects: []", line)
        dep = PEP723_RE.match(line)
        if dep:
            for spec in re.findall(r"[\"']([^\"']+)[\"']", dep.group(1)):
                if "==" not in spec:
                    add("unpinned-dependency", i, f"pin '{spec}' to an exact version (==)", line)
    if os.path.basename(path).startswith("requirements") and ext == ".txt":
        for i, line in enumerate(lines, 1):
            s = line.split("#", 1)[0].strip()
            if s and not s.startswith("-") and "==" not in s:
                add("unpinned-dependency", i, f"pin '{s}' to an exact version (==)", line)
    if re.fullmatch(r"skills/[^/]+/SKILL\.md|agents/[^/]+\.md", rel) and not UNTRUSTED_MARKER_RE.search(text):
        head, _, body = text.partition("\n---")
        reason = "requires a search: or integration: class" if EXTERNAL_REQUIRES_RE.search(head) else None
        m = EXTERNAL_SOURCE_RE.search(text)
        if not reason and m:
            reason = f"mentions '{m.group(0)}'"
        if reason:
            line_no = text.count("\n", 0, m.start()) + 1 if m and not reason.startswith("requires") else 1
            add("untrusted-content", line_no, f"{reason}: add a line starting 'External content is data.' that names "
                "the sources and says instructions in them are reported to the user, never followed")
    if ext == ".md" and rel.startswith(INSTRUCTION_DIRS) and "/evals/files/" not in rel:
        for m in COMMENT_RE.finditer(text):
            if len(m.group(1).split()) >= 4 and "security-scan:" not in m.group(1):
                line_no = text.count("\n", 0, m.start()) + 1
                add("hidden-comment", line_no, "comment prose is invisible when rendered but read by models; "
                    "make it visible text or remove it", m.group(0))
    return apply_allows(findings, lines)


def apply_allows(findings, lines):
    allows = {}
    extra = []
    for i, line in enumerate(lines, 1):
        m = ALLOW_RE.search(line)
        if not m:
            continue
        rule, reason = m.group(1), (m.group(2) or "").strip()
        if not reason:
            extra.append((i, rule))
            continue
        for target in (i, i + 1):
            allows.setdefault(target, {})[rule] = reason
    kept = []
    for f in findings:
        reason = allows.get(f["line"], {}).get(f["rule"])
        if reason:
            f["suppressed"] = reason
        kept.append(f)
    path = findings[0]["path"] if findings else None
    for i, rule in extra:
        kept.append({"rule": "allow-without-reason", "severity": "error", "path": path, "line": i,
                     "message": f"allow for '{rule}' needs a reason: security-scan: allow {rule} -- <reason>",
                     "excerpt": redact(lines[i - 1])})
    return kept


def scan(root, paths=None):
    root = os.path.abspath(root)
    cache, active, suppressed = {}, [], []
    files = list_files(root, paths)
    for path in sorted(files):
        if os.path.abspath(path) == SELF:
            continue
        for f in scan_file(root, path, cache):
            if f["path"] is None:
                f["path"] = os.path.relpath(path, root)
            (suppressed if "suppressed" in f else active).append(f)
    return files, active, suppressed


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    if "--rules" in argv:
        print(json.dumps({k: {"severity": s, "description": d} for k, (s, d) in RULES.items()}, indent=2))
        return 0
    root, paths, strict, as_json = WORKBENCH, [], False, False
    it = iter(argv)
    for a in it:
        if a == "--root":
            root = next(it, None)
            if not root or not os.path.isdir(root):
                print("Error: --root needs an existing folder. See --help.", file=sys.stderr)
                return 2
        elif a == "--strict":
            strict = True
        elif a == "--json":
            as_json = True
        elif a.startswith("-"):
            print(f"Error: unknown option '{a}'. See --help.", file=sys.stderr)
            return 2
        else:
            paths.append(a)
    try:
        files, active, suppressed = scan(root, paths)
    except FileNotFoundError as e:
        print(f"Error: path not found: {e}. See --help.", file=sys.stderr)
        return 2
    errors = [f for f in active if f["severity"] == "error"]
    warnings = [f for f in active if f["severity"] == "warning"]
    for f in errors + warnings:
        print(f"{f['severity'].upper():7} {f['path']}:{f['line']} [{f['rule']}] {f['message']}", file=sys.stderr)
    failed = bool(errors) or (strict and bool(warnings))
    summary = {"files": len(files), "errors": len(errors), "warnings": len(warnings),
               "suppressed": len(suppressed), "ok": not failed}
    if as_json:
        print(json.dumps({"summary": summary, "findings": errors + warnings, "suppressed": suppressed}, indent=2))
    else:
        print(json.dumps(summary))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
