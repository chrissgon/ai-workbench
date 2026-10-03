#!/usr/bin/env python3
"""Measure a codebase: stack, entry points, module import graph with coupling, external packages, integration signals.

Usage: python3 map_codebase.py --root <dir> [--focus <subdir>] [--top <n>]

Prints JSON. Nothing is modified. Coupling is computed from static import statements in
.ts .tsx .js .jsx .mjs .cjs .vue .svelte .py .go files (generated and dependency folders excluded):
  afferent  = number of distinct other modules that import this module
  efferent  = number of distinct other modules this module imports
A "module" is the first path segment under the source root (src/ when present, else the project root),
so counts are module-level. Dynamic imports, framework auto-imports and runtime injection are not seen;
say so in any document built on this output.

Exit codes: 0 ok, 1 no source files found, 2 usage error.
"""
import json
import os
import re
import sys
from collections import defaultdict

EXCLUDE_DIRS = {"node_modules", ".git", "dist", "build", ".nuxt", ".output", ".next", "coverage", "vendor", "__pycache__",
                ".venv", "venv", "target", ".cache", ".turbo", "playwright-report", "test-results", ".idea", ".vscode"}
SOURCE_EXT = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte", ".py", ".go")
MANIFESTS = ("package.json", "pyproject.toml", "requirements.txt", "go.mod", "Cargo.toml", "composer.json", "Gemfile")
FRAMEWORK_HINTS = {"nuxt": "Nuxt", "vue": "Vue", "react": "React", "next": "Next.js", "svelte": "Svelte", "@sveltejs/kit": "SvelteKit",
                   "express": "Express", "@nestjs/core": "NestJS", "fastify": "Fastify", "hono": "Hono", "vite": "Vite", "pinia": "Pinia",
                   "vue-router": "Vue Router", "tailwindcss": "Tailwind", "@nuxtjs/tailwindcss": "Tailwind (Nuxt)", "prisma": "Prisma",
                   "mongoose": "Mongoose", "pg": "PostgreSQL client", "redis": "Redis client", "playwright": "Playwright", "vitest": "Vitest",
                   "jest": "Jest", "django": "Django", "flask": "Flask", "fastapi": "FastAPI"}
CLIENT_HINTS = ("fetch(", "$fetch(", "useFetch(", "axios", "algoliasearch", "@nuxtjs/algolia", "prisma.", "mongoose.", "createClient(",
                "stripe", "openai", "anthropic", "supabase", "firebase", "WebSocket(", "graphql")
IMPORT_RE = re.compile(r"""(?:^|\n)\s*(?:import\s+(?:[^'"\n]*?\s+from\s+)?|export\s+[^'"\n]*?\s+from\s+)['"]([^'"\n]+)['"]|require\(\s*['"]([^'"\n]+)['"]\s*\)|import\(\s*['"]([^'"\n]+)['"]\s*\)""")
PY_IMPORT_RE = re.compile(r"^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))", re.M)
GO_IMPORT_RE = re.compile(r'"([\w\./-]+)"')
ENV_RE = re.compile(r"(?:process\.env|import\.meta\.env)\.([A-Z][A-Z0-9_]+)|os\.environ(?:\.get)?\(?\[?['\"]([A-Z][A-Z0-9_]+)['\"]|os\.Getenv\(\"([A-Z][A-Z0-9_]+)\"")
URL_RE = re.compile(r"https?://[\w\.-]+(?:/[\w\./%-]*)?")


def walk(root):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in EXCLUDE_DIRS and not d.startswith(".")]
        for fn in fns:
            yield os.path.join(dp, fn)


def read(path, limit=400000):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read(limit)
    except OSError:
        return ""


def detect_stack(root):
    stack = {"manifests": [m for m in MANIFESTS if os.path.isfile(os.path.join(root, m))], "frameworks": [], "dependencies": {}, "package": {}}
    pj = os.path.join(root, "package.json")
    if os.path.isfile(pj):
        try:
            d = json.loads(read(pj))
            deps = {**(d.get("dependencies") or {}), **(d.get("devDependencies") or {})}
            stack["dependencies"] = deps
            stack["package"] = {k: d.get(k) for k in ("name", "version", "description", "type", "main", "module", "exports", "scripts", "workspaces") if d.get(k) is not None}
            stack["frameworks"] = sorted({FRAMEWORK_HINTS[k] for k in deps if k in FRAMEWORK_HINTS})
        except ValueError:
            pass
    for fn in ("pyproject.toml", "requirements.txt"):
        p = os.path.join(root, fn)
        if os.path.isfile(p):
            txt = read(p).lower()
            stack["frameworks"] += [v for k, v in FRAMEWORK_HINTS.items() if k in ("django", "flask", "fastapi") and k in txt]
    return stack


def detect_monorepo(root, stack):
    ws = (stack.get("package") or {}).get("workspaces")
    candidates = [d for d in ("packages", "apps", "services", "libs") if os.path.isdir(os.path.join(root, d))]
    return {"workspaces": ws, "candidate_dirs": candidates, "likely": bool(ws) or bool(candidates)}


def source_root(root):
    return os.path.join(root, "src") if os.path.isdir(os.path.join(root, "src")) else root


def module_of(rel, src_rel):
    parts = rel.split(os.sep)
    if src_rel and parts and parts[0] == src_rel:
        parts = parts[1:]
    return parts[0] if len(parts) > 1 else "(root files)"


def resolve_internal(spec, importer_dir, root, src):
    if spec.startswith("."):
        base = os.path.normpath(os.path.join(importer_dir, spec))
    elif spec.startswith(("~/", "@/", "#")):
        base = os.path.normpath(os.path.join(src, spec.split("/", 1)[1] if "/" in spec else ""))
    elif spec.startswith("~"):
        base = os.path.normpath(os.path.join(src, spec[1:].lstrip("/")))
    else:
        return None
    for cand in (base, base + ".ts", base + ".js", base + ".vue", base + ".tsx", base + ".mjs", base + ".py",
                 os.path.join(base, "index.ts"), os.path.join(base, "index.js"), os.path.join(base, "index.vue"), os.path.join(base, "__init__.py")):
        if os.path.isfile(cand):
            return cand
    return base


def analyze(root, focus, top):
    root = os.path.abspath(root)
    scan_root = os.path.join(root, focus) if focus else root
    stack = detect_stack(root)
    src = source_root(scan_root)
    src_rel = os.path.relpath(src, scan_root) if src != scan_root else ""
    files = [p for p in walk(scan_root) if p.endswith(SOURCE_EXT)]
    if not files:
        return None
    ext_counts, dir_counts = defaultdict(int), defaultdict(int)
    for p in walk(scan_root):
        ext = os.path.splitext(p)[1] or "(none)"
        ext_counts[ext] += 1
        rel = os.path.relpath(p, scan_root)
        dir_counts[rel.split(os.sep)[0] if os.sep in rel else "(root files)"] += 1
    mod_imports, file_imports, external_use, env_vars, urls, clients = defaultdict(set), {}, defaultdict(set), defaultdict(set), defaultdict(set), defaultdict(set)
    afferent_files = defaultdict(set)
    for p in files:
        rel = os.path.relpath(p, scan_root)
        mod = module_of(rel, src_rel)
        txt = read(p)
        specs = []
        if p.endswith(".py"):
            specs = [a or b for a, b in PY_IMPORT_RE.findall(txt)]
        elif p.endswith(".go"):
            specs = GO_IMPORT_RE.findall(txt)
        else:
            specs = [a or b or c for a, b, c in IMPORT_RE.findall(txt)]
        internal = set()
        for spec in specs:
            target = resolve_internal(spec, os.path.dirname(p), root, src) if not p.endswith((".py", ".go")) else None
            if target:
                trel = os.path.relpath(target, scan_root)
                if not trel.startswith(".."):
                    tmod = module_of(trel, src_rel)
                    internal.add(trel)
                    afferent_files[trel].add(rel)
                    if tmod != mod:
                        mod_imports[mod].add(tmod)
            elif spec and not spec.startswith(".") and not p.endswith(".go"):
                pkg = spec if not spec.startswith("@") else "/".join(spec.split("/")[:2])
                pkg = pkg.split("/")[0] if not pkg.startswith("@") else pkg
                external_use[pkg].add(rel)
        file_imports[rel] = sorted(internal)
        for a, b, c in ENV_RE.findall(txt):
            env_vars[a or b or c].add(rel)
        for u in URL_RE.findall(txt):
            if "w3.org" not in u and "schema" not in u:
                urls[u].add(rel)
        for hint in CLIENT_HINTS:
            if hint in txt:
                clients[hint].add(rel)
    modules = sorted({module_of(os.path.relpath(p, scan_root), src_rel) for p in files})
    afferent_mod = {m: sorted({k for k, v in mod_imports.items() if m in v}) for m in modules}
    module_rows = [{"module": m, "files": sum(1 for p in files if module_of(os.path.relpath(p, scan_root), src_rel) == m),
                    "afferent": len(afferent_mod[m]), "imported_by": afferent_mod[m], "efferent": len(mod_imports.get(m, ())), "imports": sorted(mod_imports.get(m, ()))}
                   for m in modules]
    top_files = sorted(afferent_files.items(), key=lambda kv: -len(kv[1]))[:top]
    entry = []
    pkg = stack.get("package") or {}
    for k in ("main", "module"):
        if pkg.get(k):
            entry.append({"kind": k, "path": pkg[k]})
    if isinstance(pkg.get("exports"), dict):
        entry += [{"kind": "export", "path": v if isinstance(v, str) else json.dumps(v)} for v in list(pkg["exports"].values())[:8]]
    for fn in ("app.vue", "nuxt.config.ts", "nuxt.config.js", "vite.config.ts", "vite.config.js", "next.config.js", "src/main.ts", "src/main.js",
               "src/index.ts", "src/index.js", "index.html", "main.py", "app.py", "manage.py", "main.go", "server/index.ts", "src/app.ts"):
        if os.path.isfile(os.path.join(scan_root, fn)):
            entry.append({"kind": "file", "path": fn})
    routes = []
    for d in ("pages", "src/pages", "app/routes", "src/routes", "server/api", "src/server/api", "app/api"):
        dp = os.path.join(scan_root, d)
        if os.path.isdir(dp):
            routes.append({"dir": d, "files": sorted(os.path.relpath(p, scan_root) for p in walk(dp) if p.endswith(SOURCE_EXT))[:60]})
    docs = sorted(f for f in os.listdir(root) if f.lower().endswith(".md"))
    ci = []
    wf = os.path.join(root, ".github", "workflows")
    if os.path.isdir(wf):
        ci = sorted(os.path.join(".github/workflows", f) for f in os.listdir(wf))
    deploy = [f for f in ("netlify.toml", "vercel.json", "Dockerfile", "docker-compose.yaml", "docker-compose.yml", "fly.toml", "render.yaml", "Procfile") if os.path.isfile(os.path.join(root, f))]
    return {
        "root": root, "focus": focus, "source_root": os.path.relpath(src, root) or ".",
        "stack": stack, "monorepo": detect_monorepo(root, stack),
        "tree": {"top_level": dict(sorted(dir_counts.items(), key=lambda kv: -kv[1])), "by_extension": dict(sorted(ext_counts.items(), key=lambda kv: -kv[1])[:15])},
        "source_files": len(files), "entry_points": entry, "routes": routes,
        "modules": sorted(module_rows, key=lambda r: (-r["afferent"], -r["files"])),
        "top_files_by_afferent": [{"file": f, "imported_by": len(v)} for f, v in top_files],
        "external_packages": sorted(({"package": k, "files": len(v)} for k, v in external_use.items()), key=lambda r: -r["files"])[:40],
        "integration_signals": {"env_vars": {k: sorted(v)[:5] for k, v in sorted(env_vars.items())},
                                "urls": {k: sorted(v)[:3] for k, v in sorted(urls.items())[:25]},
                                "clients": {k: sorted(v)[:5] for k, v in sorted(clients.items())}},
        "docs_at_root": docs, "ci": ci, "deploy": deploy,
        "limits": "static imports only; framework auto-imports, dynamic imports and runtime injection are not counted",
    }


def main(argv):
    if not argv:
        print(__doc__, file=sys.stderr)
        print("Error: no arguments. See --help.", file=sys.stderr)
        return 2
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    root, focus, top = ".", None, 15
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--root", "--focus", "--top") and i + 1 >= len(argv):
            print(f"Error: {a} needs a value. See --help.", file=sys.stderr)
            return 2
        if a == "--root": root = argv[i + 1]; i += 2
        elif a == "--focus": focus = argv[i + 1]; i += 2
        elif a == "--top":
            try:
                top = int(argv[i + 1])
            except ValueError:
                print(f"Error: --top needs a whole number, got {argv[i + 1]!r}. See --help.", file=sys.stderr)
                return 2
            i += 2
        else:
            print(f"Error: unknown option {a!r}. See --help.", file=sys.stderr)
            return 2
    if not os.path.isdir(root):
        print(f"Error: --root {root!r} is not a directory.", file=sys.stderr)
        return 2
    result = analyze(root, focus, top)
    if result is None:
        print(json.dumps({"error": "no source files found", "root": os.path.abspath(root), "focus": focus}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
