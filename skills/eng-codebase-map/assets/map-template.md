# Codebase map: {project}

- Owner: eng-codebase-map
- Status: draft
- Date: {YYYY-MM-DD}
- Scope: {root or focused directory}; {n} source files; measured with `scripts/map_codebase.py` (static imports only; framework auto-imports, dynamic imports and runtime injection are not counted)

## Summary

{five to eight lines: what the system is, stack, how it is organized, where requests enter, what it talks to}

## Structure

```
{top-level tree with one comment per directory, from the script's tree and your reading}
```

## Stack

| Layer | Technology | Evidence |
|-------|------------|----------|
| {runtime / framework / UI / state / styling / build / tests / deploy} | {name and version} | {manifest key or file} |

## Entry points and routes

| Entry | Path | What it starts |
|-------|------|----------------|

## Components

| Component | Files | Location | Script module | Imported by (afferent) | Imports (efferent) | Responsibility |
|-----------|-------|----------|---------------|------------------------|--------------------|----------------|

Afferent and efferent numbers are copied from the `modules` list printed by `map_codebase.py`; they are counted per module ({the limits the script prints}). {Name any component that is only part of a module and carries that module's numbers.}

## Main paths

### {Path 1 name}
1. `{file}` — {what happens}
2. `{file}` — ...
3. {external call or state} — {or "not visible statically"}

## Integration points

| System | Where | Purpose | Configured by |
|--------|-------|---------|---------------|

## Security boundaries

- Untrusted input enters at: {files}
- Secrets are read at: {files or "none found in code"}
- Runs on the server: {parts}; runs in the browser: {parts}
- Public surface: {routes, endpoints, published package entries}

## Observations

- {fact with location}

## Files read

- {path} — {why}
