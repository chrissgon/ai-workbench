#!/usr/bin/env python3
"""Unpack a single-file HTML export of an AI design tool into readable source.

Usage: python3 unpack_export.py --file <export.html> --out <dir> [--json]

Handles the bundled format that stores the page as a JSON-encoded template
(<script type="__bundler/template">) and its resources in a manifest of base64
(optionally gzip-compressed) files (<script type="__bundler/manifest">). A plain HTML
file is copied as-is.

Writes to <dir>:
  source.html      the page template with resource ids kept as they are
  styles/NN.css    every <style> block of the template, in order
  scripts/NN.js    every inline script of the template, in order
  resources/<id>.<ext>   every manifest resource, decoded
  inventory.json   resources with mime and size; external URLs; pui- classes used;
                   custom properties defined and used; font families; fixed colours
Prints the inventory summary as JSON. Exit codes: 0 ok, 1 unreadable export, 2 usage error.
"""
import base64
import gzip
import json
import os
import re
import sys

EXT = {"image/svg+xml": "svg", "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp",
       "font/woff2": "woff2", "font/woff": "woff", "font/ttf": "ttf", "text/css": "css",
       "application/javascript": "js", "text/javascript": "js", "text/html": "html"}


def script_body(s, typ):
    m = re.search(r'<script type="' + re.escape(typ) + r'"[^>]*>(.*?)</script>', s, re.S)
    return m.group(1).strip() if m else None


def main(argv):
    if "--help" in argv or "-h" in argv or not argv:
        print(__doc__)
        return 0 if argv else 2
    args = {f: argv[argv.index(f) + 1] for f in ("--file", "--out") if f in argv}
    if len(args) < 2:
        print("Error: --file and --out are required. See --help.", file=sys.stderr)
        return 2
    try:
        raw = open(args["--file"], encoding="utf-8").read()
    except OSError as e:
        print(f"Error: cannot read export: {e}", file=sys.stderr)
        return 1
    out = args["--out"]
    for d in ("", "styles", "scripts", "resources"):
        os.makedirs(os.path.join(out, d), exist_ok=True)
    tpl = script_body(raw, "__bundler/template")
    resources = []
    if tpl is not None:
        try:
            page = json.loads(tpl)
        except json.JSONDecodeError as e:
            print(f"Error: template is not JSON: {e}", file=sys.stderr)
            return 1
        man = json.loads(script_body(raw, "__bundler/manifest") or "{}")
        for rid, meta in man.items():
            data = base64.b64decode(meta.get("data", ""))
            if meta.get("compressed"):
                data = gzip.decompress(data)
            ext = EXT.get(meta.get("mime", ""), "bin")
            open(os.path.join(out, "resources", f"{rid}.{ext}"), "wb").write(data)
            resources.append({"id": rid, "mime": meta.get("mime"), "bytes": len(data)})
        ext_res = json.loads(script_body(raw, "__bundler/ext_resources") or "[]")
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
    inv = {
        "resources": resources,
        "external": sorted(set([r.get("id") for r in ext_res] + re.findall(r"https?://[^\s\"')<>]+", page))),
        "pui_classes": sorted(set(re.findall(r"\bpui-[a-z0-9-]+", page))),
        "custom_properties_defined": sorted(set(re.findall(r"(--[a-z0-9-]+)\s*:", allcss))),
        "custom_properties_used": sorted(set(re.findall(r"var\((--[a-z0-9-]+)", page))),
        "font_families": sorted(set(f.strip() for f in re.findall(r"font-family\s*:\s*([^;}\n]+)", page))),
        "fixed_colours": sorted(set(c.lower() for c in re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", page))),
        "counts": {"styles": len(styles), "scripts": len(scripts), "bytes": len(page)},
    }
    json.dump(inv, open(os.path.join(out, "inventory.json"), "w"), indent=2)
    print(json.dumps({"ok": True, "out": out, "counts": inv["counts"], "resources": len(resources),
                      "external": len(inv["external"]), "pui_classes": len(inv["pui_classes"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
