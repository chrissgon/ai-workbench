// The camera move as a small state machine, with no import and no document, so a test can run it. One move at a time: a
// new move, a cancel (the scene was rebuilt, the preference changed, the screen was left) settles the one in flight
// with `false`, so whoever waits for it is never left hanging; finishing settles it with `true`.

import { ease, lerpFrustum } from "./fit.js";

export function createTween() {
  let current = null;   // {from, to, start, ms, resolve}
  return {
    /** Start a move from one frustum to another; settles an earlier move with false. Returns a promise of the move. */
    start(from, to, start, ms) {
      this.cancel();
      return new Promise((resolve) => {
        current = { from, to, start, ms, resolve };
      });
    },
    active() {
      return current !== null;
    },
    /** The frustum at `now`, or null when no move runs; the move ends (settles true) when its time is up. */
    step(now) {
      if (!current) return null;
      const t = Math.min(1, (now - current.start) / current.ms);
      const frustum = lerpFrustum(current.from, current.to, ease(t));
      if (t >= 1) {
        const done = current.resolve;
        current = null;
        done(true);
      }
      return frustum;
    },
    /** Stop the move and settle it with false (a cut). */
    cancel() {
      if (!current) return false;
      const done = current.resolve;
      current = null;
      done(false);
      return true;
    },
  };
}
