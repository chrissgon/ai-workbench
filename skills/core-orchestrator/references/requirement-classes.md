# Requirement classes (copy names verbatim)

These are the only class names. A skill's `requires` uses them; the routing block's Requirements line uses them. Never compose a new one (there is no `integration:social-media`; a social network is `publisher:<platform>`).

| Class | Meaning |
|-------|---------|
| `integration:issue-tracker` | ticket systems (Jira, Linear, GitHub Issues) |
| `integration:vcs` | GitHub, GitLab and similar |
| `integration:design-tool` | design tools whose files, variables and components an integration can read or write |
| `search:web` | web search including fetching pages |
| `generator:image` | image generation |
| `generator:video` | video generation (reserved) |
| `publisher:<platform>` | publishing to a platform: `publisher:linkedin`, `publisher:x`, `publisher:blog` |
| `mailer` | sending email |
| `mailbox` | reading email, read only: search and read messages |
| `scheduler` | scheduling an action for later |
| `store` | the agent runtime's storage: cursors, events, runs, approval inbox, executed actions |

Status words: `satisfied by <connector or provider>` or `missing → <what the skill does without it>`.
