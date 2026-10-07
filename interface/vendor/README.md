# Vendored: three.js

- Package: `three` on npm (https://www.npmjs.com/package/three), fetched with `npm pack three@latest`
- Version: 0.186.1
- Licence: MIT (the text is in `LICENSE-three.txt`)
- Files (copied unchanged from the package's `build/` folder):
  - `three.module.js` (662,772 bytes), sha256 `9052042d676cb0fdc1ddfefe193053f34b7ac0513a616fdac4535d49987812ea`
  - `three.core.js` (1,458,113 bytes), sha256 `9edde002b066a9a05676a6127f67735b62baf399bdea529f2f7e31657da769e6`

`three.module.js` imports `./three.core.js`, so the two files travel together. The prototype imports
`./vendor/three.module.js` by a relative path; nothing is loaded from another host at run time.

To fetch again: `npm pack three@0.186.1`, unpack the tarball, copy `package/build/three.module.js`,
`package/build/three.core.js` and `package/LICENSE` here, and compare the hashes above.
