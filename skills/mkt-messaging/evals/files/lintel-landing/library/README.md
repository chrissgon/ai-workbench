# Lintel UI

A small CSS and JavaScript library for interfaces built on native HTML.

Lintel UI ships only what it needs: no runtime dependencies, no CSS reset, no font import, and every rule is attached to an `ltl-` class. Behaviour comes from the browser (`<details>`, `<dialog>`, `popover`); the JavaScript only adds what a browser lacks.

## Install

```bash
npm i @lintelkit/lintel
```

```js
import "@lintelkit/lintel/lintel.css";
```

Or import only the components you use:

```js
import "@lintelkit/lintel/core.css";
import "@lintelkit/lintel/components/button.css";
```

The JavaScript is optional. It is a loader that downloads a fallback only for what your browser is missing; you need it for the overlays and for the checkbox `indeterminate` attribute:

```js
import "@lintelkit/lintel";
```

From a CDN:

```html
<link rel="stylesheet" href="https://cdn.example/@lintelkit/lintel@1.0.0/dist/lintel.css" />
```

Lintel UI is ESM only and exposes nothing on `window` or `document`.

## Writing a component

Every element is made of up to three independent classes: a shape, a style and a colour.

```html
<button class="ltl-btn ltl-solid ltl-theme">Save</button>
<button class="ltl-btn ltl-outline ltl-surface">Cancel</button>
<span class="ltl-chip ltl-soft ltl-success">Active</span>
```

## Components

`dist/css/components/` holds one stylesheet per component: accordion, badge, button, card, chip, dropdown, float, form, group, list, modal, table, timeline, tooltip.

## Documentation

The documentation is at https://lintel.example. Coming from `0.19`? See `MIGRATION.md`.

## License

MIT.
