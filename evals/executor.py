#!/usr/bin/env python3
"""The executor: where an eval's commands run. Every model run, grading, case setup and fixture commit
executes in a container built from evals/container/, one container per command (docs/decisions.md,
2026-10-01: one environment, no host mode).

What a container sees:
  /eval          the run's folder (case/, out/, prompt.md), read-write: the only thing a run can change
  /wb/adapters   the adapters, read-only          /wb/shared   the shared references, read-only
  /skill/<name>  the skill under test and the case's dependency skills, read-only, with their evals/
                 folder covered by an empty one (the cases hold the expected output and the assertions)
Nothing else of the machine: no home folder, no other checkout, no credential store.

Network, per command:
  none    no network at all (setup commands, the fixture commit)
  proxy   an internal network whose only way out is a proxy that lets through the hosts listed in
          evals/container/proxy/allow.txt, the model providers (model runs and gradings)
  open    the default network (a case with "allow_web": true)

Secrets reach a container as environment variables named by the caller; their values travel in the
environment of the docker client, never on a command line.

The images, the network and the proxy are named after a hash of evals/container/, so a change to the
definition builds new ones and a record can say which definition it was measured in.

Usage (the runner imports this module; the commands are for a person):
  python3 evals/executor.py ensure     build what is missing, start the proxy, print the environment
  python3 evals/executor.py clean      remove the proxy and the network of the current definition
"""
import hashlib
import json
import os
import subprocess
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFINITION = os.path.join(HERE, "container")
NETWORKS = ("none", "proxy", "open")
PROXY_PORT = 8888
# Passed into a container when the caller's environment has them: what keeps git inside the case folder.
FORWARD = ("GIT_ALLOW_PROTOCOL", "GIT_TERMINAL_PROMPT", "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL",
           "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL", "TZ")


class ExecutorError(RuntimeError):
    pass


def definition_hash(folder=DEFINITION):
    """sha256 over the files of evals/container/ (sorted relative paths and their bytes)."""
    h = hashlib.sha256()
    for dp, dns, fns in os.walk(folder):
        dns.sort()
        for fn in sorted(fns):
            path = os.path.join(dp, fn)
            h.update(os.path.relpath(path, folder).encode() + b"\0")
            with open(path, "rb") as f:
                h.update(f.read())
            h.update(b"\0")
    return h.hexdigest()


def names(folder=DEFINITION):
    tag = definition_hash(folder)[:12]
    return {"image": f"wb-eval:{tag}", "proxy_image": f"wb-eval-proxy:{tag}", "network": f"wb-eval-net-{tag}",
            "proxy": f"wb-eval-proxy-{tag}"}


def docker(*args, env=None, check=True, timeout=1800):
    try:
        r = subprocess.run(["docker", *args], capture_output=True, text=True, env=env, timeout=timeout)
    except FileNotFoundError as e:
        raise ExecutorError("docker is not installed or not on PATH: evals run only in a container") from e
    if check and r.returncode != 0:
        raise ExecutorError(f"docker {' '.join(args[:2])} failed: {(r.stderr or r.stdout).strip()[-400:]}")
    return r


def ensure(env=None):
    """Build the images that are missing, create the internal network and start the proxy. Idempotent, and
    safe when several runners call it at once (a second create of the same name is not an error).
    Returns the environment a record names."""
    n = names()
    if docker("info", "--format", "{{.ServerVersion}}", env=env, check=False).returncode != 0:
        raise ExecutorError("the docker daemon is not running: start it; evals run only in a container")
    for image, folder in ((n["image"], DEFINITION), (n["proxy_image"], os.path.join(DEFINITION, "proxy"))):
        if docker("image", "inspect", image, env=env, check=False).returncode != 0:
            docker("build", "-q", "-t", image, folder, env=env)
    if docker("network", "inspect", n["network"], env=env, check=False).returncode != 0:
        r = docker("network", "create", "--internal", n["network"], env=env, check=False)
        if r.returncode != 0 and "already exists" not in r.stderr:
            raise ExecutorError(f"cannot create the eval network: {r.stderr.strip()[-300:]}")
    state = docker("inspect", "--format", "{{.State.Running}}", n["proxy"], env=env, check=False)
    if state.returncode != 0 or state.stdout.strip() != "true":
        docker("rm", "-f", n["proxy"], env=env, check=False)
        r = docker("run", "-d", "--restart", "unless-stopped", "--name", n["proxy"], n["proxy_image"], env=env, check=False)
        if r.returncode != 0 and "already in use" not in r.stderr:
            raise ExecutorError(f"cannot start the eval proxy: {r.stderr.strip()[-300:]}")
        r = docker("network", "connect", n["network"], n["proxy"], env=env, check=False)
        if r.returncode != 0 and "already exists" not in r.stderr:
            raise ExecutorError(f"cannot connect the eval proxy: {r.stderr.strip()[-300:]}")
    image_id = docker("image", "inspect", "--format", "{{.Id}}", n["image"], env=env).stdout.strip()
    return {"kind": "container", "definition_sha256": definition_hash(), "image": n["image"], "image_id": image_id}


def clean(env=None):
    n = names()
    docker("rm", "-f", n["proxy"], env=env, check=False)
    docker("network", "rm", n["network"], env=env, check=False)


def mounts(root, skills=()):
    """[(host path, container path, read_only)], longest host path first, for translating a command."""
    pairs = [(os.path.join(ROOT, "adapters"), "/wb/adapters", True), (os.path.join(ROOT, "shared"), "/wb/shared", True),
             (root, "/eval", False)]
    for d in skills:
        if d:
            pairs.append((d, f"/skill/{os.path.basename(os.path.normpath(d))}", True))
    return sorted(pairs, key=lambda p: len(p[0]), reverse=True)


def translate(value, pairs):
    """A host path under a mounted folder becomes its path in the container; anything else is unchanged."""
    for host, inside, _ in pairs:
        for h in dict.fromkeys((host, os.path.realpath(host))):
            if value == h or value.startswith(h + os.sep):
                return inside + value[len(h):]
    return value


def command(cmd, root, cwd=None, env=None, skills=(), pass_names=(), network="none"):
    """(docker argv, container name) that runs cmd in a container. cmd, cwd and the mounts are host paths."""
    if network not in NETWORKS:
        raise ExecutorError(f"network must be one of {', '.join(NETWORKS)}")
    n, env = names(), env or {}
    pairs = mounts(root, skills)
    name = f"wb-eval-run-{uuid.uuid4().hex[:16]}"
    argv = ["docker", "run", "--rm", "--init", "--name", name, "-w", translate(cwd or root, pairs),
            "-e", "ENABLE_CLAUDEAI_MCP_SERVERS=false",
            "-e", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1"]
    if sys.platform.startswith("linux"):  # a bind mount keeps numeric owners there; elsewhere the runtime maps them
        argv += ["--user", f"{os.getuid()}:{os.getgid()}", "-e", "HOME=/home/eval"]
    for host, inside, read_only in pairs:
        if os.path.exists(host):
            argv += ["-v", f"{os.path.realpath(host)}:{inside}" + (":ro" if read_only else "")]
            # A skill's eval cases carry the expected output and the assertions: an empty folder covers
            # them, so that a model that looks into /skill cannot read what it is graded on.
            if inside.startswith("/skill/") and os.path.isdir(os.path.join(host, "evals")):
                argv += ["--tmpfs", f"{inside}/evals:ro,size=1k"]
    for key in FORWARD:
        if env.get(key):
            argv += ["-e", f"{key}={env[key]}"]
    for key in dict.fromkeys(pass_names):
        if env.get(key):
            argv += ["-e", key]  # the value comes from the docker client's environment
    if network == "none":
        argv += ["--network", "none"]
    elif network == "proxy":
        proxy = f"http://{n['proxy']}:{PROXY_PORT}"
        argv += ["--network", n["network"]]
        for key in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"):
            argv += ["-e", f"{key}={proxy}"]
        argv += ["-e", "NO_PROXY=localhost,127.0.0.1", "-e", "no_proxy=localhost,127.0.0.1"]
    return argv + [n["image"]] + [translate(a, pairs) for a in cmd], name


def remove(name, env=None):
    """End a container by name: the docker client's process group ending does not end it."""
    docker("rm", "-f", name, env=env, check=False, timeout=60)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["ensure"]:
        print(json.dumps(ensure(), indent=2))
    elif argv == ["clean"]:
        clean()
    else:
        print(__doc__.strip())
        return 0 if argv in (["--help"], ["-h"]) else 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ExecutorError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
