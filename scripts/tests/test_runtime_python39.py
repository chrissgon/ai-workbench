"""The scheduled tick runs scripts/runtime.py with /usr/bin/python3 (Python 3.9 on macOS), and the runtime starts
the scripts below with that same interpreter. A `X | None` annotation evaluated at definition time raises TypeError
on 3.9, so each of them either has no such annotation or defers annotations with `from __future__ import annotations`.
Providers that reach the network run through `uv run` under their own `requires-python` and are not listed."""
import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ON_SYSTEM_PYTHON = [
    "scripts/runtime.py", "scripts/runtime_vote.py", "scripts/vote_job.py",
    "providers/store/sqlite.py", "providers/scheduler/launchd.py",
    "skills/mkt-engage/scripts/policy_gate.py", "skills/mkt-engage/scripts/parse_notification.py",
    "skills/mkt-vote-round/scripts/vote_state.py", "skills/mkt-vote-round/scripts/vote_update.py",
    "skills/mkt-social-copy/scripts/check_post.py", "skills/mkt-publish/scripts/payload.py",
    "skills/brand-identity/scripts/render.py", "skills/brand-identity/scripts/contrast.py",
    "skills/brand-voice/scripts/voice_stats.py", "skills/brand-profile/scripts/sensitive_topics.py",
]


def annotations(tree):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            for a in args.posonlyargs + args.args + args.kwonlyargs + [args.vararg, args.kwarg]:
                if a is not None and a.annotation is not None:
                    yield a.annotation
            if node.returns is not None:
                yield node.returns
        elif isinstance(node, ast.AnnAssign):
            yield node.annotation


@pytest.mark.parametrize("rel", ON_SYSTEM_PYTHON)
def test_no_union_annotation_is_evaluated_on_python_39(rel):
    tree = ast.parse((REPO / rel).read_text(encoding="utf-8"), feature_version=(3, 9))
    deferred = any(isinstance(n, ast.ImportFrom) and n.module == "__future__" and
                   any(x.name == "annotations" for x in n.names) for n in tree.body)
    if deferred:
        return
    unions = [ast.unparse(a) for a in annotations(tree)
              if any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitOr) for n in ast.walk(a))]
    assert not unions, f"{rel}: add 'from __future__ import annotations' (3.9 evaluates {unions[0]!r})"
