# Security review: chrissgon/ai-workbench, 2026-09-28

- Owner: eng-security-review (0.1, first real run; written in the skill's report format)
- Status: approved
- Scope: dependency alerts only (secrets, authentication, input handling and configuration not reviewed)
- Source: provider `providers/vcs/github.py alerts --state open`, run by the `dependabot-alerts` workflow (run 36367778232, artifact `dependabot-alerts`), fetched 2026-09-28; 30 open alerts
- By severity: critical 2, high 8, medium 14, low 6

Counts come from `skills/eng-security-review/scripts/triage_alerts.py` run on the artifact.

## Manifests
| Manifest | Open alerts | Packages | Shipped? | Installed or run? | Copied from | Evidence |
|----------|-------------|----------|----------|-------------------|-------------|----------|
| `skills/ops-ci-pipeline/evals/files/docsite/package.json` | 15 | nuxt, vitest | no: an eval fixture, copied into a scratch case folder per run | no | perfectui-doc | no lockfile in the folder or a parent (`lockfiles: []`, `parent_lockfiles: []`); `skills/ops-ci-pipeline/evals/evals.json` allows `npm test` and `npm run`, not `npm install`; `.github/workflows/*.yml` run no npm command |
| `skills/ops-ci-pipeline/evals/files/docsite-ci/package.json` | 15 | nuxt, vitest | no: same fixture, with a CI file | no | perfectui-doc | as above; its `npm ci` lines are in `docsite-ci/.github/workflows/ci.yml`, a nested file GitHub never runs (only the root `.github/workflows/` runs) |

perfectui-doc: the user checked on 2026-09-28 that it does not use these versions.

## Plan
| # | Manifest | Package | Declared | Alerts (numbers) | Max severity | Recommendation | Reason | Target version |
|---|----------|---------|----------|------------------|--------------|----------------|--------|----------------|
| 1 | `.../docsite/package.json` | vitest | 3.2.4 (devDependencies) | 19, 30 | critical | dismiss | `not_used` | (4.1.11 would clear them; a major) |
| 2 | `.../docsite-ci/package.json` | vitest | 3.2.4 (devDependencies) | 4, 15 | critical | dismiss | `not_used` | (4.1.11; a major) |
| 3 | `.../docsite/package.json` | nuxt | 4.1.0 (devDependencies) | 16 to 18, 20 to 29 | high | dismiss | `not_used` | (4.5.1) |
| 4 | `.../docsite-ci/package.json` | nuxt | 4.1.0 (devDependencies) | 1 to 3, 5 to 14 | high | dismiss | `not_used` | (4.5.1) |

Rejected: updating the fixtures. It changes the evals that read them and gains no security, and any pinned version will get new advisories.

## Dismissal comments
- Groups 1 and 3 (alerts 16 to 30): "Eval fixture of ops-ci-pipeline (skills/ops-ci-pipeline/evals/files/docsite), never installed: no lockfile, evals allow npm test/run but not npm install, repo CI never installs it. The real project it copies (perfectui-doc) does not use this version." (250 characters)
- Groups 2 and 4 (alerts 1 to 15): "Eval fixture of ops-ci-pipeline (skills/ops-ci-pipeline/evals/files/docsite-ci), never installed: no lockfile, evals allow npm test/run but not npm install, its nested CI file never runs. The real project it copies (perfectui-doc) does not use this version." (257 characters)

## Approval
- 2026-09-28: the user chose to dismiss all 30 as `not_used` ("1. A") and to dismiss them by hand on the alerts page from this list ("2. A"): the session's network replaces the token on calls to api.github.com, and the stored token is read-only.

## Results
| Alert | Action | Result |
|-------|--------|--------|
| 1 to 30 | dismiss `not_used` with the comment above | handed to the user |

## Proposed tasks
- none

## Assumptions
- none
