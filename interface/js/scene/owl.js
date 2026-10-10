// The owl of the scene (R-41, R4D-2): the brand mark's own drawing as flat meshes, in the mark's fixed palette. The palette
// below is the one place where this scene holds a colour literal: it is the brand's drawing, not the interface's (round 4, the brand's
// exception to "no colour literal"; the same rule keeps the brand pair in `style.css`). Everything else in the scene is a token or a mix.
//
// This module holds the owl's parts as data and builds them as flat shapes with `svgpath.js`; no texture, no HTML. This package needs the owl's
// outline for the City's shadow (R-19); the Building's rooms add the three poses (R4-B2) from the same parts. Coordinates are the mark's own:
// a viewBox of 200 by 200, y down; a built part is centred on the owl's feet (x 100, y 186) with y up, so an owl stands on the origin.

import { ellipseToShape, pathToShapes, strokeTriangles } from "./svgpath.js";

/** The mark's fixed palette. */
export const OWL_PALETTE = Object.freeze({
  ink: "#1E1B2E", brown: "#6B4429", tan: "#A47551", cream: "#E6D2BC", white: "#FFFFFF", yellow: "#FCD34D",
});

/** Where the owl stands in the mark's drawing: the point under its feet, and the extent of its body with the ear tufts. */
export const OWL_ORIGIN = Object.freeze({ x: 100, y: 186 });
export const OWL_BOUNDS = Object.freeze({ x0: 20, x1: 180, y0: 22, y1: 186 });

const P = OWL_PALETTE;

// A part is {id, kind: "path" | "ellipse", d | e: [cx, cy, rx, ry], fill, stroke: {colour, width} | null}. The order is the mark's back to front.
export const OWL_PARTS = Object.freeze([
  { id: "ear-left", kind: "path", d: "M44 70 Q30 40 36 22 Q60 34 74 50Z", fill: P.brown, stroke: { colour: P.ink, width: 7 } },
  { id: "ear-right", kind: "path", d: "M156 70 Q170 40 164 22 Q140 34 126 50Z", fill: P.brown, stroke: { colour: P.ink, width: 7 } },
  { id: "foot-left", kind: "ellipse", e: [80, 186, 13, 7], fill: P.yellow, stroke: { colour: P.ink, width: 7 } },
  { id: "foot-right", kind: "ellipse", e: [120, 186, 13, 7], fill: P.yellow, stroke: { colour: P.ink, width: 7 } },
  { id: "body", kind: "path", d: "M100 36 C152 36 180 74 180 120 C180 164 146 186 100 186 C54 186 20 164 20 120 C20 74 48 36 100 36Z", fill: P.tan, stroke: { colour: P.ink, width: 7 } },
  { id: "wing-left", kind: "path", d: "M30 120 Q28 158 62 174 Q48 148 50 122Z", fill: P.brown, stroke: { colour: P.ink, width: 6 } },
  { id: "wing-right", kind: "path", d: "M170 120 Q172 158 138 174 Q152 148 150 122Z", fill: P.brown, stroke: { colour: P.ink, width: 6 } },
  { id: "face", kind: "path", d: "M100 72 C84 52 42 54 42 96 C42 128 72 142 100 132 C128 142 158 128 158 96 C158 54 116 52 100 72Z", fill: P.cream, stroke: { colour: P.ink, width: 6 } },
  { id: "eye-left", kind: "ellipse", e: [74, 98, 22, 22], fill: P.white, stroke: { colour: P.ink, width: 6 } },
  { id: "eye-right", kind: "ellipse", e: [126, 98, 22, 22], fill: P.white, stroke: { colour: P.ink, width: 6 } },
  { id: "pupil-left", kind: "ellipse", e: [80, 101, 11, 11], fill: P.ink, stroke: null },
  { id: "pupil-right", kind: "ellipse", e: [132, 101, 11, 11], fill: P.ink, stroke: null },
  { id: "glint-left", kind: "ellipse", e: [84, 98, 4, 4], fill: P.white, stroke: null },
  { id: "glint-right", kind: "ellipse", e: [136, 98, 4, 4], fill: P.white, stroke: null },
  { id: "beak", kind: "path", d: "M92 116 Q100 112 108 116 Q103 130 100 132 Q97 130 92 116Z", fill: P.yellow, stroke: { colour: P.ink, width: 5 } },
]);

/** The part with this id, or null. */
export function owlPart(id) {
  return OWL_PARTS.find((part) => part.id === id) || null;
}

/** The options that put a part's drawing coordinates on the owl's feet, at `scale` (or stretched by `scaleX` and `scaleY`), y up. */
export function owlFrame(o = {}) {
  return { originX: OWL_ORIGIN.x, originY: OWL_ORIGIN.y, ...o };
}

/** The shapes of one part (a path may hold several subpaths), standing on the feet. `o`: {scale, scaleX, scaleY}. */
export function partShapes(THREE, part, o = {}) {
  const frame = owlFrame(o);
  if (part.kind === "ellipse") return [ellipseToShape(THREE, part.e[0], part.e[1], part.e[2], part.e[3], frame)];
  return pathToShapes(THREE, part.d, frame);
}

/**
 * The owl's outline, the silhouette of the City's shadow (R-19): the body and the two ear tufts, no wings, no feet, no face. Returns
 * {body: Shape, ears: [Shape, Shape]}, standing on the origin; `o` stretches it ({scaleX, scaleY}): the shadow is fitted to a window.
 */
export function owlOutline(THREE, o = {}) {
  return {
    body: partShapes(THREE, owlPart("body"), o)[0],
    ears: [partShapes(THREE, owlPart("ear-left"), o)[0], partShapes(THREE, owlPart("ear-right"), o)[0]],
  };
}

/** The triangles of a part's ink outline, from its shape sampled at `divisions` points a curve, as a flat position array (z = 0), or null with no stroke. */
export function partStroke(THREE, part, o = {}, divisions = 24) {
  if (!part.stroke) return null;
  const { sx, sy } = { sx: o.scaleX === undefined ? (o.scale === undefined ? 1 : o.scale) : o.scaleX, sy: o.scaleY === undefined ? (o.scale === undefined ? 1 : o.scale) : o.scaleY };
  const width = part.stroke.width * ((sx + sy) / 2);
  const triangles = [];
  for (const shape of partShapes(THREE, part, o)) {
    const points = shape.getPoints(divisions).map((p) => [p.x, p.y]);
    if (points.length > 1 && points[0][0] === points[points.length - 1][0] && points[0][1] === points[points.length - 1][1]) points.pop();
    triangles.push(...strokeTriangles(points, width, true));
  }
  return triangles;
}
