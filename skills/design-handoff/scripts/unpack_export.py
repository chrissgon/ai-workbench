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
Prints the inventory summary as JSON. Exit codes: 0 ok, 1 unreadable or refused export, 2 usage error.

The export is content written by someone else, so its manifest is checked before anything is
written: every resource id must match [a-z0-9-]+ (an id such as ../../src/index or /etc/x is
refused and nothing is unpacked), every resolved path must stay inside <dir>/resources, and a
decoded or decompressed resource larger than --max-bytes (default 52428800, 50 MB) is refused.
"""
import base64
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


def main(argv):
    if "--help" in argv or "-h" in argv or not argv:
        print(__doc__)
        return 0 if argv else 2
    try:
        args = {f: argv[argv.index(f) + 1] for f in ("--file", "--out", "--max-bytes") if f in argv}
        limit = int(args.get("--max-bytes", MAX_BYTES))
    except (IndexError, ValueError):
        print("Error: --file, --out and --max-bytes need a value. See --help.", file=sys.stderr)
        return 2
    if "--file" not in args or "--out" not in args:
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
