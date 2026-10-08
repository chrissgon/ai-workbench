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

/** Read one token's resolved colour through a probe element placed in `host`. */
function read(probe, name) {
  probe.style.setProperty("color", `var(${name})`);
  return new THREE.Color().setStyle(getComputedStyle(probe).color, THREE.SRGBColorSpace);
}

/** The palette: the token colours, the recipes derived from them and whether the scheme is dark. */
export function readPalette(host) {
  const probe = document.createElement("span");
  probe.className = "wb-probe";
  host.appendChild(probe);
  const T = {};
  for (const [key, name] of Object.entries(TOKEN_NAMES)) T[key] = read(probe, name);
  probe.remove();
  const mix = (a, b, t) => a.clone().lerp(b, t);
  const dark = T.bgToken.r + T.bgToken.g + T.bgToken.b < 1.5;
  const bg = T.bg;
  const palette = {
    dark, T, mix, bg,
    ground: T.muted,
    pale: mix(bg, T.theme, 0.25),
    warm: dark ? T.warn.clone() : mix(bg, T.warn, 0.72),
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
  palette.windows = { lit: palette.warm, pale: palette.pale, dark: T.border };
  return palette;
}
