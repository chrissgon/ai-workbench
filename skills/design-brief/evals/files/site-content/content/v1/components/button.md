---
title: Button
description: A control that starts an action. One class, four styles, seven colours.
since: "1.0"
section: Components
---

## Usage

Add the class `pui-btn` to a `button` or an `a` element. Without a style class the button is solid; without a colour class it uses the theme colour.

```html
<button class="pui-btn">Save</button>
```

## Styles

Four styles change how much weight the button carries: `solid`, `soft`, `outline` and `text`.

```html
<button class="pui-btn">Solid</button>
<button class="pui-btn pui-soft">Soft</button>
<button class="pui-btn pui-outline">Outline</button>
<button class="pui-btn pui-text">Text</button>
```

## Colours

Seven colour classes set the role: `theme`, `success`, `error`, `warn`, `muted`, `surface` and `inverse`.

```html
<button class="pui-btn pui-success">Publish</button>
<button class="pui-btn pui-error pui-outline">Delete</button>
<button class="pui-btn pui-surface">Cancel</button>
```

## Rounded

Add `pui-rounded` for a pill shape.

```html
<button class="pui-btn pui-rounded">Subscribe</button>
```

## Disabled

A disabled button keeps its colour at 50% opacity and ignores the pointer.

```html
<button class="pui-btn" disabled>Save</button>
```

## Accessibility

Use a `button` element for actions and an `a` element for navigation. An icon-only button needs an `aria-label`. The focus ring is 2 px of the theme colour, 2 px outside the button.
