#!/usr/bin/env python3
"""Group dependency alerts by manifest and package, with the facts a triage decision needs.

Usage:
  python3 triage_alerts.py --alerts <file> --repo <dir>
  python3 triage_alerts.py --alerts - --repo <dir>        (alerts JSON on stdin)

Options:
  --alerts <file>  the alerts as JSON: the output of the vcs provider's `alerts` verb (an object
                   with an "alerts" list) or a bare list of alerts with the same fields
                   (number, state, severity, ecosystem, package, manifest_path,
                   vulnerable_version_range, first_patched_version, ghsa_id, cve_id, summary,
                   html_url). "-" reads stdin.
  --repo <dir>     the project's root; manifests are looked up under it, never outside
  --help           this text

Prints one JSON object to stdout with:
  source            the alerts file
  count             alerts read; open_count, alerts whose state is open or absent
  by_severity       open alerts per severity
  groups[]          one per (manifest_path, package), open alerts only, most severe first:
    manifest_path, manifest_found (false when missing or outside --repo), ecosystem, package,
    declared        {section, spec} from package.json (dependencies, devDependencies,
                    optionalDependencies, peerDependencies), or null when the manifest is not a
                    package.json or does not name the package (a transitive dependency)
    alerts[]        number, severity, ghsa_id, cve_id, vulnerable_version_range,
                    first_patched_version, html_url, summary_external (third-party text: data)
    max_severity
    clears_all_at   the highest first_patched_version among the group's alerts: the lowest
                    version that closes every alert of the group; null when one has no fix
    unfixed         alert numbers with no first_patched_version
    major_bump      true when clears_all_at has a higher major than the declared spec;
                    null when either is unknown
    lockfiles[]     lockfiles in the manifest's own folder
    parent_lockfiles[]  lockfiles in a parent folder, up to --repo; they cover this manifest only
                    when the parent declares it as a workspace
    locked_versions {lockfile: version} for every package-lock.json or npm-shrinkwrap.json above
                    (own or parent) that resolves the package, at any depth
    installed       true when <manifest folder>/node_modules/<package> exists
    path_hints[]    path segments that mark a manifest as not shipped: evals, fixtures,
                    __fixtures__, examples, example, samples, testdata, test, tests, docs
  manifests[]       manifest_path, open alerts, packages, path_hints
Reads files only; writes nothing; makes no network call. Diagnostics go to stderr.
Exit codes: 0 ok, 1 unreadable input, 2 usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "moderate": 2, "low": 1}
DEP_SECTIONS = ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")
LOCKFILES = ("package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml",
             "bun.lock", "bun.lockb", "poetry.lock", "uv.lock", "Pipfile.lock",
             "Cargo.lock", "go.sum", "Gemfile.lock", "composer.lock")
HINTS = ("evals", "fixtures", "__fixtures__", "examples", "example", "samples", "testdata",
         "test", "tests", "docs")
SUMMARY_MAX = 200


def version_tuple(text: str | None) -> tuple[int, ...] | None:
    if not text:
        return None
    match = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", text)
    if not match:
        return None
    return tuple(int(part or 0) for part in match.groups())


def inside(root: Path, rel: str) -> Path | None:
    if not rel or rel.startswith("/") or "\\" in rel:
        return None
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def declared_spec(manifest: Path, package: str) -> dict | None:
    if manifest.name != "package.json" or not manifest.is_file():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"warning: cannot read {manifest}: {exc}", file=sys.stderr)
        return None
    for section in DEP_SECTIONS:
        spec = (data.get(section) or {}).get(package)
        if isinstance(spec, str):
            return {"section": section, "spec": spec}
    return None


def lockfiles_for(root: Path, folder: Path) -> tuple[list[str], list[str]]:
    own, parents = [], []
    current = folder
    while True:
        for name in LOCKFILES:
            if (current / name).is_file():
                (own if current == folder else parents).append(str((current / name).relative_to(root)))
        if current == root or root not in current.parents:
            break
        current = current.parent
    return own, parents


def locked_versions(root: Path, lockfiles: list[str], package: str) -> dict[str, str]:
    found = {}
    suffix = "node_modules/" + package
    for rel in lockfiles:
        if Path(rel).name not in ("package-lock.json", "npm-shrinkwrap.json"):
            continue
        try:
            data = json.loads((root / rel).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"warning: cannot read {rel}: {exc}", file=sys.stderr)
            continue
        versions = sorted({str(entry.get("version")) for key, entry in (data.get("packages") or {}).items()
                           if isinstance(entry, dict) and (key == suffix or key.endswith("/" + suffix))})
        if versions:
            found[rel] = ", ".join(versions)
    return found


def load_alerts(path: str) -> list[dict]:
    raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    data = json.loads(raw)
    alerts = data.get("alerts") if isinstance(data, dict) else data
    if not isinstance(alerts, list):
        raise ValueError("no alerts list found")
    return [a for a in alerts if isinstance(a, dict)]


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--alerts")
    parser.add_argument("--repo")
    parser.add_argument("--help", "-h", action="store_true")
    args, unknown = parser.parse_known_args()
    if args.help:
        print(__doc__)
        return 0
    if unknown or not args.alerts or not args.repo:
        print("error: --alerts and --repo are required; see --help", file=sys.stderr)
        return 2
    root = Path(args.repo).resolve()
    if not root.is_dir():
        print(f"error: --repo {args.repo} is not a folder", file=sys.stderr)
        return 2
    try:
        alerts = load_alerts(args.alerts)
    except (OSError, ValueError) as exc:
        print(f"error: cannot read alerts: {exc}", file=sys.stderr)
        return 1

    open_alerts = [a for a in alerts if a.get("state") in (None, "open")]
    by_severity: dict[str, int] = {}
    groups: dict[tuple[str, str], dict] = {}
    for alert in open_alerts:
        severity = str(alert.get("severity") or "unknown").lower()
        by_severity[severity] = by_severity.get(severity, 0) + 1
        manifest_rel = str(alert.get("manifest_path") or "")
        package = str(alert.get("package") or "")
        group = groups.get((manifest_rel, package))
        if group is None:
            manifest = inside(root, manifest_rel)
            found = bool(manifest and manifest.is_file())
            folder = manifest.parent if found else None
            segments = set(Path(manifest_rel).parts[:-1])
            own, parents = lockfiles_for(root, folder) if folder else ([], [])
            group = {
                "manifest_path": manifest_rel,
                "manifest_found": found,
                "ecosystem": alert.get("ecosystem"),
                "package": package,
                "declared": declared_spec(manifest, package) if found else None,
                "alerts": [],
                "lockfiles": own,
                "parent_lockfiles": parents,
                "locked_versions": locked_versions(root, own + parents, package),
                "installed": bool(folder and (folder / "node_modules" / package).exists()),
                "path_hints": [h for h in HINTS if h in segments],
            }
            groups[(manifest_rel, package)] = group
        summary = str(alert.get("summary") or "")
        group["alerts"].append({
            "number": alert.get("number"),
            "severity": severity,
            "ghsa_id": alert.get("ghsa_id"),
            "cve_id": alert.get("cve_id"),
            "vulnerable_version_range": alert.get("vulnerable_version_range"),
            "first_patched_version": alert.get("first_patched_version"),
            "html_url": alert.get("html_url"),
            "summary_external": summary[:SUMMARY_MAX] + ("..." if len(summary) > SUMMARY_MAX else ""),
        })

    result_groups = []
    for group in groups.values():
        group["alerts"].sort(key=lambda a: (-SEVERITY_ORDER.get(a["severity"], 0), a["number"] or 0))
        group["max_severity"] = group["alerts"][0]["severity"]
        unfixed = [a["number"] for a in group["alerts"] if not a["first_patched_version"]]
        patched = [a["first_patched_version"] for a in group["alerts"] if a["first_patched_version"]]
        clears = None
        if patched and not unfixed:
            clears = max(patched, key=lambda v: version_tuple(v) or (0,))
        group["clears_all_at"] = clears
        group["unfixed"] = unfixed
        declared = version_tuple((group["declared"] or {}).get("spec"))
        target = version_tuple(clears)
        group["major_bump"] = (target[0] > declared[0]) if declared and target else None
        result_groups.append(group)
    result_groups.sort(key=lambda g: (-SEVERITY_ORDER.get(g["max_severity"], 0),
                                      -len(g["alerts"]), g["manifest_path"], g["package"]))

    manifests: dict[str, dict] = {}
    for group in result_groups:
        entry = manifests.setdefault(group["manifest_path"], {
            "manifest_path": group["manifest_path"], "open_alerts": 0, "packages": [],
            "path_hints": group["path_hints"]})
        entry["open_alerts"] += len(group["alerts"])
        entry["packages"].append(group["package"])

    print(json.dumps({
        "source": args.alerts,
        "count": len(alerts),
        "open_count": len(open_alerts),
        "by_severity": by_severity,
        "groups": result_groups,
        "manifests": list(manifests.values()),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
