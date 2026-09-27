# Publisher providers

Implementations of the `publisher:<platform>` class. Interface: `providers/CONTRACT.md`.

## LinkedIn (`linkedin.py`)

Publishes one post as the authenticated member through the versioned Posts API (`LinkedIn-Version: 202609`), with at most one image uploaded through the Images API. The member Posts API has no scheduling: a future `--at` is refused, and scheduling belongs to the `scheduler` class.

### Setup (once)

1. Create an app at https://www.linkedin.com/developers/apps. LinkedIn requires the app to be linked to a LinkedIn Page; posts are still published as you, the member.
2. In the app's Products tab, add "Share on LinkedIn" (scope `w_member_social`) and "Sign In with LinkedIn using OpenID Connect" (scopes `openid profile`).
3. In the Auth tab, add the redirect URL `http://localhost:8765/callback`.
4. Export the client ID and secret in your shell, never in a file:

   ```sh
   export LINKEDIN_CLIENT_ID=...
   export LINKEDIN_CLIENT_SECRET=...
   ```

5. Run `uv run providers/publisher/auth.py --provider linkedin` and approve in the browser. The access token and its expiry go to the OS secret store (service `ai-workbench`, username `publisher-linkedin`), never to disk in plain text.
6. Verify: `uv run providers/publisher/linkedin.py --check`.

Access tokens last 60 days and self-serve apps get no refresh token. `--check` warns under 7 days; rerun step 5 before expiry.

### Usage

```sh
uv run providers/publisher/linkedin.py publish --platform linkedin \
    --text-file post.txt [--media cover.png] --idempotency-key <k> --dry-run
uv run providers/publisher/linkedin.py publish --platform linkedin \
    --text-file post.txt [--media cover.png] --idempotency-key <k> --confirmed
uv run providers/publisher/linkedin.py resolve --idempotency-key <k> \
    (--post-urn <urn> | --not-published) --confirmed
```

The dry run reads no token and sends nothing, so the author URN is shown as a placeholder (`/v2/userinfo` is only called when publishing).

### At most once per key

`--idempotency-key` is required: one key per post, reused on every retry of that post. The key is recorded as `pending` in the ledger, under a file lock, before any request, and as `published` with the post URN after the 201; a second run with a published key returns the existing post. When the outcome is unknown (a timeout, a dropped connection or a crash after the Posts API request was sent), the key stays `pending` and every new attempt is refused until the user checks the profile and runs `resolve`: `--post-urn <urn>` if the post is there, `--not-published` if it is not. A 4xx answer, or a failure before the post request, releases the key. Redirects are refused, so the token never leaves for a URL that was not checked. The ledger and its folder are 0600/0700.

The post text is escaped for LinkedIn's little text format, so every reserved character (`\ | { } @ [ ] ( ) < > # * _ ~`) appears literally. As a consequence, `#word` and `@name` are shown as plain text, not as links.

### Environment variables

| Variable | Used by | Purpose |
|----------|---------|---------|
| `LINKEDIN_CLIENT_ID` | `auth.py` | App client ID; required for the authorization. |
| `LINKEDIN_CLIENT_SECRET` | `auth.py` | App client secret; required for the authorization. |
| `LINKEDIN_ACCESS_TOKEN` | `linkedin.py` | Optional; a token from the environment instead of the secret store. |
| `LINKEDIN_TOKEN_EXPIRES_AT` | `linkedin.py` | Optional; ISO-8601 expiry of `LINKEDIN_ACCESS_TOKEN`. |
| `PUBLISHER_LINKEDIN_LEDGER` | `linkedin.py` | Path of the idempotency ledger. Default `~/.cache/ai-workbench/publisher-linkedin.json` (or under `$XDG_CACHE_HOME`). |
| `LINKEDIN_API_BASE` | `linkedin.py` | Tests only: a loopback URL that replaces `https://api.linkedin.com`. When set, the secret store is not read. |
| `LINKEDIN_HTTP_TIMEOUT` | `linkedin.py` | Tests only, honoured with `LINKEDIN_API_BASE`: request timeout in seconds (default 60). |

### Tests

```sh
uv run --with pytest==9.1.1 pytest providers/publisher/tests
```

The tests use a local fake server and a fake token; they need no network and no credentials.
