# Shared references

Cross-cutting knowledge loaded by many skills: `security.md`, `accessibility.md`, `performance.md`, `privacy.md`, `documentation.md`, `prompting.md`, `research-method.md`. Each file states at the top which skills load it and at which step.

Skills reference these files with a relative path from the skill folder (`../../shared/references/security.md`). Adapters that copy skills instead of linking them must copy `shared/` alongside.

Files are added when a second skill needs the same knowledge, never speculatively. Present today: `security.md` (the security checklist; `core-skill-creator`, `core-security-audit`).
