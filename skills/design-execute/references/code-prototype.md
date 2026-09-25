# Code prototype runs

The automatic mode that is always available: the agent writes the artifact as HTML and CSS with the product's real stylesheet and renders it in a browser.

1. One folder per run: `docs/design/results/<artifact>/round-<n>/<direction>/`. Write `index.html` there (one file per frame when the deliverable has several, for example `landing-card.html`, `docs-card.html`).
2. Link the product's real assets the way the brief's non-negotiables say (a pinned CDN stylesheet, the fonts, the logo as inline SVG). Never re-implement a component the product ships.
3. Build the direction as the brief describes it, one direction per folder; do not blend ideas across folders.
4. Render every frame at the sizes of the brief's Deliverables:
   `node scripts/screenshot.mjs --html <file.html> --out <file.png> --width <w> --height <h> [--full-page] [--scale 2] [--dark] [--reduced-motion] [--wait <ms>]`
   The script needs the `playwright` package resolvable from the working directory or `NODE_PATH`; it launches Chromium headless. Use `--wait` for animations to reach their final state, or `--reduced-motion` to capture it directly.
5. Look at every PNG before judging it; fix defects of the build (overflow, a font that did not load, a clipped text) in the same run, because they are not properties of the direction.
6. Record the outputs in the results document: the HTML path and the PNG path per frame.

Gotchas:

- Fonts load asynchronously; the script waits for `document.fonts.ready`, but a font blocked by the network renders in the fallback: check the PNG, not the HTML.
- Text measured for a template (longest title, longest description) must be rendered with those longest values, not with the shortest example.
