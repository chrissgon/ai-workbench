// The marks the City puts on a building (round 4): the decision mark (R-20) and the corner brackets of the building the person follows or points at
// (R-17). Both are flat-faced solids in tokens (`cityTones`), no text and no glow; the brackets are drawn in the brand colour.

import { cityTones } from "./palette.js";

// The decision mark: a small amber exclamation, a bar over a cube, as the drawing has it (a bar 0.8 over a cube 0.26 with a gap of 0.13 at the
// drawing's scale), a little larger so that it reads: a floor of the closed City is 1.9 units high and the mark is a little over two thirds of it.
export const MARK = Object.freeze({ cube: 0.32, gap: 0.16, bar: [0.32, 0.96, 0.32] });
export const MARK_HEIGHT = MARK.cube + MARK.gap + MARK.bar[1];

/**
 * The decision mark as a group whose origin is the middle of its foot (so it rises and tilts about its foot), added to `parent` at (x, y, z).
 * The cube and the bar are one batch in three tones: top, left and right.
 */
export function decisionMark(kit, parent, x, y, z) {
  const { THREE, palette } = kit;
  const tones = cityTones(palette).mark;
  const group = new THREE.Group();
  group.position.set(x, y, z);
  group.userData.mark = true;
  const batch = kit.batch();
  batch.box(MARK.cube, MARK.cube, MARK.cube, 0, 0, 0, tones);
  batch.box(MARK.bar[0], MARK.bar[1], MARK.bar[2], 0, MARK.cube + MARK.gap, 0, tones);
  batch.mesh(group, { cast: false });
  parent.add(group);
  return group;
}

// The brackets: an L at each of four corners, arms of ARM along both sides, ARM_WIDTH wide. On the ground they stand round the lot (the drawing:
// 8.96 by 8.64, a little toward the front); at the roof they stand round the roof's edge, each with a short line down.
const ARM = 1.15;
const ARM_WIDTH = 0.13;
const DROP = 0.9;
const GROUND_HALF = { x: 4.5, z: 4.35 };
const GROUND_SHIFT = { x: 0.3, z: 0.75 };
const ROOF_HALF = { x: 3.9, z: 3.4 };
const FLAT = 0.04;

/**
 * Eight corner brackets in the brand colour. Returns {group, roof}: `group` holds the four on the ground (at `ground` height) and `roof`, a group
 * to be moved to the roof's height, the four at the roof with their line down. Both are one batch each; the whole is hidden until asked for.
 * The positions are relative to the building's centre: the group goes where the building stands.
 */
export function bracketSet(kit, ground = 0.22) {
  const { THREE, palette } = kit;
  const colour = cityTones(palette).bracket;
  const group = new THREE.Group();
  group.visible = false;
  const roof = new THREE.Group();
  group.add(roof);
  const onGround = kit.batch();
  const atRoof = kit.batch();
  for (const sx of [-1, 1]) {
    for (const sz of [-1, 1]) {
      // an L: one arm along x and one along z from the corner (cx, cz), toward the middle
      const L = (batch, cx, cz, y) => {
        batch.box(ARM, FLAT, ARM_WIDTH, cx - sx * (ARM / 2 - ARM_WIDTH / 2), y, cz, colour);
        batch.box(ARM_WIDTH, FLAT, ARM, cx, y, cz - sz * (ARM / 2 - ARM_WIDTH / 2), colour);
      };
      L(onGround, sx * GROUND_HALF.x + GROUND_SHIFT.x, sz * GROUND_HALF.z + GROUND_SHIFT.z, ground);
      const rx = sx * ROOF_HALF.x;
      const rz = sz * ROOF_HALF.z;
      L(atRoof, rx, rz, 0.02);
      atRoof.box(ARM_WIDTH, DROP, ARM_WIDTH, rx, 0.02 - DROP, rz, colour);
    }
  }
  onGround.mesh(group, { cast: false });
  atRoof.mesh(roof, { cast: false });
  return { group, roof };
}
