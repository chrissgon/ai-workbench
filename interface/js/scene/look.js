// What the scene shows for a state, as plain choices with no three.js and no document, so a test can run them:
//   - a window is warm and unlit when the agent of its floor works, grey otherwise (the maintainer's rule of 2026-10-08;
//     there is no in-between state any more);
//   - an outline of the theme colour is drawn only for the object the pointer is on or the route selected.

/** The window state of a floor: "lit" when its agent works, "grey" in every other case (waiting, idle, off, not accepted). */
export function windowState(working) {
  return working ? "lit" : "grey";
}

/** The colour of a window state: the warm recipe when lit, the border tone otherwise (the same rule in light and dark). */
export function windowColour(palette, state) {
  return state === "lit" ? palette.warm : palette.windows.grey;
}

/** A lit window is drawn with an unlit material; a grey one takes the light of the scene. */
export function windowUnlit(state) {
  return state === "lit";
}

/** True when the outline lines of object `id` are drawn: it is hovered or it is the one the route selected. */
export function outlineVisible(id, hoverId, selectedId) {
  return id !== null && id !== undefined && (id === hoverId || id === selectedId);
}

/** Show the outline lines of the registered objects ({id, lines}) that are hovered or selected and hide all the others. */
export function applyOutlineVisibility(outlines, hoverId, selectedId) {
  for (const o of outlines) {
    const on = outlineVisible(o.id, hoverId, selectedId);
    for (const line of o.lines) line.visible = on;
  }
}

/**
 * What `show(kind, model)` must do, from what was shown before: "none" (the same model), "relabel" (the same structure, other words:
 * only the labels and tooltips change, nothing that moves is built again) or "build". `before` is {signature, structure, built};
 * `structureOf` is the builder's `structure` function or null (then the whole model is its structure).
 */
export function showPlan(before, kind, model, structureOf) {
  const signature = JSON.stringify([kind, model]);
  const structure = JSON.stringify([kind, structureOf ? structureOf(model) : model]);
  let action = "build";
  if (signature === before.signature) action = "none";
  else if (before.built && structure === before.structure) action = "relabel";
  return { action, signature, structure };
}
