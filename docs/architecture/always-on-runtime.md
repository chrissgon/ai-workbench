# Always-on runtime: where the social agent runs once it leaves the Mac

- Status: proposal (backlog PB8), for the operator's decision
- Date: 2026-09-30
- Reads: `contracts/runtime.md`, `scripts/runtime.py`, `providers/store/`, `providers/scheduler/`, `providers/mailbox/`, `providers/publisher/`, `adapters/claude-code/run-agent.sh`
- Prices: every number comes from the vendor's own page, accessed 2026-09-30, listed under Sources. Anything else is marked **Assumption**.

## 1. The question

The runtime works on a Mac: launchd fires `scripts/runtime.py tick` every 10 minutes; the tick reads new LinkedIn comment notifications, runs the `social-manager` agent read-only through the Claude Code CLI, lets `policy_gate.py` decide, and replies through the LinkedIn provider or queues the comment in the inbox. Scheduled posts run as one-shot launchd jobs.

The Mac's main limit: launchd misses a `StartInterval` firing while the Mac sleeps (`man 5 launchd.plist`, quoted in `providers/scheduler/README.md`), and the Mac must be on and logged in. The rehearsal of 2026-09-30 proved the rest works unattended: a one-shot job and a recurring job every 5 minutes read the LinkedIn token from the login keychain through launchd and `uv` (the first read took about 95 seconds, the next ones about 10). An always-on host removes the sleep limit. This document compares where to put it, what each option costs, and what it changes in the code.

## 2. What has to move

| Piece | Today | What a host must provide |
|-------|-------|--------------------------|
| Trigger | launchd, every 10 min, snapshot and hash of the approved command, lock, timeout | a timer (10 min) and 3 fixed times a week, no overlap, bounded run time |
| Runtime | `scripts/runtime.py`, standard library, uses `subprocess` and `fcntl` | Python 3, subprocesses, a writable folder |
| Store | `providers/store/sqlite.py`, WAL, `BEGIN IMMEDIATE` | a local disk, or another store provider behind the same CLI verbs |
| Agent run | `claude -p` with `--tools Read,Glob,Grep` | the CLI and its credentials, or a different adapter |
| Mailbox | Gmail API, `gmail.readonly` | outbound HTTPS, 3 secrets |
| Publisher | LinkedIn API, 60-day token without refresh, idempotency ledger file | outbound HTTPS, 1 secret, a persistent ledger |
| Project files | policy (hash-bound), voice, brand, `state.md`, `engagement-log.jsonl` | read at run time; the log is written |
| The person | `runtime.py inbox` / `approve`; macOS notifications | a way to run `approve` where the store lives; another notification channel |

Workload: 4,320 to 4,464 ticks a month (every 10 minutes), 0 to 900 agent runs (0 to 30 comments a day), 12 to 13 posts.

## 3. The decision that sets the price: how the model is called

### 3.1 Two ways

- **A. Keep the Claude Code CLI** (today's adapter). Claude Code needs "4 GB+ RAM" [S34], which puts the cheapest server at Hetzner CX23 (€5.99/month) and everything else at $20 to $29/month. On a server it signs in with `claude setup-token`, "a one-year OAuth token" documented for "CI pipelines, scripts" [S30]. But the Consumer Terms forbid access "through automated or non-human means, whether through a bot, script, or otherwise" except "via an Anthropic API Key or where we otherwise explicitly permit it" [S32], and the Claude Code legal page says subscription OAuth is "designed to support ordinary use" [S33]. A bot answering strangers every 10 minutes is closer to the prohibition than to ordinary use. **This is the operator's decision, not settled by the sources.**
- **B. A tool-free API adapter** (to build: `adapters/api/run-agent.*`). One Messages API or OpenRouter call with the agent, the skill and the brand files in the prompt and no tools at all. It runs anywhere (no 4 GB rule), keeps "the model has no tool that acts" true by construction, costs per token, and is covered by the API terms.

### 3.2 Cost per reply (15,000 input and 400 output tokens, one call, no cache)

| Model | Input / output per MTok | Per reply | 300 replies/month | 900 replies/month |
|-------|-------------------------|-----------|-------------------|-------------------|
| Claude Sonnet 5.5 | $2 / $10 [S27] | $0.034 | $10.20 | $30.60 |
| Claude Haiku 4.5 | $1 / $5 [S27] | $0.017 | $5.10 | $15.30 |
| DeepSeek V3.2 (OpenRouter) | $0.28 / $0.42 [S29] | $0.0044 | $1.31 | $3.93 |

Arithmetic, Sonnet: 15,000 × $2/1e6 + 400 × $10/1e6 = $0.030 + $0.004. Caching barely helps: the 5-minute cache expires between 10-minute ticks, and the 1-hour cache breaks even at about two replies an hour [S28]. The runtime's `daily_cost_cap_usd` bounds any of these. The CLI path costs more than one call (tool turns resend context); its real cost per reply was measured on 2026-09-30 in the model comparison (section 6).

## 4. The options

### 4.1 Stay on the Mac (today)

- Cost: $0 infrastructure; the model on the operator's plan.
- Limits: the Mac must be awake and logged in; missed firings during sleep; one keychain click per new binary.
- Fit: good for the first weeks, while the e-mail trigger and the policy are proven.

### 4.2 A small VPS with systemd (same code)

- Mapping: a systemd timer runs `runtime.py tick`; SQLite on the local disk exactly as on the Mac; secrets in a 0600 environment file read by `resolver.py`; `approve` over SSH.
- New code: a `systemd` scheduler provider mirroring `launchd.py` (snapshot, hash, lock, timeout), a notification channel (e-mail), and adapter B on boxes under 4 GB.
- Cost: DigitalOcean $4 (512 MiB) or $6 (1 GiB) [S22]; Lightsail $3.50 to $7 [S17]; EC2 t4g.nano $7.36 with its IPv4 [S9][S10]. With the CLI (4 GB): Hetzner CX23 €5.99 (EU; its product page marked the plan "not available" on 2026-09-30 [S21]), DigitalOcean or Lightsail $24, EC2 t4g.medium $28.82.
- Ops: patching, SSH, backups (`sqlite3 .backup`). Lock-in: lowest. Security: every secret and the store on one box; the blast radius is the box.

### 4.3 AWS Lambda + EventBridge Scheduler (serverless)

- Mapping: EventBridge Scheduler `rate(10 minutes)` and cron schedules in the posting time zone (IANA) [S5]; one Python Lambda with reserved concurrency 1 as the lock (**Assumption**); secrets in SSM Parameter Store; state in DynamoDB (a new store provider) or the SQLite file in S3 with conditional writes (`If-Match`, 412 on a race) [S13]. Never SQLite on EFS: SQLite warns that locks "have been known to operate incorrectly for some network filesystems" [S12].
- Cost: about 20,256 GB-s and 5,376 requests a month with adapter B at 512 MB, inside Lambda's always-free "400,000 GB-seconds per month" [S3]: **$0**; about $0.30 to $1.60 without it or with Secrets Manager. Accounts created from 2025-07-15 get credits on a Free plan that closes after 6 months, so an always-on agent belongs on the Paid plan; the always-free limits still apply [S1].
- New code: large. A store provider (or S3 sync), a scheduler provider, packaging, adapter B, the publisher's ledger moved into the store. Lambda's 15-minute limit [S4] means per-tick work is capped by time as well as count.
- Ops: lowest at run time. Lock-in: medium (AWS code stays in providers).

### 4.4 Other serverless hosts

- **Google Cloud Run jobs + Cloud Scheduler:** $0 inside the free tier, about $1.36 without it [S39][S40]; the state layer is the hard part, as on Lambda.
- **Cloudflare Workers + D1:** $0 or $5 [S37][S38]; Python Workers went GA on 2026-09-21 on Pyodide [S23][S25]. The runtime calls providers through subprocesses, which Pyodide is not documented to support (**Assumption**): a rewrite.
- **Fly.io:** $1.94 to $5.70 a month for a small Machine with a volume, $20.70 at 4 GB; no ongoing free allowance, card required [S43][S44].
- **GitHub Actions cron:** scheduled runs "can be delayed during periods of high loads" and "some queued jobs may be dropped" [S45]; each job rounds up to a minute [S47], about $15 to $20 a month on a private repository. Not reliable enough for a 10-minute tick.

### 4.5 Workflow-automation platforms

| Platform | Monthly fee for this workload | Keeps the gate and the store in our code? | LinkedIn reply | Model |
|----------|-------------------------------|-------------------------------------------|----------------|-------|
| n8n self-hosted (Community Edition) | €0 + a VPS | yes, only by running `runtime.py` through Execute Command, which n8n 2.0 disables by default and which needs a custom image with Python | HTTP Request node, or our provider | our adapter |
| n8n Cloud Starter | €20 billed annually for 2,500 executions; empty Gmail polls do not count | no: Cloud Python "doesn't allow users to import any Python libraries", no Execute Command | HTTP Request node | API key |
| Make Core | $9 to $18.82 (polling alone uses 4,320 credits) | no: pasted code, 30 s, no files | "Make an API Call" | API key |
| Zapier Professional | $89 to $193.50 | no | none built in | API key |
| Pipedream Advanced | $49 to $74, overage price not published | partly: real Python steps | "Create Comment" with `parentComment` | API key |

Sources: n8n [pricing, Code node, Execute Command, 2.0 and 3.0 changelogs, Gmail and LinkedIn nodes], Make [pricing, Code app, LinkedIn app], Zapier [pricing, Python code], Pipedream [pricing, LinkedIn app], all listed under Sources.

What the platforms add is a visual run history and, in n8n, a phone-friendly approval form. What they cost the design: on SaaS the gate becomes a pasted copy outside `validate.py`, the security scan and the offline tests; the hash then binds whatever was pasted into the platform, not the file the person approved; the store's atomic claim and unique keys move to platform storage whose guarantees are not documented. n8n's "AI Agent" node with a LinkedIn tool attached would give the model a publishing tool, which `contracts/runtime.md` forbids. Self-hosted n8n keeps the design only by reducing itself to a scheduler with a UI, which systemd does with less surface.

## 5. Comparison

| Option | Infrastructure per month | Model | Code change | Run-time ops | Lock-in | Fit |
|--------|--------------------------|-------|-------------|--------------|---------|-----|
| Mac | $0 | CLI on the plan | none | Mac awake | none | now |
| VPS + adapter B | $4 to $7 | API key | small | patching, SSH | lowest | **recommended next** |
| VPS 4 GB + CLI | €5.99 to $29 | CLI on the plan (terms question) | small | patching, SSH | lowest | only if the operator settles the terms question |
| Lambda + EventBridge + adapter B | $0 to $1.60 | API key | large | lowest | medium | later, if zero ops matters |
| Cloud Run / Fly.io | $0 to $5.70 | API key | medium to large | low | medium / low | alternatives to the VPS |
| Cloudflare Workers | $0 or $5 | API key | rewrite | lowest | high | no |
| GitHub Actions | $15 to $20 | either | medium | delays, drops | medium | no |
| n8n self-hosted | €0 + VPS | our adapter | small, plus a custom image | highest | low | only for the approval UI |
| n8n Cloud, Make, Zapier, Pipedream | $9 to $193 | API key | rewrite of the gate and store | low | high | no |

## 6. Recommendation

1. **Now: stay on the Mac** until three things are proven: the e-mail trigger (or pasted links), a first reply sent, and 7 days of unattended ticks.
2. **Next: a small VPS with a tool-free API adapter (B).** Same runtime, store, gate and providers; new pieces are the `systemd` scheduler provider, adapter B, and an e-mail notification. Infrastructure $4 to $7 a month; model cost per section 3.2, capped by `daily_cost_cap_usd`.
3. **Model for adapter B:** chosen from a comparison of models on real comments (2026-09-30; `docs/decisions.md`), with the gate unchanged whatever the model.
4. **Not recommended:** workflow SaaS as the core (the gate and the hash-bound approval would leave the repository), Cloudflare Workers (rewrite), GitHub Actions (drops).

Decisions for the operator: the terms question (CLI on the plan vs an API key) and the host.

## 7. What every option needs

- `runtime.py approve` where the store lives (SSH on a VPS; credentials against DynamoDB on Lambda).
- The publisher's idempotency ledger next to the store.
- A notification channel other than macOS.
- The LinkedIn token renewed by hand every 60 days on the Mac (browser and localhost callback), then copied to the host.
- `gmail.readonly` reads the whole mailbox: the largest privacy risk of the three secrets; keep it readable only by the tick's identity.

## Sources (accessed 2026-09-30)

- [S1] AWS Free Tier: https://aws.amazon.com/free/
- [S3] AWS Lambda pricing: https://aws.amazon.com/lambda/pricing/
- [S4] Lambda quotas: https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html
- [S5] EventBridge pricing and Scheduler schedule types: https://aws.amazon.com/eventbridge/pricing/ , https://docs.aws.amazon.com/scheduler/latest/UserGuide/schedule-types.html
- [S9] AWS EC2 on-demand price feed, US East (N. Virginia) Linux: https://b0.p.awsstatic.com/pricing/2.0/meteredUnitMaps/ec2/USD/current/ec2-ondemand-without-sec-sel/US%20East%20(N.%20Virginia)/Linux/index.json
- [S10] Amazon VPC pricing (public IPv4): https://aws.amazon.com/vpc/pricing/
- [S12] SQLite over a network: https://sqlite.org/useovernet.html
- [S13] S3 conditional writes: https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html
- [S17] Lightsail pricing: https://aws.amazon.com/lightsail/pricing/
- [S21] Hetzner Cloud cost-optimized plans: https://www.hetzner.com/cloud/cost-optimized/
- [S22] DigitalOcean Droplet pricing: https://www.digitalocean.com/pricing/droplets
- [S23] Cloudflare Python Workers GA: https://blog.cloudflare.com/python-workers-ga/
- [S25] How Python Workers work: https://developers.cloudflare.com/workers/languages/python/how-python-workers-work/
- [S27] Anthropic pricing: https://platform.claude.com/docs/en/about-claude/pricing
- [S28] Anthropic prompt caching: https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- [S29] OpenRouter model listing for deepseek/deepseek-v3.2: https://openrouter.ai/api/v1/models
- [S30] Claude Code authentication: https://code.claude.com/docs/en/authentication
- [S32] Anthropic Consumer Terms: https://www.anthropic.com/legal/consumer-terms
- [S33] Claude Code legal and compliance: https://code.claude.com/docs/en/legal-and-compliance
- [S34] Claude Code setup: https://code.claude.com/docs/en/setup
- [S37] Cloudflare Workers pricing: https://developers.cloudflare.com/workers/platform/pricing/
- [S38] Cloudflare D1 pricing: https://developers.cloudflare.com/d1/platform/pricing/
- [S39] Cloud Run pricing: https://cloud.google.com/run/pricing
- [S40] Cloud Scheduler pricing: https://cloud.google.com/scheduler/pricing
- [S43] Fly.io pricing: https://docs.fly.io/about/pricing/
- [S44] Fly.io free trial: https://docs.fly.io/about/free-trial/
- [S45] GitHub Actions schedule event: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- [S47] GitHub Actions runner pricing: https://docs.github.com/en/billing/reference/actions-runner-pricing
- n8n pricing: https://n8n.io/pricing/ ; Code node: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.code ; Execute Command: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.executecommand/ ; 2.0 changes: https://docs.n8n.io/changelog/v20-breaking-changes ; 3.0 changes: https://docs.n8n.io/changelog/v30-breaking-changes ; executions: https://docs.n8n.io/build/understand-workflows/understand-executions ; LinkedIn node: https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.linkedin/ ; license: https://github.com/n8n-io/n8n/blob/master/LICENSE.md
- Make pricing: https://www.make.com/en/pricing ; Code app: https://apps.make.com/code ; LinkedIn app: https://apps.make.com/linkedin
- Zapier pricing: https://zapier.com/pricing ; Python in Zaps: https://help.zapier.com/hc/en-us/articles/8496326417549-Use-Python-code-in-Zaps ; LinkedIn integrations: https://zapier.com/apps/linkedin/integrations
- Pipedream pricing: https://pipedream.com/pricing ; LinkedIn app: https://pipedream.com/apps/linkedin ; Workday acquisition: https://newsroom.workday.com/2025-11-19-Workday-Signs-Definitive-Agreement-to-Acquire-Pipedream
- Full research notes, with every figure's arithmetic and the assumptions: [research/2026-09-30-hosting.md](research/2026-09-30-hosting.md) and [research/2026-09-30-automation-platforms.md](research/2026-09-30-automation-platforms.md).
