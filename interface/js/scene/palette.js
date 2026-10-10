// The scene's colours: none of its own. Every colour is read from the page's CSS custom properties when the scene is
// built and again when the colour scheme changes, so dark mode (and a new primary colour) flows into the scene. The
// recipes (a mix of two tokens) are the handoff's scene.md section 3.

import * as THREE from "../three.js";

// The names read through a probe element. `--wb-raised` and `--wb-ground` are the page's two derived properties
// (DEVIATION-1): the scene reads them where the design tool read the library's background tokens.
export const TOKEN_NAMES = Object.freeze({
  bg: "--wb-raised", muted: "--wb-ground", emphasis: "--pui-bg-emphasis", text: "--pui-text", textMuted: "--pui-text-muted",
  border: "--pui-border", theme: "--pui-theme", warn: "--pui-warn", success: "--pui-success", error: "--pui-error",
  mutedRole: "--pui-muted", bgToken: "--pui-bg",
});

// A light's colour is not a painted colour (DEVIATION-8): named once here.
export const LIGHT_WHITE = 0xffffff;
export const SHADOW_BLACK = 0x000000;

/**
 * Ask for a new palette when the colours change: the system's scheme (the media query) or the person's choice of light or dark (the
 * library's `data-pui-mode` attribute on the root element, set by `mode.js`). Returns a function that stops listening. The query, the root
 * and the observer class are arguments so a test runs it with stand-ins; where `MutationObserver` is missing the query alone is watched.
 */
export function watchScheme(onChange, { query = window.matchMedia("(prefers-color-scheme: dark)"), root = document.documentElement,
  Observer = typeof MutationObserver === "function" ? MutationObserver : null } = {}) {
  query.addEventListener("change", onChange);
  const observer = Observer ? new Observer(() => onChange()) : null;
  if (observer) observer.observe(root, { attributes: true, attributeFilter: ["data-pui-mode"] });
  return () => {
    query.removeEventListener("change", onChange);
    if (observer) observer.disconnect();
  };
}

/** Read one token's resolved colour through a probe element placed in `host`. */
function read(probe, name) {
  probe.style.setProperty("color", `var(${name})`);
  return new THREE.Color().setStyle(getComputedStyle(probe).color, THREE.SRGBColorSpace);
}

/**
 * A mix of two colours as the page's stylesheet mixes them: `color-mix(in srgb, a, b t)`, a straight blend of the encoded channels (round 4,
 * `scene.css`). Three.js keeps colours in a linear working space, where a blend of the same two colours comes out lighter, so the blend is made
 * in the encoded space and brought back.
 */
export function mixSrgb(a, b, t) {
  const x = a.clone().convertLinearToSRGB();
  const y = b.clone().convertLinearToSRGB();
  x.r += (y.r - x.r) * t;
  x.g += (y.g - x.g) * t;
  x.b += (y.b - x.b) * t;
  return x.convertSRGBToLinear();
}

/** The palette: the token colours, the recipes derived from them and whether the scheme is dark. */
export function readPalette(host) {
  const probe = document.createElement("span");
  probe.className = "wb-probe";
  host.appendChild(probe);
  const T = {};
  for (const [key, name] of Object.entries(TOKEN_NAMES)) T[key] = read(probe, name);
  // The decision mark is the same amber in light and in dark (R-20): its three tones are mixed from the tokens as the dark scheme gives them.
  probe.style.setProperty("color-scheme", "dark");
  const inDark = { warn: read(probe, TOKEN_NAMES.warn), text: read(probe, TOKEN_NAMES.text), bgToken: read(probe, TOKEN_NAMES.bgToken) };
  probe.remove();
  const mix = mixSrgb;
  const dark = T.bgToken.r + T.bgToken.g + T.bgToken.b < 1.5;
  const bg = T.bg;
  const palette = {
    dark, T, mix, bg, inDark,
    ground: T.muted,
    pale: mix(bg, T.theme, 0.25),
    // R-18: a lit window is a warm white, not amber (`scene.css` `.m-g-lit`): the raised surface with a little of the warn colour in light, the
    // text colour with a little of the brand's light brown in dark. The full amber is left to the decision marks.
    warm: dark ? mix(T.text, T.theme, 0.36) : mix(bg, T.warn, 0.34),
    glass: mix(bg, T.theme, dark ? 0.18 : 0.12),
    shell: dark ? T.emphasis.clone() : bg.clone(),
    leafA: mix(bg, T.success, dark ? 0.55 : 0.66),
    leafB: mix(bg, T.success, dark ? 0.42 : 0.52),
    trunk: mix(T.textMuted, T.warn, 0.25),
    wood: mix(bg, T.warn, dark ? 0.28 : 0.2),
    metal: T.textMuted.clone(),
    ink: dark ? mix(T.emphasis, T.text, 0.15) : mix(T.text, T.textMuted, 0.25),
    screenOff: dark ? mix(bg, T.theme, 0.12) : mix(T.text, T.theme, 0.28),
    drawer: mix(bg, T.theme, 0.55),
    lot: dark ? mix(T.muted, bg, 0.6) : bg.clone(),
    deskTop: dark ? mix(T.emphasis, T.text, 0.12) : mix(bg, T.emphasis, 0.6),
    skin: dark ? mix(T.emphasis, T.text, 0.35) : mix(bg, T.emphasis, 0.35),
    shadowColor: dark ? new THREE.Color(SHADOW_BLACK) : T.text.clone(),
    shadowOpacity: dark ? 0.35 : 0.1,
    hemiIntensity: dark ? 1.15 : 1.85,
    sunIntensity: dark ? 0.9 : 1.45,
  };
  // A window is warm when its floor's agent works and the border tone otherwise, in light and in dark (WP-9.8); `pale` stays
  // the front door's colour only.
  palette.windows = { lit: palette.warm, grey: T.border };
  return palette;
}

/**
 * The City's drawing in the colours of `scene.css` (round 4): every one a token or a mix of two tokens, in light and in dark, as that file writes
 * them. A face of a solid is top, left (the front, +z) or right (+x), each its own tone, so the drawing is flat faces and needs no light.
 * Pure: it reads `palette.T`, `palette.mix`, `palette.bg` and `palette.dark` only (a stand-in without the two tokens `bgToken` and `muted`
 * takes the surface for them). Returns Colours (and {top, left, right} for a solid).
 */
export function cityTones(palette) {
  const { T, mix, bg, dark } = palette;
  const bgt = T.bgToken || bg;                       // --pui-bg
  const emph = T.emphasis;                           // --pui-bg-emphasis
  const tm = T.textMuted;
  const tx = T.text;
  const th = T.theme;
  const ink = dark ? bgt : tx;                       // --wb-shadow-ink: light-dark(--pui-text, --pui-bg)
  const pick = (light, deep) => (dark ? deep : light);
  const warnD = (palette.inDark && palette.inDark.warn) || T.warn;
  const textD = (palette.inDark && palette.inDark.text) || tx;
  const bgD = (palette.inDark && palette.inDark.bgToken) || bgt;
  const solid = (top, left, right) => ({ top, left, right });
  return {
    road: pick(mix(emph, tm, 0.24), mix(bg, emph, 0.6)),
    lane: pick(bg.clone(), tm.clone()),
    kerb: pick(mix(emph, tm, 0.45), mix(bgt, emph, 0.55)),
    walk: pick(mix(bg, emph, 0.55), mix(emph, T.border, 0.35)),
    plaza: pick(bg.clone(), mix(bgt, bg, 0.78)),
    grass: pick(mix(bg, T.success, 0.26), mix(bgt, T.success, 0.3)),
    trunk: mix(tm, T.warn, 0.25),
    // the four tones of a crown, lightest first: facets are given the tone of the light they face
    crown: [
      pick(mix(bg, T.success, 0.48), mix(bgt, T.success, 0.62)),
      pick(mix(bg, T.success, 0.62), mix(bgt, T.success, 0.5)),
      pick(mix(bg, T.success, 0.76), mix(bgt, T.success, 0.4)),
      pick(mix(T.success, ink, 0.14), mix(bgt, T.success, 0.31)),
    ],
    shell: solid(pick(mix(bg, emph, 0.75), mix(bgt, emph, 0.72)), pick(mix(bg, emph, 0.75), mix(bgt, emph, 0.72)), pick(mix(bg, emph, 0.25), mix(bgt, emph, 0.92))),
    ledge: solid(pick(bg.clone(), mix(emph, tm, 0.42)), pick(mix(emph, tm, 0.38), mix(emph, tm, 0.2)), pick(mix(emph, tm, 0.2), mix(emph, tm, 0.3))),
    glass: pick(mix(emph, tm, 0.78), mix(bgt, bg, 0.55)),
    glassOff: pick(mix(bg, emph, 0.9), mix(bgt, emph, 0.6)),
    glassLit: pick(mix(bg, T.warn, 0.34), mix(tx, th, 0.36)),
    store: pick(mix(bg, th, 0.34), mix(bgt, th, 0.46)),
    door: pick(mix(bg, th, 0.62), mix(bgt, th, 0.66)),
    sill: pick(bg.clone(), mix(emph, tm, 0.34)),
    jamb: pick(mix(emph, tm, 0.7), bgt.clone()),
    roof: solid(mix(th, ink, 0.1), mix(th, ink, 0.36), mix(th, ink, 0.22)),
    roofFloor: th.clone(),
    roofIn: solid(mix(th, ink, 0.18), mix(th, ink, 0.3), mix(th, ink, 0.18)),
    unit: solid(pick(mix(emph, tm, 0.3), mix(emph, tm, 0.55)), pick(mix(emph, tm, 0.7), mix(emph, tm, 0.28)), pick(mix(emph, tm, 0.5), mix(emph, tm, 0.4))),
    post: tm.clone(),
    // R-20: the same amber in light and in dark (`.m-ex` sets `color-scheme: dark`)
    mark: solid(mix(warnD, textD, 0.3), mix(warnD, bgD, 0.26), warnD.clone()),
    beacon: bgt.clone(),
    bracket: th.clone(),
    agent: ink.clone(),
    shadow: ink.clone(),
  };
}
