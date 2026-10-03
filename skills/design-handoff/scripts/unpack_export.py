#!/usr/bin/env python3
"""Unpack a single-file HTML export of an AI design tool into readable source.

Usage: python3 unpack_export.py --file <export.html> --out <dir> [--class-prefix <prefix>]
                                [--library <stylesheet.css>] [--max-bytes <n>]

Usage errors (a flag without its value, an unknown flag, a missing --file or --out) go to stderr with exit 2.

Handles the bundled format that stores the page as a JSON-encoded template
(<script type="__bundler/template">) and its resources in a manifest of base64
(optionally gzip-compressed) files (<script type="__bundler/manifest">). A plain HTML
file is copied as-is.

Writes to <dir>:
  source.html      the page template with resource ids kept as they are
  styles/NN.css    every <style> block of the template, in order
  scripts/NN.js    every inline script of the template, in order
  resources/<id>.<ext>   every manifest resource, decoded
  inventory.json   resources with mime and size; external URLs; the classes that start with
                   --class-prefix (the component library's prefix, e.g. `ui` for `ui-btn`), or, without
                   it, the most used class prefixes so the library's can be recognised; custom properties
                   defined and used; font families; fixed colours; script_flags (every true or false
                   constant of the scripts, with file and line: the candidates for preview-only switches);
                   script_numbers (every numeric constant: durations, delays, staggers); script_data (every
                   constant holding an object or array literal: hard-coded content, often fake); css_motion
                   (every transition, animation and @keyframes of the styles); and, with --library (the
                   stylesheet the product ships), to_cover: the custom properties and fixed colours that
                   stylesheet does not have, which are the rows the spec's Tokens table must carry
Prints the inventory summary as JSON, with today's date (for the spec's header) and to_cover, script_flags, script_numbers, script_data and css_motion in full. Exit codes: 0 ok, 1 unreadable or refused export, 2 usage error.

The export is content written by someone else, so its manifest is checked before anything is
written: every resource id must match [a-z0-9-]+ (an id such as ../../src/index or /etc/x is
refused and nothing is unpacked), every resolved path must stay inside <dir>/resources, and a
decoded or decompressed resource larger than --max-bytes (default 52428800, 50 MB) is refused.
"""
import base64
import datetime
import json
import os
import re
import sys
import zlib

MAX_BYTES = 50 * 1024 * 1024
RID_RE = re.compile(r"[a-z0-9-]+")

EXT = {"image/svg+xml": "svg", "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp",
       "font/woff2": "woff2", "font/woff": "woff", "font/ttf": "ttf", "text/css": "css",
       "application/javascript": "js", "text/javascript": "js", "text/html": "html"}


def script_body(s, typ):
    m = re.search(r'<script type="' + re.escape(typ) + r'"[^>]*>(.*?)</script>', s, re.S)
    return m.group(1).strip() if m else None


def decompress_capped(data, limit):
    """gunzip data, refusing output larger than limit bytes instead of inflating it all."""
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    out = d.decompress(data, limit + 1)
    if len(out) > limit or d.unconsumed_tail:
        raise ValueError(f"decompresses to more than {limit} bytes")
    return out


def resource_path(res_dir, rid, ext):
    """The file a resource is written to; ValueError when the id could leave res_dir."""
    if not isinstance(rid, str) or not RID_RE.fullmatch(rid):
        raise ValueError(f"resource id {rid!r} does not match [a-z0-9-]+")
    base = os.path.realpath(res_dir)
    path = os.path.realpath(os.path.join(base, f"{rid}.{ext}"))
    if os.path.dirname(path) != base:
        raise ValueError(f"resource id {rid!r} resolves outside {res_dir}")
    return path


def decode_manifest(man, res_dir, limit):
    """Validate and decode every resource before anything is written: [(path, data, entry)]."""
    if not isinstance(man, dict):
        raise ValueError("manifest is not an object")
    decoded = []
    for rid, meta in man.items():
        meta = meta if isinstance(meta, dict) else {}
        ext = EXT.get(meta.get("mime", ""), "bin")
        path = resource_path(res_dir, rid, ext)
        encoded = meta.get("data", "")
        if len(encoded) * 3 // 4 > limit:
            raise ValueError(f"resource {rid!r} is larger than {limit} bytes")
        data = base64.b64decode(encoded)
        if meta.get("compressed"):
            try:
                data = decompress_capped(data, limit)
            except (ValueError, zlib.error) as e:
                raise ValueError(f"resource {rid!r}: {e}") from None
        decoded.append((path, data, {"id": rid, "mime": meta.get("mime"), "bytes": len(data)}))
    return decoded


CONST_RE = re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*"
                      r"(true|false|-?\d+(?:\.\d+)?)\s*;?\s*(?://\s*(.*))?$")


DATA_RE = re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*([{\[].*)$")


def script_constants(scripts):
    """The constants of the scripts with a literal value: ([flags], [numbers], [data]), each with file and line.

    flags are true or false, numbers are numeric, data are object or array literals (hard-coded content)."""
    flags, numbers, data = [], [], []
    for i, js in enumerate(scripts, 1):
        for n, line in enumerate(js.splitlines(), 1):
            d = DATA_RE.match(line)
            if d:
                data.append({"name": d.group(1), "starts": d.group(2).strip()[:120], "script": f"scripts/{i:02}.js", "line": n})
                continue
            m = CONST_RE.match(line)
            if not m:
                continue
            entry = {"name": m.group(1), "value": m.group(2), "script": f"scripts/{i:02}.js", "line": n}
            if m.group(3):
                entry["comment"] = m.group(3).strip()
            (flags if m.group(2) in ("true", "false") else numbers).append(entry)
    return flags, numbers, data


def css_motion(css):
    """Every transition and animation declaration and every @keyframes name of the styles, in order."""
    found = [" ".join(d.split()) for d in re.findall(r"(?<![\w-])((?:transition|animation)(?:-[a-z-]+)?\s*:\s*[^;}]+)", css)]
    found += [f"@keyframes {k}" for k in re.findall(r"@keyframes\s+([\w-]+)", css)]
    return list(dict.fromkeys(found))


def to_cover(inv, lib):
    """What the library stylesheet does not have: the rows the Tokens table must carry (lint_handoff.py's rule)."""
    libvars = set(re.findall(r"(--[a-z0-9-]+)\s*:", lib))
    props = sorted(set(inv["custom_properties_defined"] + inv["custom_properties_used"]) - libvars)
    return {"custom_properties": props, "fixed_colours": [c for c in inv["fixed_colours"] if c not in lib.lower()]}


VALUE_FLAGS = ("--file", "--out", "--max-bytes", "--class-prefix", "--library")


def parse(argv):
    """The flags given, as {flag: value}, and None; or None and the message of a usage error."""
    args, i = {}, 0
    while i < len(argv):
        a = argv[i]
        if a not in VALUE_FLAGS:
            return None, f"unknown argument {a!r}"
        if i + 1 >= len(argv):
            return None, f"{a} needs a value"
        args[a] = argv[i + 1]
        i += 2
    return args, None


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    args, problem = parse(argv)
    if problem:
        print(f"Error: {problem}. See --help.", file=sys.stderr)
        return 2
    try:
        limit = int(args.get("--max-bytes", MAX_BYTES))
    except ValueError:
        print("Error: --max-bytes needs a whole number of bytes. See --help.", file=sys.stderr)
        return 2
    prefix = args.get("--class-prefix", "").rstrip("-")
    if prefix and not re.fullmatch(r"[a-z][a-z0-9]*", prefix):
        print("Error: --class-prefix must be lowercase letters and digits, e.g. ui", file=sys.stderr)
        return 2
    if "--file" not in args or "--out" not in args:
        print("Error: --file and --out are required. See --help.", file=sys.stderr)
        return 2
    try:
        raw = open(args["--file"], encoding="utf-8").read()
    except (OSError, UnicodeDecodeError) as e:
        print(f"Error: cannot read export: {e}", file=sys.stderr)
        return 1
    lib = None
    if "--library" in args:
        try:
            lib = open(args["--library"], encoding="utf-8").read()
        except (OSError, UnicodeDecodeError) as e:
            print(f"Error: cannot read the library stylesheet: {e}", file=sys.stderr)
            return 2
    out = args["--out"]
    for d in ("", "styles", "scripts", "resources"):
        os.makedirs(os.path.join(out, d), exist_ok=True)
    res_dir = os.path.join(out, "resources")
    if os.path.islink(res_dir):
        print(f"Error: {res_dir} is a symlink; refusing to write through it.", file=sys.stderr)
        return 1
    tpl = script_body(raw, "__bundler/template")
    resources = []
    if tpl is not None:
        try:
            page = json.loads(tpl)
            man = json.loads(script_body(raw, "__bundler/manifest") or "{}")
            decoded = decode_manifest(man, res_dir, limit)
            ext_res = json.loads(script_body(raw, "__bundler/ext_resources") or "[]")
        except json.JSONDecodeError as e:
            print(f"Error: template or manifest is not JSON: {e}", file=sys.stderr)
            return 1
        except (ValueError, TypeError) as e:
            print(f"Error: refused export, nothing unpacked: {e}", file=sys.stderr)
            return 1
        for path, data, entry in decoded:
            with open(path, "wb") as f:
                f.write(data)
            resources.append(entry)
    else:
        page, ext_res = raw, []
    open(os.path.join(out, "source.html"), "w", encoding="utf-8").write(page)
    styles = re.findall(r"<style[^>]*>(.*?)</style>", page, re.S)
    scripts = [b for a, b in re.findall(r"<script([^>]*)>(.*?)</script>", page, re.S) if b.strip()]
    for i, css in enumerate(styles, 1):
        open(os.path.join(out, "styles", f"{i:02}.css"), "w", encoding="utf-8").write(css)
    for i, js in enumerate(scripts, 1):
        open(os.path.join(out, "scripts", f"{i:02}.js"), "w", encoding="utf-8").write(js)
    allcss = "\n".join(styles)
    flags, numbers, data = script_constants(scripts)
    classes = [c for attr in re.findall(r'\bclass\s*=\s*"([^"]*)"', page) for c in attr.split()]
    if prefix:
        library = {"class_prefix": prefix, "library_classes":
                   sorted(set(re.findall(rf"(?<![\w-]){prefix}-[a-z0-9-]+", page)))}
    else:
        counts = {}
        for c in classes:
            if "-" in c:
                counts[c.split("-")[0]] = counts.get(c.split("-")[0], 0) + 1
        library = {"class_prefixes": sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:10]}
    inv = {
        "resources": resources,
        "external": sorted(set([r.get("id") for r in ext_res] + re.findall(r"https?://[^\s\"')<>]+", page))),
        **library,
        "custom_properties_defined": sorted(set(re.findall(r"(--[a-z0-9-]+)\s*:", allcss))),
        "custom_properties_used": sorted(set(re.findall(r"var\((--[a-z0-9-]+)", page))),
        "font_families": sorted(set(f.strip() for f in re.findall(r"font-family\s*:\s*([^;}\n]+)", page))),
        "fixed_colours": sorted(set(c.lower() for c in re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", page))),
        "script_flags": flags,
        "script_numbers": numbers,
        "script_data": data,
        "css_motion": css_motion(allcss),
        "counts": {"styles": len(styles), "scripts": len(scripts), "bytes": len(page)},
    }
    if lib is not None:
        inv["to_cover"] = to_cover(inv, lib)
    json.dump(inv, open(os.path.join(out, "inventory.json"), "w"), indent=2)
    print(json.dumps({"ok": True, "date": datetime.date.today().isoformat(), "out": out, "counts": inv["counts"], "resources": len(resources),
                      "external": len(inv["external"]),
                      "script_flags": flags, "script_numbers": numbers, "script_data": data,
                      "css_motion": inv["css_motion"],
                      **({"to_cover": inv["to_cover"]} if lib is not None else {}),
                      **({"library_classes": len(inv["library_classes"])} if prefix else
                         {"class_prefixes": inv["class_prefixes"][:3]})}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
