---
title: Button
description: A control that starts an action. One class, four styles, seven colours.
since: "1.0"
section: Components
---

## Usage

Add the class `plu-btn` to a `button` or an `a` element. Without a style class the button is solid; without a colour class it uses the theme colour.

```html
<button class="plu-btn">Save</button>
```

## Styles

Four styles change how much weight the button carries: `solid`, `soft`, `outline` and `text`.

```html
<button class="plu-btn">Solid</button>
<button class="plu-btn plu-soft">Soft</button>
<button class="plu-btn plu-outline">Outline</button>
<button class="plu-btn plu-text">Text</button>
```

## Colours

Seven colour classes set the role: `theme`, `success`, `error`, `warn`, `muted`, `surface` and `inverse`.

```html
<button class="plu-btn plu-success">Publish</button>
<button class="plu-btn plu-error plu-outline">Delete</button>
<button class="plu-btn plu-surface">Cancel</button>
```

## Rounded

Add `plu-rounded` for a pill shape.

```html
<button class="plu-btn plu-rounded">Subscribe</button>
```

## Disabled

A disabled button keeps its colour at 50% opacity and ignores the pointer.

```html
<button class="plu-btn" disabled>Save</button>
```

## Accessibility

Use a `button` element for actions and an `a` element for navigation. An icon-only button needs an `aria-label`. The focus ring is 2 px of the theme colour, 2 px outside the button.
