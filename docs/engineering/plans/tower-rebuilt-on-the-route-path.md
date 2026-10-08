# Plan: tower-rebuilt-on-the-route-path

- Task: review of PR 252, finding 1 (high): "towerStructure includes state, window, decisions, sheet paths and lot.selected, so the whole open tower is rebuilt"
- Date: 2026-10-08

## Root cause

- Owner: eng-root-cause
- Evidence: confirmed

### Report
Seen: on the real route path (the City, the Building without its documents, the Building with them, the Floor without, with, Back) the open building's meshes are all replaced: 504 of 504 on the floor click, on Back and when the documents arrive; the table's sheets pop out and in. Expected: the clicked building's meshes exist continuously across the route change (SCENE-SPEC-ROUND3, section 2: the tower is built again only when projects or agents change). Reported by: the reviewer, with a probe.
Suggested fix: take sheets, drawers, state, window and decisions out of `towerStructure` and update those room parts in place; not evaluated here.

### Reproduction
`runtime/tests/test_interface_scene_round3.py::test_the_product_sequence_city_building_floor_back_replaces_no_mesh_and_every_transform_moves_by_the_prototypes_curve` (the product's own models in the product's order) and the reviewer's probe, which printed `{"result":{"rebuild":false,"structure":true,...},"sameGroup":false,"replaced":504,"total":504}`.
Run with `uv run --with pytest==9.1.1 pytest -q runtime/tests/test_interface_scene_round3.py -k product_sequence`.
| Case (one field of a floor changed, the rest as before) | Node 24 |
|------|------|
| only a name | structure false, replaced 0 of 504 |
| only the work-order floor (`lot.selected`) | structure true, replaced 504 of 504 |
| only decisions | structure true, replaced 504 of 504 |
| only sheets | structure true, replaced 504 of 504 |
| only drawers | structure true, replaced 504 of 504 |
| only window | structure true, replaced 504 of 504 |
| only state | structure true, replaced 504 of 504 |
| a floor added | structure true, replaced 504 of 504 (right: the floors changed) |

### Cause
`interface/js/scene/tower.js:19-22` `lot.floors.map((f) => [f.name, f.state, f.window, f.decisions, f.lobby, f.drawers, f.interactive, (f.sheets || []).map((s) => s.path)])` with `lot.selected`. The key was meant to name what a tower is made of, and it names everything that can change while the tower is open; `world.js` `update` compares the key and calls `place()`, which builds a new tower and drops the old one. The Floor and Building views read their documents after the screen is shown, so their first model has `sheets: []` and the second has the paths: the key changes on the floor click, on Back and when the documents arrive. Node 24, vendored three.js r186; no browser quirk is involved.

### Discriminating experiment
| Case | Predicted by the cause | Observed | Rules out |
|------|------------------------|----------|-----------|
| a name changed | no rebuild (not in the key) | structure false | the compare being too eager |
| each other field of the key changed | rebuild | structure true for all six | a single field being the cause (the sheets alone) |
| a floor added | rebuild (legitimate) | structure true | the fix removing every rebuild |

### Reach
- Triggers: any poll that changes a floor's state, window or decisions; the documents arriving; the work-order floor moving.
- Seen today at: every Floor and Building screen with documents read late (the served page).
- Same assumption elsewhere: `world.js` `place()` is the only caller; none.

### Why it escaped
The round-3 acceptance test used a model identical to the one before the click, so nothing in it changed; the world's own poll test changed a state and asserted that the tower was rebuilt (it pinned the behaviour). Introduced in the commit of the world (WP-9.11).

### What a fix must preserve
- A model that differs only in words changes no mesh (`test_a_poll_changes_the_world_in_place...`).
- A floor added to a lot rebuilds that tower and no other.
- The City, the opening, the floor click and Back keep their curves (`..._product_sequence...`).

### Found on the way
- `tween.js` snapped within 1 % of the first distance (finding 6); `frame.js` counted the pointer's hover as a selection (finding 3).

### Open
- none

### Assumptions
- none

## Failing tests

- Owner: eng-unit-tests
- Command: `uv run --with pytest==9.1.1 pytest -q runtime/tests/test_interface_scene_round3.py`
- Files: `runtime/tests/test_interface_scene_round3.py`

| Test | Source | Expected before the change | Observed before (Node 24) |
|------|--------|----------------------------|---------------------------|
| `test_the_product_sequence_city_building_floor_back_replaces_no_mesh_and_every_transform_moves_by_the_prototypes_curve` | Root cause › Reproduction | fails now | `no mesh of the clicked building is ever replaced ...: [['open', 12], ...]` (the building's meshes at the documents' arrival) |
| `test_each_thing_a_poll_or_the_documents_change_changes_where_it_stands` | Root cause › Discriminating experiment | fails now | the tower has no `sync` (the tray's stack is not a group of its own) |
| `test_a_poll_changes_the_world_in_place_a_tower_is_made_again_only_when_its_floors_change` | What a fix must preserve | fails now (the old test asserted the rebuild) | a state change gave `structure: true` |

- Result before the change: the product-sequence test failed (run with `git stash push -- interface`), the others cannot run against the old shape.
- Not run: browsers other than the pane's (the page has one)
- Pending decisions: none

## Change

- Owner: eng-implement
- Date: 2026-10-08
- Check: `uv run --with pytest==9.1.1 pytest -q runtime/tests/test_interface_scene_round3.py -k product_sequence` → before: failed on the replaced meshes; after: `1 passed`
- What changed: `interface/js/scene/tower.js`: `towerStructure` is the floors' names, lobby and interactive flags, `accepted` and whether a task runs; `tower.sync` (window, decisions, sheets, drawers, selected, the outside exclamation; state makes that room again); `tower.dispose`; the cloned fade materials are adopted by the kit. `interface/js/scene/world.js`: `update` calls `tower.sync`; `place()` frees the replaced tower. `interface/js/scene/building.js`, `furniture.js`: the room's setters (the tray's stack and the cabinet's drawers are groups of their own). `interface/js/floor-model.js`, `views/lobby-model.js`: documents unread are `null`, not `[]`.
- Preserved: words-only polls change no mesh (the poll test); the opening, the floor click and Back keep their curves (the product-sequence test).

## Integration tests

- Owner: eng-integration-tests
- Test files: the served page in the pane (the real service, three fictional projects), the Floor click, the late documents, the tray's click, Back and Back again, with a counter on `Object3D.add`.
- With the change: 0 meshes added across those steps, against 535 for the opening itself (the rooms, built once); the Marketing floor with two decisions: hover "Inbox · 2 waiting", click goes to `.../floor/marketing/inbox`.
- Against the code before the change: not run in the pane (the unit test is the red run).
- Scratch copies left: the reviewer's worktree was removed.

## Docs

- Owner: eng-docs
- Documents checked against the change: `design/handoff/scene.md`, `building.md`, `floor.md`, `00-specification.md` (A5), `interface/README.md`; search terms `towerStructure`, `structure`, `rebuilt`, `rebuild`.

| Document | Sentence before | After | Why |
|----------|-----------------|-------|-----|
| `design/handoff/scene.md` | (none about when a tower is built again) | M-30 to M-33 added | the rule was only in code |
| `design/00-specification.md` A5 | "the two durations above are the time those exponential approaches take to settle" | adds the quarter-pixel landing | the landing moved |
| `interface/README.md` | `world.js` and `tower.js` described | unchanged | still true |
