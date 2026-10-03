# Scheduling again under the same approval

Read this file when a job has to be scheduled again (step 10 of the procedure, or a refusal at step 9). The steps named here are those of the procedure in `SKILL.md`; `payload.py` is in the skill's `scripts/` folder, run as `python3 <this skill's folder>/scripts/payload.py`.

A job has to be scheduled again while its approval is still `pending-execution` (the provider was fixed, the computer was replaced, the user said yes to a missed post at its original time). The approval still stands when the payload is the same, so prove that instead of asking again:

1. Find `<OUT>`: the "Payload folder" of the earlier reply, or the folder under `.workbench-local/payloads/` for which `python3 <this skill's folder>/scripts/payload.py verify --manifest <folder>/manifest.json --hash <recorded hash> --publisher <publisher> --workbench <workbench root>` prints `"ok": true`.
2. The folder, the publisher or the workbench checkout was moved (verify names `job.json`): run `python3 <this skill's folder>/scripts/payload.py jobs --manifest <OUT>/manifest.json --publisher <publisher> --workbench <workbench root>`. It writes each `job.json` for the new place; the `plan_hash` does not change.
3. The folder is gone: build again (step 4). The same `plan_hash` as the approval means the approval covers the new folder. A different `plan_hash` means a content file, a time or an image changed after the approval: show the changed posts and ask again (the gate).
4. Run `payload.py verify` (step 9), dry-run the job again (step 7) to get its new `approved` digest, and schedule it. A new time is a change to the approval and is asked.

What the `plan_hash` is: the SHA-256 of `<OUT>/manifest.json`. Since manifest `"version": 2` that file holds the platform's name, lower-cased, and each post's key, content file, time, scope and file hashes with paths relative to the payload folder, so the hash does not depend on where the folder, the publisher or the workbench lives; `job.json` is derived from the manifest and checked by `verify`, not hashed.

An approval recorded before version 2 keeps the hash it has: it binds a manifest with absolute paths and the hash of each `job.json`, and nothing built now reproduces it. `payload.py verify --manifest <old OUT>/manifest.json --hash <recorded hash>` recognises that manifest (the output says `"manifest_version": 1`) and checks it the old way, which works only while the folder is where it was built. Jobs already scheduled under it run on the scheduler's own copies and are not affected. If the old folder is gone, the approval cannot be checked again: build a new payload, show the posts that have not run, and ask once for them.
