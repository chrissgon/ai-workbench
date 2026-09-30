![Plinth UI](https://plinthui.example/logo.png)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# Plinth UI

An exceptionally lightweight and highly customizable CSS and JavaScript library for crafting elegant user interfaces. 🎨💡

Plinth UI ships the bare minimum: no runtime dependencies, no CSS reset, no font import, and no rule that is not attached to a `pui-` class. Behavior comes from the browser — `<details>`, `<dialog>`, `popover` — and JavaScript only fills in what a browser is missing.

## 📦 Install

### By package manager

- Install package

```bash
# npm
npm i @plinthkit/plinthui

# yarn
yarn add @plinthkit/plinthui

# pnpm
pnpm i @plinthkit/plinthui

# bun
bun i @plinthkit/plinthui
```

- Import library on your project.

```js
import "@plinthkit/plinthui/plinthui.css";
```

Or import only the components you use:

```js
import "@plinthkit/plinthui/core.css";
import "@plinthkit/plinthui/components/button.css";
```

The JavaScript is optional. It is a loader that downloads a fallback only for
what your browser is missing, and you need it for the overlays and for the
checkbox `indeterminate` attribute:

```js
import "@plinthkit/plinthui";
import { setMode } from "@plinthkit/plinthui/mode";
```

### By CDN's.

- Import CDN's on your html.

```html
<link
  rel="stylesheet"
  href="https://cdn.jsdelivr.net/npm/@plinthkit/plinthui@latest/dist/plinthui.css"
/>

<script type="module">
  import "https://cdn.jsdelivr.net/npm/@plinthkit/plinthui@latest/dist/js/index.js";
</script>
```

Plinth UI is ESM only and exposes nothing on `window` or `document`.

## ✍🏻 Writing a component

Every element is made of up to three independent classes: a shape, a style and
a color.

```html
<button class="pui-btn pui-solid pui-theme">Save</button>
<button class="pui-btn pui-outline pui-surface">Cancel</button>
<span class="pui-chip pui-soft pui-success">Active</span>
```

## 📚 Documentation

Read all documentation in [docs](https://git.example/plinthkit/plinthui/tree/main/docs) folder or in the [official website](https://plinthui.example/).

Coming from `0.x`? See [MIGRATION.md](https://git.example/plinthkit/plinthui/blob/main/MIGRATION.md).

## 💪🏻 Contribution

This project is open source and welcomes community contributions. Feel free to fork, implement improvements, and submit a pull request. Every contribution is valued and appreciated!

Feel free to explore the source code, provide feedback, and report any issues you encounter.

[Plinth UI Figma](https://figma.example/file/pLt7Kq2mN4vR8tY1wZ3cXd/PlinthUI) is free for both commercial and personal projects.

## ❤️ Authors

- [@rowan-hale](https://git.example/rowan-hale)
