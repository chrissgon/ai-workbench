# Requirement classes

| Class | What satisfies it | Used by |
|-------|-------------------|---------|
| `integration:issue-tracker` | Jira, Linear, GitHub Issues | engineering flows |
| `integration:vcs` | GitHub, GitLab | delivery |
| `integration:design-tool` | Figma; the design-system projects of a generative design tool | design, validation |
| `search:web` | read-only access to the public web: a search tool, fetching a page, reading a public registry or a public API | research, business, brand, engineering, marketing |
| `generator:image` | any image model behind an API | design assets, marketing |
| `generator:video` | any video model behind an API | marketing (slot reserved, not implemented) |
| `publisher:<platform>` | the publishing API of the platform, called directly or through a scheduling service; the platform is a parameter | marketing |
| `sender:email` | SMTP, a mail API | marketing, notifications |
| `reader:email` | Gmail API, IMAP (read only: search and read messages) | marketing, engagement |
| `scheduler:job` | launchd on macOS, systemd on Linux (a job runs a command once at a set time or every N minutes); or a harness routine | marketing, operations, the agent runtime's trigger |
| `store:runtime` | SQLite (a local file); a cloud database later | the agent runtime: cursors, events, runs, approval inbox, executed actions |
