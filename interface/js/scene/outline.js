// The outline of a hovered object: the edges of the object's own meshes, standing a small distance off the surface, as one line
// geometry in world space. Nothing here is a bounding box: a box was drawn around the City's building and took in its porch, its
// plants and its roof units, so the outline was a giant rectangle that did not follow the building (the maintainer, 2026-10-08).
//
// Which meshes make the outline: those of the object marked `userData.shell` (the building's slabs, bodies and roof, a rack's cabinet,
// a floor's slab and walls, the wall screen); an object with none marked uses all of its visible meshes (the figure, the desk, the
// tray, a sheet, the console). The offset is in world units on each axis of the part, so a thin sheet and a tall building both stand
// `pad` off their surface.

export const EDGE_ANGLE = 35;   // degrees: the angle between two faces above which their shared edge is drawn

/** The meshes that make an object's outline. */
export function outlineMeshes(object) {
  const all = [];
  const shell = [];
  const walk = (node) => {
    if (!node.visible) return;
    if (node.isMesh) {
      all.push(node);
      if (node.userData && node.userData.shell) shell.push(node);
    }
    for (const child of node.children) walk(child);
  };
  walk(object);
  return shell.length ? shell : all;
}

/** The outline's line geometry (world space) for `object`, `pad` world units off each part. Free it with dispose(). */
export function outlineGeometry(THREE, object, pad, angle = EDGE_ANGLE) {
  object.updateWorldMatrix(true, true);
  const points = [];
  const box = new THREE.Box3();
  const centre = new THREE.Vector3();
  const scale = new THREE.Vector3();
  for (const mesh of outlineMeshes(object)) {
    mesh.updateWorldMatrix(true, false);
    const edges = new THREE.EdgesGeometry(mesh.geometry, angle);
    if (!mesh.geometry.boundingBox) mesh.geometry.computeBoundingBox();
    box.copy(mesh.geometry.boundingBox);
    box.getCenter(centre);
    scale.setFromMatrixScale(mesh.matrixWorld);
    const half = { x: (box.max.x - box.min.x) / 2 * scale.x, y: (box.max.y - box.min.y) / 2 * scale.y, z: (box.max.z - box.min.z) / 2 * scale.z };
    const grow = { x: half.x > 1e-6 ? 1 + pad / half.x : 1, y: half.y > 1e-6 ? 1 + pad / half.y : 1, z: half.z > 1e-6 ? 1 + pad / half.z : 1 };
    const position = edges.getAttribute("position");
    for (let i = 0; i < position.count; i++) {
      position.setXYZ(i,
        centre.x + (position.getX(i) - centre.x) * grow.x,
        centre.y + (position.getY(i) - centre.y) * grow.y,
        centre.z + (position.getZ(i) - centre.z) * grow.z);
    }
    edges.applyMatrix4(mesh.matrixWorld);
    points.push(...position.array);
    edges.dispose();
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(points, 3));
  return geometry;
}
