# Security policy

This repository holds instructions and scripts that AI tools execute with access to a terminal, files and the network. A flaw here can make a tool leak a credential, act without the user's approval, or follow instructions hidden in content it reads.

## Reporting a vulnerability

Report it privately through GitHub: the repository's **Security** tab, **Report a vulnerability**. Do not open a public issue.

Include what is affected (a skill, script, provider or adapter), how to reproduce it, and what an attacker gains. You will get an answer within seven days.

## What counts

- A skill, agent or script that sends data, pushes, publishes or runs a command the user did not approve.
- A credential that can be printed, logged or written to a file.
- Content (a web page, a ticket, a pull request comment) that makes a skill act on instructions inside it.
- A way around `scripts/security_scan.py` or the pre-commit hook that lets one of the above land unnoticed.

## What the repository already does

- `scripts/validate.py` runs `scripts/security_scan.py` on every commit (through `.githooks/pre-commit`) and in CI, including a scan of the whole history for secrets.
- Skills that act outside the repository declare it in `metadata.side_effects` and ask once before acting (`contracts/environment.md`).
- Providers read credentials only from the environment or the OS secret store (`providers/CONTRACT.md`).
