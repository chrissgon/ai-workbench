# Bug-fix checklist

Loaded at step 5 of `eng-code-review` when the change is a bug fix: the backlog task or commit says fix, or a plan in `docs/engineering/plans/<task>.md` names a root cause. Fill every row; "not checked" is a valid result only with the reason.

| Item | How to check | Result to record |
|------|--------------|------------------|
| The cause is named | Open the plan; copy the root cause sentence and its location (`file:function`) | the sentence, or "no plan: cause unknown" (then the fix is judged as a change, and the report says the cause is unverified) |
| The fix is at the cause | Compare the diff's changed lines with the cause's location. A guard, retry or conversion added at a caller while the cause stays in the callee treats a symptom | `at the cause` / `symptom: changed <file:line>, cause at <file:function>` |
| The reproduction no longer reproduces | Run the reproduction from the plan or the bug report (a test, a command, a request); quote the output | pass / fail, with the line |
| A regression test exists | Find the test the plan names or the test added by the diff | `file::test`, or "none" (high) |
| The regression test fails without the fix | Make a scratch copy without the fix in one chained command that prints its path, and use that literal path afterwards, never a shell variable. A change with a parent commit: `d="$(mktemp -d)" && git worktree add --detach "$d/copy" <base> && echo "$d/copy"`. A patch already in the tree, with no parent commit: the same command with `HEAD`, then `git -C <path> apply --reverse <absolute path of the patch>`. Run the test in the copy; it must fail. Remove the copy after (`git worktree remove --force <path>`). Never reverse a patch in the tree under review | fails without / passes without (then it is not a regression test) / not checked: reason |
| The test asserts the fixed behaviour | Read the assertion: it names the correct output for the input that used to be wrong, not "does not throw" | quote the assertion |
| Other callers of the fixed code | grep the fixed function; each caller either wanted the old behaviour (then it is a regression) or the new one | list, with a line each |
| Similar code elsewhere | grep for the same pattern that caused the bug (the same wrong call, the same strip-then-check order) | list, or "none found: searched for <pattern>" |
| Nothing was weakened to make it pass | Diff of test files: no removed assertions, no skip, no widened tolerance | none / `file:line` |
| The fix stays minimal | Hunks that are not the fix or its test are scope findings in perspective 1 | none / list |

Verdict rule for fixes: a symptom fix, a skipped or removed failing test, or a reproduction that still reproduces is blocking.
