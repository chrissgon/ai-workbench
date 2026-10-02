# Packs: what gets installed

Harnesses load the name and description of every installed skill into every session, and most cap that catalog and truncate beyond it. Installing everything always does not scale past a few dozen skills. A pack is the unit of installation: a list of skill patterns that an adapter resolves against `skills/` at install time.

```
packs/default.txt     everything except optional areas; what `install.sh` uses when no --pack is given
packs/all.txt         everything, optional areas included
packs/assistant.txt   the optional assistant area only
```

## Format

One pattern per line. `#` starts a comment.

- `eng-*` — glob on the skill name
- `area:engineering` — every skill whose `metadata.area` matches
- `!asst-*` — exclusion, applied after inclusions
- `biz-business-model` — an exact skill name

Resolve a pack with `python3 scripts/select_skills.py --pack <name>`; adapters accept `--pack <name>`. One pack is installed at a time: installing another pack removes what the earlier one installed and the new one does not select. A pack that selects no skill (today `assistant`: the area has no skill yet) is reported and installs nothing.

Add a pack when a real installation needs a different subset (a project that only does engineering, a marketing team). Do not add packs speculatively.
