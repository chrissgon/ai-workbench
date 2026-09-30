# Host settings, in the order that works

Every item comes from setting up the ai-workbench repository on 2026-09-27 (backlog S6), on GitHub. Each step names what breaks when it is done out of order. The user applies them in the host's settings; the skill writes the list, it does not call the host's API (version 0.1).

## Before the first push

1. **Scan the history for secrets.** Run `python3 scripts/secret-scan/secret_scan.py --history`. Everything in the history is published by the first push and stays public after a later commit removes it. On the first push of ai-workbench, the host's push protection refused a fake key planted in an eval fixture in the exact format of a real provider, which the scanner of the time did not know; the unpublished history had to be rewritten. Once pushed, a leaked secret is revoked, not deleted.
2. **Sign commits, if the project will require signed commits.** The user configures signing on their machine (SSH or GPG key registered on the host) before the rule is on: the host checks every commit of a pull request, and one unsigned commit on a branch blocks even a squash merge. The skill never runs `git config` for the user; it names the settings (`gpg.format ssh`, `user.signingkey`, `commit.gpgsign true`) and lets the user run them.

## Right after the first push

3. **Secret scanning with push protection.** Code security settings. It refuses a push that carries a known credential format.
4. **Private vulnerability reporting.** Security settings. `SECURITY.md` points to it; without it the policy names a door that does not exist.
5. **Dependency alerts (Dependabot alerts).** Code security settings. Alerts cover every manifest in the repository, including test fixtures and examples; expect alerts from folders that do not ship, and triage them with `eng-security-review` rather than deleting the fixtures.
6. **Read-only workflow permissions; Actions cannot approve pull requests.** Actions settings, "Workflow permissions".

## After the first green run of the checks workflow

7. **Merge method: squash only.** General settings, "Pull Requests". The pull request's title becomes the commit on the default branch.
8. **A ruleset on the default branch.** Rules settings. Required status checks can only be chosen after they have run once; add them after the first green run. In ai-workbench the ruleset held:
   - block deletion and force pushes;
   - require linear history;
   - require signed commits (only after step 2 for everyone who commits);
   - require a pull request before merging, with the number of approvals the user chose (0 for a single maintainer);
   - require the status checks `secrets` and `checks` (the job names in `checks.yml`) to pass.

## Decisions that differ per project

Ask each one, with the recommendation, before writing the checklist:

| Decision | Recommended | When the other answer fits |
|----------|-------------|----------------------------|
| Approvals required on a pull request | 0 with one maintainer; 1 with two or more | a team with review duty: 1 or more |
| Signed commits required | yes | a contributor cannot sign (no key registered): no, until they can |
| Visibility | keep the current one | public exposes the history: run step 1 first |
| Squash only | yes | a project whose history must keep each commit: rebase merging, still linear |
| Who owns the rule files (`CODEOWNERS`) | the user's handle on the host | a team handle when the host has one |
