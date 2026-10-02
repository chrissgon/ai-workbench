# Shared references

Cross-cutting knowledge loaded by more than one skill. Each file states at the top which skills load it and at which step.

Skills reference these files with a relative path from the skill folder (`../../shared/references/security.md`). Adapters that copy skills instead of linking them must copy `shared/` alongside.

Files are added when a second skill needs the same knowledge, never speculatively. Present today: `security.md` only (the security checklist; `core-skill-creator`, `core-security-audit`). References for accessibility, performance, privacy, documentation, prompting and research method do not exist yet; each is added when a second skill needs it.
