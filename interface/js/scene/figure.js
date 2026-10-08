// The agent figure (handoff scene.md 5.2): no face, no gender, a vest in the state's colour. Three poses: working
// (seated, leaning forward, both forearms on the keyboard), waiting for the person (standing beside the desk, one arm
// raised, the amber exclamation above the head) and idle (seated, leaning back, arms resting). An agent that is off has
// no figure (nothing is built). The only motion is A1: the forearms alternate by about 0.04 rad at about 3 Hz while a
// task of the agent runs; `typing(seconds)` sets them and `rest()` puts them back, so a still frame is the pose.

import { exclamation } from "./props.js";

export const TYPING_HZ = 3;
export const TYPING_AMPLITUDE = 0.04;   // radians (the scene package's choice, scene.md section 11)

/** The vest colour of a state (DEVIATION-9): working theme, waiting warn, idle muted. */
export function vestColour(palette, state) {
  if (state === "working") return palette.T.theme;
  if (state === "waiting") return palette.T.warn;
  return palette.T.mutedRole;
}

/**
 * Build the figure for `state` ("working", "waiting" or "idle") at (x, z) turned by rotY. Returns
 * {group, marker, typing(seconds), rest()}; marker is {key, group, restY} for the waiting exclamation, else null.
 */
export function figure(kit, parent, state, x, z, rotY, key = "figure") {
  const { THREE, palette } = kit;
  const group = new THREE.Group();
  group.position.set(x, 0, z);
  group.rotation.y = rotY;
  parent.add(group);
  const vest = vestColour(palette, state);
  const ink = palette.ink;
  const standing = state === "waiting";

  if (standing) {
    for (const side of [-1, 1]) {
      kit.box(0.14, 0.64, 0.15, side * 0.1, 0.06, 0, ink, { parent: group });
      kit.box(0.14, 0.07, 0.24, side * 0.1, 0, 0.04, ink, { parent: group });
    }
  } else {
    for (const side of [-1, 1]) {
      kit.box(0.14, 0.14, 0.44, side * 0.1, 0.46, 0.22, ink, { parent: group });
      kit.box(0.12, 0.42, 0.13, side * 0.1, 0.04, 0.44, ink, { parent: group });
      kit.box(0.13, 0.07, 0.22, side * 0.1, 0, 0.5, ink, { parent: group });
    }
  }

  const body = new THREE.Group();
  body.position.y = standing ? 0.7 : 0.56;
  body.rotation.x = state === "working" ? 0.18 : state === "idle" ? -0.28 : 0;
  group.add(body);
  const torso = kit.mesh(new THREE.CylinderGeometry(0.19, 0.17, 0.5, 4), vest, 0, 0.25, 0, { parent: body, flat: true });
  torso.rotation.y = Math.PI / 4;
  torso.scale.set(1.25, 1, 0.85);
  kit.box(0.44, 0.08, 0.24, 0, 0.46, 0, vest, { parent: body });
  kit.cyl(0.06, 0.07, 0.08, 8, palette.skin, 0, 0.5, 0, { parent: body });
  kit.mesh(new THREE.SphereGeometry(0.22, 18, 14), palette.skin, 0, 0.78, 0, { parent: body });

  const elbows = [];
  for (const side of [-1, 1]) {
    const shoulder = new THREE.Group();
    shoulder.position.set(side * 0.27, 0.44, 0);
    body.add(shoulder);
    kit.cyl(0.055, 0.06, 0.26, 8, vest, 0, -0.26, 0, { parent: shoulder });
    const elbow = new THREE.Group();
    elbow.position.y = -0.26;
    shoulder.add(elbow);
    kit.cyl(0.048, 0.055, 0.24, 8, palette.skin, 0, -0.24, 0, { parent: elbow });
    kit.mesh(new THREE.SphereGeometry(0.06, 8, 6), palette.skin, 0, -0.27, 0, { parent: elbow });
    if (state === "working") {
      shoulder.rotation.x = -0.55;
      elbow.rotation.x = -1.0;
      elbows.push({ elbow, base: -1.0, phase: side > 0 ? 0 : Math.PI });
    } else if (state === "waiting") {
      if (side > 0) {
        shoulder.rotation.z = side * 2.75;
        elbow.rotation.z = side * 0.25;
      } else {
        shoulder.rotation.z = side * 0.08;
      }
    } else {
      shoulder.rotation.x = -0.25;
      elbow.rotation.x = -0.9;
    }
  }

  let marker = null;
  if (standing) {
    const mark = exclamation(kit, group, 0, 1.92, 0, 0.12, [0.12, 0.42, 0.12]);
    mark.children[1].position.y = 0.18 + 0.21;
    marker = { key, group: mark, restY: 1.92 };
  }
  return {
    group, marker,
    typing(seconds) {
      for (const e of elbows) e.elbow.rotation.x = e.base + TYPING_AMPLITUDE * Math.sin(seconds * TYPING_HZ * Math.PI * 2 + e.phase);
    },
    rest() {
      for (const e of elbows) e.elbow.rotation.x = e.base;
    },
  };
}
