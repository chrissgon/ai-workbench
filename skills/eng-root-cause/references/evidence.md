# Evidence when the bug resists

Loaded at step 3 or step 4 of `eng-root-cause` when the reproduction is unreliable, the runtime is not reachable, or two causes fit the same observations.

## Unreliable reproduction (timing, order, load)

- Make the timing explicit before touching the code: run the reproduction 20 times and record how many fail; a cause that explains a 3-in-20 failure must say what differs in those three.
- Force the suspected order instead of waiting for it: delay one side (`await new Promise(r => setTimeout(r, 500))` in the probe, a throttled CPU or network in the browser, a paused debugger) and see whether the failure becomes certain. A cause that predicts "fails when A finishes before B" is confirmed when forcing A first fails every time and forcing B first never does.
- In a browser, hydration, fonts, transitions and lazy chunks change timing between the first paint and a settled page; read values after the state the user sees (`networkidle`, the end of a transition, the application reporting that it has mounted), and say which one the reproduction waits for.

## No access to the runtime

- Ask for the smallest thing that settles it: the exact version (`navigator.userAgent`, `node -v`), a screenshot with the developer tools showing the computed value, a log line. One question with the recommended way to collect the answer.
- A runtime the project supports but the machine lacks (WebKit on Linux, an older Node) is often available through the test runner's browser install or a container. That is a download: name what will be installed and its version, and run it only after the user agrees.

## Two causes fit

- Write both predictions side by side and find the input where they differ; that input is the discriminating case. If no input separates them, the two are the same cause described twice, or the evidence needed is not observable yet: grade `unconfirmed` and say what would separate them.
- Reverting the suspected line in a scratch copy (`scratch=$(mktemp -d)`, `git worktree add "$scratch" <commit>`, removed afterwards) and seeing the symptom disappear is evidence for the line, not for the mechanism; pair it with the specification or a trace that explains why.

## Grades, not percentages

Percent confidence invites invented numbers. The section uses three grades, each defined by what was observed:

| Grade | Requires |
|-------|----------|
| confirmed | reproduced in every supported runtime where it occurs; the line found and quoted; every discriminating case matched its prediction |
| probable | reproduced and the line found; at least one discriminating case not run (say which and why) |
| unconfirmed | not reproduced, or two causes fit and nothing yet separates them |
