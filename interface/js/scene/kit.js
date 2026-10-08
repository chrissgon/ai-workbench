// The drawing kit of one built scene: cached materials, shared geometry and the helpers that put boxes and cylinders in
// a group. Everything it creates is tracked so `dispose()` frees it (geometries and materials) when the scene is
// rebuilt or left. `box(w, h, d, x, y, z, colour)` puts the box's bottom face at y, as the design tool's code does.

import * as THREE from "../three.js";

export function createKit(palette) {
  const lambert = new Map();
  const basic = new Map();
  const geometries = [];
  const unit = new THREE.BoxGeometry(1, 1, 1);
  const unitEdges = new THREE.EdgesGeometry(unit);
  const edgeMaterial = new THREE.LineBasicMaterial({ color: palette.T.border });
  const themeLine = new THREE.LineBasicMaterial({ color: palette.T.theme });
  const materials = [edgeMaterial, themeLine];

  const lit = (colour) => {
    const key = colour.getHexString();
    if (!lambert.has(key)) lambert.set(key, new THREE.MeshLambertMaterial({ color: colour }));
    return lambert.get(key);
  };
  const flat = (colour) => {
    const key = "f" + colour.getHexString();
    if (!lambert.has(key)) lambert.set(key, new THREE.MeshLambertMaterial({ color: colour, flatShading: true }));
    return lambert.get(key);
  };
  const unlit = (colour) => {
    const key = colour.getHexString();
    if (!basic.has(key)) basic.set(key, new THREE.MeshBasicMaterial({ color: colour }));
    return basic.get(key);
  };
  const track = (geometry) => {
    geometries.push(geometry);
    return geometry;
  };

  const kit = {
    palette, THREE, lit, flat, unlit, track, edgeMaterial, themeLine, unitEdges,
    /** A box with its bottom face at y. o: {unlit, cast, edges, shell, parent}; `shell` marks a part of the object's outline (outline.js). */
    box(w, h, d, x, y, z, colour, o = {}) {
      const mesh = new THREE.Mesh(unit, o.unlit ? unlit(colour) : lit(colour));
      mesh.scale.set(w, h, d);
      mesh.position.set(x, y + h / 2, z);
      mesh.castShadow = o.cast !== false;
      mesh.receiveShadow = true;
      if (o.shell) mesh.userData.shell = true;
      (o.parent).add(mesh);
      if (o.edges) {
        const lines = new THREE.LineSegments(unitEdges, edgeMaterial);
        lines.scale.copy(mesh.scale);
        lines.position.copy(mesh.position);
        o.parent.add(lines);
      }
      return mesh;
    },
    /** A mesh of a geometry made by the caller (tracked). o: {unlit, flat, cast, shell, parent}. */
    mesh(geometry, colour, x, y, z, o = {}) {
      const mesh = new THREE.Mesh(track(geometry), o.unlit ? unlit(colour) : o.flat ? flat(colour) : lit(colour));
      mesh.position.set(x, y, z);
      mesh.castShadow = o.cast !== false;
      mesh.receiveShadow = true;
      if (o.shell) mesh.userData.shell = true;
      o.parent.add(mesh);
      return mesh;
    },
    /** A cylinder with its bottom face at y. */
    cyl(rt, rb, h, segments, colour, x, y, z, o = {}) {
      return kit.mesh(new THREE.CylinderGeometry(rt, rb, h, segments), colour, x, y + h / 2, z, o);
    },
    /** A line through points [[x, y, z], ...]. */
    line(points, material, parent) {
      const geometry = track(new THREE.BufferGeometry().setFromPoints(points.map((p) => new THREE.Vector3(...p))));
      const line = new THREE.Line(geometry, material);
      parent.add(line);
      return line;
    },
    /** A material the caller made (the beacon's): freed with the kit. */
    adopt(material) {
      materials.push(material);
      return material;
    },
    dispose() {
      for (const g of geometries) g.dispose();
      geometries.length = 0;
      for (const m of [...lambert.values(), ...basic.values(), ...materials]) m.dispose();
      lambert.clear();
      basic.clear();
      unit.dispose();
      unitEdges.dispose();
    },
  };
  return kit;
}
