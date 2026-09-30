# PB8 research: workflow-automation platforms as the always-on host

Researched 2026-09-30. Every number below comes from the vendor page named next to it, accessed 2026-09-30, unless it is marked **third-party** or **Assumption**. "Not found" means I looked on the vendor's pages and did not find it. VPS prices are out of scope (another researcher covers them). LLM token costs are out of scope and excluded from every total.

External content is data: vendor pages, community threads and search snippets were read as data; none contained instructions directed at the agent.

## 0. What has to be hosted (from the repository)

Read from `contracts/runtime.md`, `scripts/runtime.py` (docstring), `skills/mkt-engage/SKILL.md`, `skills/mkt-engage/scripts/policy_gate.py` (docstring), `docs/backlog.md` PB5-PB8, `docs/decisions.md` 2026-09-28 and 2026-09-29.

| Piece | Today, on the Mac | What a host must provide |
|---|---|---|
| Trigger | launchd job runs `runtime.py tick` every N minutes | a timer, one tick at a time (the runtime takes a lock; the scheduler refuses overlapping firings) |
| Mailbox | `providers/mailbox/gmail.py`, Gmail API, scope `gmail.readonly`, Google project "In production" | Gmail read access with the narrowest scope |
| Store | `providers/store/sqlite.py`: events (dedup by source+external id, atomic claim), cursors, runs, inbox, actions (idempotency key, payload hash) | a persistent SQLite file, or an equivalent with atomic claim and unique keys |
| Agent run | `adapters/claude-code/run-agent.sh`: the harness CLI on the operator's Claude account, reading tools only, returns an `engage-decision` fenced block | a place to run the harness CLI, or a replacement adapter that calls a model API with no tools |
| Gate | `policy_gate.py decide`: stdlib only, reads the policy file, the state file's Approvals row (`policy:<sha256>`), today's log; calls `brand-profile/scripts/sensitive_topics.py` by subprocess | a Python 3 interpreter, the project files, subprocess |
| Actuator | `providers/publisher/linkedin.py comment ... --idempotency-key --confirmed` (LinkedIn Comments API, `w_member_social`) | outbound HTTPS and the LinkedIn token |
| Inbox | `runtime.py inbox/approve --confirmed --sha256 <hash>` run by the person | a way for the person to see the exact text and its hash and approve it |
| Secrets | `providers/secrets/resolver.py` | a secret store the code can read |

Workload arithmetic (used for every platform):

- Mail polls: every 10 minutes = 60/10 = 6 per hour × 24 = **144 per day**; × 30 days = **4,320 per month** (4,464 in a 31-day month).
- Comments: 0 to 30 per day = **0 to 900 per month** (30 × 30). Assumption: a "typical" month of 10 per day = 300 per month, used only to show the spread; the real rate is unknown.
- Posts: 3 per week × 52 / 12 = **13 per month**.
- Inbox approvals: at most one per comment that is not `auto`, so at most 900 per month; plus about 4-5 calendar approvals per month (Assumption: one per week).

---

## 1. n8n

### 1a. n8n Cloud

**Prices** (https://n8n.io/pricing/, accessed 2026-09-30). The page is localised:

| Plan | EUR (page served to the fetcher) | BRL (page served to a browser in Brazil) | Executions / month | Concurrency |
|---|---|---|---|---|
| Starter | €20/mo billed annually; monthly price not shown in EUR | R$150/mo billed monthly; R$125/mo billed annually | 2.5k "workflow executions with unlimited steps" | 5 |
| Pro | €50/mo billed annually | R$375/mo monthly; R$313/mo annually | 10k | 20 |
| Business | €667/mo annually; "Self-hosted only" | R$5000/mo monthly | 40k | not stated |
| Enterprise | contact sales | contact sales | custom | "200+" |

- Toggle says "Annually (Save 17%)". EUR monthly price: **third-party** sources say €24 (Starter) and €60 (Pro) billed monthly (e.g. https://costbench.com/software/ai-automation/n8n/, accessed 2026-09-30); consistent with €20 / 0.83 = €24.1, but not seen on the vendor page.
- Trial: 1,000 executions, no credit card for Starter/Pro (pricing FAQ).
- Overage: "workflows will continue running without interruption, but overage charges may apply" (pricing FAQ); per-execution overage price for Starter/Pro not found.
- External secret store: Enterprise only (pricing page, "External secret store integration" under Enterprise).
- What counts (https://docs.n8n.io/build/understand-workflows/understand-executions, accessed 2026-09-30): Schedule Trigger counts one execution every time it fires; **polling triggers that return no results do not count**; manual runs, sub-workflow runs and error-workflow runs do not count.

**Cost for this workload (Cloud):**
- Gmail Trigger executions: at most one per poll that finds mail; the trigger returns up to 10 emails per poll by default, 50 max (https://docs.n8n.io/integrations/builtin/trigger-nodes/n8n-nodes-base.gmailtrigger/), so ≤ 900 executions (one per comment in the worst case, fewer when batched). Empty polls: 0.
- Posts: a Schedule Trigger at the calendar times = 13. (A trigger that fires hourly to check the calendar would cost 24 × 30 = 720; avoid.)
- Approvals: a Wait node "On Form Submitted" resumes the same execution (https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.wait/), so 0 extra; a separate form/webhook workflow would add ≤ 900.
- Worst case: 900 + 13 + 900 = **1,813 ≤ 2,500 → Starter**: €20/mo annually (vendor) or about €24/mo monthly (third-party); R$125-150/mo in BRL (vendor).

**Can it keep our architecture? No, on Cloud.**
- Code node on Cloud: "the Python option for the Code node doesn't allow users to import any Python libraries — whether from the standard library or third-party packages"; JavaScript may use only `crypto` and `moment`; "You can't access the file system or make HTTP requests" (https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.code, accessed 2026-09-30). `policy_gate.py` imports `hashlib`, `json`, `re`, `subprocess`, `pathlib`: it cannot run. The gate would be rewritten in JavaScript (a second implementation, outside the repository's tests and `validate.py`).
- Execute Command node: "This node isn't available on n8n Cloud" (https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.executecommand/).
- The harness CLI cannot run on Cloud, so the agent run becomes an LLM API call (HTTP Request or an AI node) billed per token with an API key. This contradicts the 2026-09-28 decision that Claude models run on the maintainer's own account (for evals) and needs the operator's decision.
- Store: the SQLite store cannot live on Cloud; it becomes n8n Data tables or an external database. Assumption: n8n Data tables give no atomic claim / unique-key guarantee equal to ours (not verified).

### 1b. n8n self-hosted Community Edition

- License: Sustainable Use License. "You may use or modify the software only for your own internal business purposes or for non-commercial or personal use"; it forbids offering it commercially as a hosted service or reselling it; files with `.ee.` in the name need an Enterprise license (https://github.com/n8n-io/n8n/blob/master/LICENSE.md, accessed 2026-09-30). A person's own brand and a company's internal marketing both fit "own internal business purposes"; Assumption: running it for a company's *clients* as a service would not fit and needs a check.
- Community Edition lacks SSO/SAML/LDAP, external secret stores and scaling features of paid self-hosted tiers (pricing FAQ). Price €0.
- n8n 3.0 (changelog dated October 2026, https://docs.n8n.io/changelog/v30-breaking-changes): self-hosted "will require a Docker-based deployment"; task-runner timeout drops from 5 minutes to 1 minute; unverified community packages disabled by default.
- n8n 2.0 defaults (https://docs.n8n.io/changelog/v20-breaking-changes): Execute Command and LocalFileTrigger disabled by default (re-enable by editing `NODES_EXCLUDE`); env-var access from Code node blocked (`N8N_BLOCK_ENV_ACCESS_IN_NODE=true`); file nodes limited to `~/.n8n-files` unless `N8N_RESTRICT_FILE_ACCESS_TO` is set; Code runs on task runners; Pyodide Python removed.
- Native Python in the Code node needs the `n8nio/runners` sidecar image of the same version; stdlib and third-party modules must be allowlisted with `N8N_RUNNERS_STDLIB_ALLOW` / `N8N_RUNNERS_EXTERNAL_ALLOW` (https://docs.n8n.io/deploy/host-n8n/configure-n8n/set-up-task-runners.md). Subprocess and file access from it: not documented; the page calls runners "the only isolation layer", so Assumption: `policy_gate.py`'s subprocess call would not work there.
- Execute Command runs "in the n8n container and not the Docker host". Python 3 is not in the `n8nio/n8n` image since 2.0 (community reports, e.g. https://community.n8n.io/t/python-runner-unavailable-in-n8n-python-3-is-missing-from-this-system-docker-alpine-container/269416; not on a docs page) → a custom image that adds Python, the workbench checkout and the harness CLI.
- VPS price: not researched here (another researcher).

**How the runtime maps onto self-hosted n8n (keeps the architecture):**
- Schedule Trigger every 10 minutes → Execute Command `python3 scripts/runtime.py tick --project ...` (unchanged); n8n adds a UI, run history and an error workflow; the lock, dedup, gate, idempotency and SQLite stay in our code. At that point n8n is a scheduler provider with a UI; systemd/cron on the same VPS does the same with less surface.
- Optional value n8n adds: an approval front end. A Form/Webhook workflow that calls `runtime.py inbox` and `runtime.py approve --confirmed --sha256 <hash>` via Execute Command, so the person approves from the phone. The hash check stays in `runtime.py`.
- What not to do: build the flow as an n8n "AI Agent" node with a LinkedIn tool attached. n8n's human-in-the-loop feature is for "tools connected to AI Agent nodes" (https://docs.n8n.io/build/integrate-ai/ai-examples/human-in-the-loop-for-tools.md); that design gives the model a publishing tool, which our contract forbids.

### 1c. n8n nodes relevant to this workload

- **Gmail Trigger**: polling; Poll Times modes Every Hour / Day / Week / Month / Every X (minutes or hours) / Custom cron (https://docs.n8n.io/integrations/builtin/trigger-nodes/n8n-nodes-base.gmailtrigger/poll-mode-options); minimum interval not stated. Filters: labels, Gmail search syntax, read status (default unread only), sender. Fetches up to 10 emails per poll by default, 50 max. Dedup: node static data `lastTimeChecked` and `possibleDuplicates` (source: https://raw.githubusercontent.com/n8n-io/n8n/master/packages/nodes-base/nodes/Google/Gmail/GmailTrigger.node.ts). Gotcha: the default "unread only" filter means reading the notification in Gmail first hides it from the trigger; set it to include read mail.
- **Gmail OAuth scopes**: the credential's default scope list is `gmail.labels`, `gmail.addons.current.action.compose`, `gmail.addons.current.message.action`, `https://mail.google.com/`, `gmail.modify`, `gmail.compose` (full mailbox access), with a "Custom Scopes" toggle to replace them (https://raw.githubusercontent.com/n8n-io/n8n/master/packages/nodes-base/credentials/GmailOAuth2Api.credentials.ts). To keep the `gmail.readonly` scope the mailbox provider uses, use Custom Scopes. Google "Testing" status: tokens expire after seven days (https://docs.n8n.io/integrations/builtin/credentials/google/oauth-single-service/), same as the repo already found.
- **LinkedIn node**: one operation, Post → Create (person or organization); no comment or reply. "For unsupported operations, you can use the HTTP Request node with the LinkedIn credential" (https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.linkedin/). Credential scopes: `w_member_social`, plus `w_organization_social` when "Organization Support" is on (default on), plus `r_liteprofile,r_emailaddress` (legacy, default) or `profile,email,openid` (https://raw.githubusercontent.com/n8n-io/n8n/master/packages/nodes-base/credentials/LinkedInOAuth2Api.credentials.ts). Turn Organization Support off for a member-only app. Replies would go through HTTP Request to the Comments API (the same endpoint `linkedin.py comment` uses).
- **Wait node**: resume after interval, at a time, on webhook call, on form submitted; waits over 65 seconds are offloaded to the database; optional wait-time limit (Wait node docs above).
- **Error handling**: per-workflow error workflow starting with Error Trigger; Stop and Error node (https://docs.n8n.io/build/flow-logic/handle-errors-gracefully.md). Retry-on-fail details: not found on that page.
- **Credentials**: encrypted in n8n's database with a key n8n "creates ... automatically on the first launch and saves ... in the `~/.n8n` folder", or `N8N_ENCRYPTION_KEY` (https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/configuration-examples/set-a-custom-encryption-key.md). Losing that key loses every credential; back it up separately from the database.
- **Export**: workflow JSON includes credential names and IDs, not secrets per the docs' wording (https://docs.n8n.io/build/manage-workflows/export-and-import.md); Git version control is a Business-plan feature (pricing page).

---

## 2. Make.com

**Prices** (https://www.make.com/en/pricing, accessed 2026-09-30, USD, credit slider read in the browser):

| Credits / month | Core monthly | Core annually | Pro (10k) | Teams (10k) |
|---|---|---|---|---|
| 10k | $10.59/mo | $9/mo | $16/mo (billing period not re-checked) | $29/mo (same) |
| 20k | $18.82/mo | $16/mo | | |
| 40k | $34.12/mo | $29/mo | | |

- Free: 1,000 credits, "15-minute minimum interval between runs", 2 active scenarios. Core: unlimited active scenarios, scheduling "down to the minute", 40-minute max execution, 30-day logs (pricing page).
- Billing unit: credits since August 27 (pricing FAQ). Module actions usually 1 credit; the Code app "consumes two credits for every one second of code execution time" (https://apps.make.com/code).
- Extra credits cost the plan's rate × 1.25; auto-purchase buys 10,000-credit batches; without it, scenarios pause (https://help.make.com/extra-credits).
- Polling costs credits: "Running every 5 minutes = 288 credits per day ... 8,640 operations per month" for the trigger module (https://help.make.com/step-10-schedule-your-scenario). An explicit sentence that an empty check still costs a credit: not found on a vendor page; the example numbers only work if it does, so treated as yes.

**Cost for this workload (Make):**
- Polls: 4,320 credits (one per 10-minute check).
- Per comment, Assumption on module count: Gmail get body 1, HTTP call to the model 1, Code gate 2-6 (1-3 s × 2), HTTP LinkedIn reply 1, Data store search/add for dedup, idempotency and daily count about 3 → about 8-12 credits.
- Approvals, Assumption: a webhook scenario of about 5 credits each.
- Worst case: 4,320 + 900 × 12 + 13 × 4 + 900 × 5 = 4,320 + 10,800 + 52 + 4,500 = **19,672 → 20k tier: $18.82/mo monthly, $16/mo annually**.
- Typical (300 comments): 4,320 + 300 × 10 + 52 + 300 × 5 = 8,872 → **10k tier: $10.59 / $9**.
- Polling alone uses 43% of the 10k tier (4,320 / 10,000).

**Gmail**: personal @gmail.com connections "expire after 6 months" and need reauthorisation; own-client scopes listed are `gmail.modify`, `gmail.readonly`, `gmail.compose`, `gmail.send` (https://apps.make.com/create-and-configure-a-google-cloud-platform-project-for-gmail). Broader than our `gmail.readonly`. Trigger mechanism (polling vs push): not found on the page read; Assumption polling (billing examples above).

**LinkedIn**: modules are user text/image/video post, delete user post, company posts and statistics, and "Make an API Call"; no comment or reply module (https://apps.make.com/linkedin). A reply would go through "Make an API Call". Scopes of Make's LinkedIn connection: not found.

**Code app**: JavaScript (Node 20.19.4) and Python 3.12.11; Core/Pro/Teams 1 CPU, 512 MB, **30-second max**; built-in Python libraries `pendulum`, `toolz`, `requests`; custom libraries Enterprise only; the docs advise the HTTP module rather than API calls from code (https://apps.make.com/code). Standard-library availability is not stated explicitly. No file system or subprocess documented → `policy_gate.py` must be pasted and refactored (inputs as variables, `sensitive_topics.py` inlined, state/log read from Data stores).

**Architecture fit**: logic is rebuilt as a scenario (visual modules + pasted code). The hash-bound approval survives only if the policy file and the state row are stored somewhere the scenario reads (Data store) and the pasted gate recomputes the hash; the repository's gate and Make's copy drift apart unless a deploy step copies it. Lock-in: scenario blueprints are Make-specific.

---

## 3. Zapier

**Prices** (https://zapier.com/pricing, accessed 2026-09-30, USD; page toggle "Pay yearly (Save 33%)"):

| Professional tasks / month | Annual billing | Monthly billing |
|---|---|---|
| 750 | $19.99 | $29.99 |
| 2,000 | $49.00 | $73.50 |
| **5,000** | **$89.00** | **$133.50** |
| 10,000 | $129.00 | $193.50 |

- Polling ("update time"): Free 15 min, Professional 2 min, Team 1 min. Code by Zapier runtime: Free 1 s, Professional/Team 30 s per step, Enterprise 2 min. Overage ("pay-per-task") 1.25× base rate on annual, 2.5× on monthly (pricing page).
- What counts: "A task is counted whenever Zapier successfully completes a unit of work"; **triggers, polling for new data, Formatter, Paths and Filter do not count** (pricing page FAQ).
- Team starts "from $69/month" (pricing page); not needed for one person.

**Cost for this workload (Zapier):**
- Polls: 0 tasks.
- Per comment, Assumption: Code gate 1, Webhooks call to the model 1, Webhooks call to LinkedIn 1, Storage/Tables writes 2 → about 5 tasks. Approvals about 3 tasks. Posts about 3 tasks.
- Worst case: 900 × 5 + 900 × 3 + 13 × 3 = 4,500 + 2,700 + 39 = **7,239 → 10,000 tier: $129/mo annual, $193.50/mo monthly**.
- Typical: 300 × 5 + 300 × 3 + 39 = 2,439 → **5,000 tier: $89 / $133.50**. The brief's ~4,500 tasks/month also lands in the 5,000 tier.
- Assumption: Code by Zapier and Webhooks steps count as tasks (they are actions and not in the exclusion list).

**Gmail**: "New Email Matching Search" is a polling trigger; interval 1-15 minutes by plan (help/community results for the search above; plan intervals from the pricing page). Scopes: not found.

**LinkedIn**: actions are "Create Company Update" and "Create Share Update"; no comment or reply action (https://zapier.com/apps/linkedin/integrations). An "API Request (Beta)" action appeared in a search snippet but not on the vendor page read: unverified. Fallback: Webhooks by Zapier with a bearer token pasted into the Zap; LinkedIn member tokens last 60 days without refresh (noted in n8n's LinkedIn credential source), so it breaks every two months.

**Code**: Python 3.13 with standard library, `requests` and BeautifulSoup; no pip installs; inputs arrive as strings; "If you need to make more than 2 HTTP requests or make authenticated HTTP requests, Zapier recommends creating a custom app" (https://help.zapier.com/hc/en-us/articles/8496326417549-Use-Python-code-in-Zaps). Rate limit on Professional: 225 requests per 10 s (https://help.zapier.com/hc/en-us/articles/29971850476173-Code-by-Zapier-rate-limits). No files, no subprocess → same rewrite as Make.

**Architecture fit**: worst of the four. No reply action, token handling by hand, the most expensive per unit, gate pasted into a Zap.

---

## 4. Pipedream

**Prices** (https://pipedream.com/pricing, accessed 2026-09-30, rendered in the browser, USD):

| Plan | Monthly | Annual | Included credits | Active workflows | Connected accounts | Min. schedule interval | Max duration | Event history |
|---|---|---|---|---|---|---|---|---|
| Free | $0 | $0 | 100/mo (usage cap 100/mo) | 3 | 3 | 5 minutes | 300 s | 7 days |
| Basic | $45/mo | $29/mo ($348/yr) | 2,000/mo | 10 | 5 | 1 minute | 750 s | 7 days |
| Advanced | $74/mo | $49/mo ($588/yr) | 2,000/mo | unlimited (plan card) | unlimited (plan card) | 1 second | 750 s | 30 days |
| Connect | $150/mo | $99/mo ($1,188/yr) | 10,000/mo | | | | 750 s | 30 days |

- Credit: "30 seconds of compute time with 256MB of memory, with a minimum of 1 credit per workflow segment"; "The first 30 seconds of compute time for event sources configured as workflow triggers is free"; unused credits do not roll over; "You can run any number of credits ... on any paid tier" (pricing FAQ). Price per extra credit: "varies by plan and is automatically discounted" — **amount not found**.
- Data stores: Basic 1 store, 500 keys, 100 KB; Advanced/Connect 1 MB. File Stores: Advanced and up ("Unlimited in Preview"). File system `/tmp`: 2 GB (pricing page; https://pipedream.com/docs/workflows/limits). Assumption: `/tmp` does not persist between executions reliably, so it cannot hold the SQLite store.
- Ownership: Workday signed a definitive agreement to acquire Pipedream on 2025-11-19 (https://newsroom.workday.com/2025-11-19-Workday-Signs-Definitive-Agreement-to-Acquire-Pipedream). Roadmap risk for a personal-use product.

**Cost for this workload (Pipedream):**
- Gmail polling source: free (public registry source as a trigger, first 30 s free). Default polling interval for registry sources is 15 minutes, overridable (https://pipedream.com/docs/components/contributing/guidelines); set it to 10.
- Per comment: one workflow, one segment; model call + gate + reply. Assumption 10-40 s → 1-2 credits. Approvals 1 credit each. Posts 1 each.
- Worst case: 900 × 2 + 900 + 13 = **2,713 credits → over the 2,000 included; overage price not found**.
- Typical: 300 × 1.5 + 300 + 13 = 763 → inside 2,000.
- Plan: Basic ($45 / $29) fits the counts (10 workflows, 5 accounts) but its 100 KB data store cannot hold an event/run/action ledger for months; Advanced ($74 / $49) adds File Stores (to keep a SQLite file) and 30-day history. Realistic: **Advanced, $49-74/mo**, plus overage in a 30-comment/day month.

**Gmail**: triggers New Email Received, New Email Matching Search (≤100 new messages per run), New Labeled Email, and others; "Supply your own OAuth client to request a different set" of scopes (https://pipedream.com/apps/gmail). "Use custom OAuth clients" is a pricing-table row; which plans include it: not readable (icons). Polling vs push: not stated.

**LinkedIn**: 22 actions including "Create Comment" ("Create a comment on a share or user generated content post"), with a `parentComment` field for nested replies (https://pipedream.com/apps/linkedin; component source https://raw.githubusercontent.com/PipedreamHQ/pipedream/master/components/linkedin/actions/create-comment/create-comment.mjs). The only platform here with a ready reply action.

**Code**: Python 3.12 steps, PyPI packages auto-installed from imports, read/write `/tmp`, env vars for secrets via `os.environ` (https://pipedream.com/docs/workflows/building-workflows/code/python). "Run Bash scripts", Go, Node.js also listed on the pricing page. Subprocess and importing local modules: not documented. Assumption: `policy_gate.py` (stdlib only) can run nearly as is if the policy, state and log are written to `/tmp` from the store first; `sensitive_topics.py` has to be fetched or inlined.

**Architecture fit**: closest of the SaaS options to "code decides": steps are real Python, Git Sync (Advanced+) keeps workflow code in GitHub. Still: the harness CLI does not run there (model via API), the store moves to File Stores/data store or an external DB, and the gate is a copy.

---

## 5. Cross-platform comparison

| | n8n self-hosted CE | n8n Cloud Starter | Make Core | Zapier Professional | Pipedream |
|---|---|---|---|---|---|
| Platform fee, typical month | €0 + VPS (not researched) | €20 annual / ~€24 monthly (third-party) | $9 / $10.59 (10k) | $89 / $133.50 (5k) | $29-49 annual, $45-74 monthly |
| Platform fee, worst month (30 comments/day) | €0 + VPS | same (1,813 ≤ 2,500 executions) | $16 / $18.82 (20k) | $129 / $193.50 (10k) | same + overage (price not found) |
| Polling cost | none | none (empty polls free) | 4,320 credits | none | none |
| Runs `runtime.py` + `policy_gate.py` unchanged | yes, via Execute Command in a custom image | no (no stdlib imports, no Execute Command) | no (paste, 30 s, no files) | no (paste, 30 s, strings only) | partly (real Python; files via `/tmp`) |
| Harness CLI on the operator's Claude account | possible (Assumption: CLI installed and signed in on the server; whether that is allowed unattended is a separate question) | no → model API key | no → API key | no → API key | no → API key |
| SQLite store with atomic claim | yes (local file) | no | no (Data stores) | no (Storage/Tables) | only via File Stores copy, race-prone (Assumption) |
| LinkedIn reply | HTTP Request node or our `linkedin.py` | HTTP Request node | "Make an API Call" | none built in; raw webhook | "Create Comment" with `parentComment` |
| Gmail scope | our `gmail.readonly` (our provider) or Custom Scopes | Custom Scopes | modify/readonly/compose/send; 6-month expiry on @gmail.com | not found | own OAuth client allowed |
| Secrets | n8n DB encrypted with a key in `~/.n8n`; or our resolver's env | n8n Cloud holds them; external secrets Enterprise only | Make holds them | Zapier holds them | Pipedream env vars / connected accounts |
| Run history | our store + n8n executions | n8n (retention for Starter not found; Pro "7 days of insights") | 30 days | not found | 7 days Basic, 30 Advanced |
| Ops burden | highest: OS, Docker, updates (3.0 in Oct 2026), backups, TLS, encryption key | low | low | low | low |
| Lock-in | low (logic stays in repo) | high | high | high | medium (Python steps portable; workflow wiring not) |

## 6. Findings against the repository's principles

1. **"The model proposes, code decides."** Every SaaS option keeps it only if the model call is a plain completion with no tools and the gate is a code step. The dangerous path is the platforms' "AI agent with tools" features (n8n's AI Agent node, human-in-the-loop for tools): wiring a LinkedIn tool to the agent gives the model a publishing tool. Only a plain LLM/HTTP node is acceptable.
2. **Hash-bound approvals.** Survive where the gate is our code and reads the real policy file (self-hosted n8n; Pipedream with care). On n8n Cloud, Make and Zapier the gate is a pasted copy reading platform storage; the SHA-256 would bind whatever was pasted into platform storage, not the repository file the person approved, unless a deploy step syncs both.
3. **Idempotency ledger / SQLite store.** Only self-hosted keeps it unchanged. Elsewhere it becomes platform storage (n8n Data tables, Make Data stores, Zapier Storage/Tables, Pipedream data store 100 KB-1 MB) whose atomicity guarantees were not found on vendor pages.
4. **Harness-agnostic core (AGENTS.md principle 1, 2).** These platforms are not AI harnesses, but the same open-closed rule applies: platform workflow exports (n8n JSON, Make blueprints, Zaps, Pipedream workflows) must live outside `skills/`, `agents/`, `contracts/`, `shared/`, `providers/`' core files and `templates/` — for example as a `scheduler`/host implementation folder, the way `providers/scheduler/launchd.py` is one implementation. A skill or contract that says "open n8n" breaks the rule. Rebuilding the gate as visual nodes also moves logic out of reach of `scripts/validate.py`, `security_scan.py` and the offline tests.
5. **Model on the operator's account (decision 2026-09-28, for evals).** All four SaaS options force an API key billed per token instead of the claude-code adapter on the operator's own account; that is the operator's decision, not a technical detail. A tool-free API adapter would also need its own prompt assembly (agent file + skill + artifacts), which `run-agent.sh` gets from the CLI today.
6. **External content.** Comments arrive in e-mail bodies on every platform. Any platform expression language that evaluates fields (n8n expressions, Make mapping) must receive the comment as data only; Assumption: none of them evaluate text inside a mapped value, not verified.

## 7. Assumptions (all of them)

- Comment rate for the "typical" month: 10 per day (unknown).
- Module/task/credit counts per comment and per approval on Make, Zapier and Pipedream (sections 2-4).
- Code by Zapier and Webhooks by Zapier count as tasks.
- Make charges a credit for an empty scheduled check (inferred from the vendor's example numbers).
- Make's Gmail trigger is polling.
- n8n Data tables and SaaS stores lack our atomic-claim guarantees.
- Pipedream `/tmp` is not a reliable persistent store; Pipedream step durations of 10-40 s per comment.
- The native-Python task runner in self-hosted n8n blocks subprocess.
- Running the harness CLI signed in to the operator's account on a server is technically possible; whether its terms allow unattended server use was not checked.
- Running self-hosted n8n for a company's clients as a service would fall outside the Sustainable Use License.
- No platform evaluates expressions found inside mapped text values.

## 8. Not found

- n8n Cloud EUR monthly-billing price on the vendor page (only third-party €24/€60); n8n Starter overage price; n8n Gmail Trigger minimum interval; n8n Starter log retention.
- Make: explicit statement on empty-poll credits; Gmail trigger mechanism; LinkedIn connection scopes.
- Zapier: Gmail scopes; LinkedIn "API Request (Beta)" on a vendor page; run-history retention.
- Pipedream: price per extra credit; which plans include custom OAuth clients; Gmail polling vs push; subprocess support.
