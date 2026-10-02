import { readFileSync } from "node:fs";

export interface ManifestEntry {
  id: string;
  deprecated?: boolean;
}

export interface Manifest {
  latest: string;
  versions: ManifestEntry[];
}

const ID = /^\d+\.\d+$/;

export function parseManifest(text: string): Manifest {
  const data = JSON.parse(text) as Manifest;
  if (!Array.isArray(data.versions) || data.versions.length === 0) {
    throw new RangeError('versions.json: "versions" must be a non-empty list');
  }
  for (const entry of data.versions) {
    if (!ID.test(entry.id)) throw new RangeError(`versions.json: "${entry.id}" is not a <major>.<minor> id`);
  }
  if (!data.versions.some((entry) => entry.id === data.latest)) {
    throw new RangeError(`versions.json: latest "${data.latest}" is not listed in "versions"`);
  }
  return data;
}

export function loadManifest(path: string): Manifest {
  return parseManifest(readFileSync(path, "utf8"));
}
