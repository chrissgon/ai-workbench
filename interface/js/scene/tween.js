// The camera move as a small state machine, with no document, so a test can run it. One move at a time: a new move, a cancel (the
// scene was rebuilt, the preference changed, the screen was left) settles the one in flight with `false`, so whoever waits for it is
// never left hanging; finishing settles it with `true`. A move may settle with `true` earlier, at a fraction of its progress
// (`settleAt`): the screen that waits for it can be opened while the camera is still on its way, as the prototype's one camera did,
// and the move still runs to its end.
//
// The move is the prototype's (prototype-motion.js): each frame the progress approaches 1 by `1 - exp(-dt * 4.5)` and the camera's
// centre and zoom are moved in a straight line by that progress (fit.js: moveFrustum). It is stepped by frame time, not by a clock
// from the start: a slow frame slows the move, as it did in the prototype.

import { moveFrustum } from "./fit.js";
import { CAMERA_RATE, createApproach, frameSeconds } from "./prototype-motion.js";

export function createTween() {
  let current = null;   // {from, to, approach, last, resolve, settleAt, settled}
  return {
    /** Start a move from one frustum to another at time `start` (ms); settles an earlier move with false. Returns a promise of the move. */
    start(from, to, start, settleAt = 1) {
      this.cancel();
      return new Promise((resolve) => {
        current = { from, to, approach: createApproach(CAMERA_RATE), last: start, resolve, settleAt, settled: false };
      });
    },
    active() {
      return current !== null;
    },
    /** The frustum at `now` (ms), or null when no move runs; the move ends (settles true) when it has landed. */
    step(now) {
      if (!current) return null;
      const progress = current.approach.step(frameSeconds(now, current.last));
      current.last = now;
      const frustum = moveFrustum(current.from, current.to, progress);
      if (!current.settled && progress >= current.settleAt) {
        current.settled = true;
        current.resolve(true);
      }
      if (current.approach.done()) current = null;
      return frustum;
    },
    /** Stop the move and settle it with false (a cut). */
    cancel() {
      if (!current) return false;
      const done = current.resolve;
      const settled = current.settled;
      current = null;
      if (!settled) done(false);   // a move already settled with true stays true
      return true;
    },
  };
}
