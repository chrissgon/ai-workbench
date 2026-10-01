# The image every eval run executes in (backlog T16; evals/executor.py builds and names it).
# Versions are pinned; changing this file changes what a run measures, so raise measurement_version
# in evals/eval-gate.json in the same commit.
FROM node:24.10.0-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git python3 python3-venv chromium fonts-liberation jq less procps ripgrep \
    && rm -rf /var/lib/apt/lists/*

# The two runners and uv, at the versions the gate was measured with on the host.
RUN npm install -g --no-fund --no-audit @anthropic-ai/claude-code@2.1.283 opencode-ai@1.18.32 \
    && npm cache clean --force
COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /uvx /usr/local/bin/

# A browser a skill's script can find, and no sandbox of its own: the container is the boundary.
ENV CHROME_BIN=/usr/bin/chromium PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

RUN useradd --create-home --shell /bin/bash eval \
    && git config --system user.name "Eval" && git config --system user.email "eval@example.invalid" \
    && git config --system init.defaultBranch main && git config --system --add safe.directory '*'
# On Linux a run keeps the caller's numeric user, so the home must be usable by any of them.
RUN chmod 1777 /home/eval
USER eval
WORKDIR /eval
