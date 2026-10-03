---
title: Button
description: A control that starts an action. One class, four styles, seven colours.
since: "1.0"
section: Components
---

## Usage

Add the class `btn` to a `button` or an `a` element. Without a style class the button is solid; without a colour class it uses the theme colour.

```html
<button class="btn">Save</button>
```

## Styles

Four styles change how much weight the button carries: `solid`, `soft`, `outline` and `text`.

```html
<button class="btn">Solid</button>
<button class="btn soft">Soft</button>
<button class="btn outline">Outline</button>
<button class="btn text">Text</button>
```

## Colours

Seven colour classes set the role: `theme`, `success`, `error`, `warn`, `muted`, `surface` and `inverse`.

```html
<button class="btn success">Publish</button>
<button class="btn error outline">Delete</button>
<button class="btn surface">Cancel</button>
```

## Rounded

Add `rounded` for a pill shape.

```html
<button class="btn rounded">Subscribe</button>
```

## Disabled

A disabled button keeps its colour at 50% opacity and ignores the pointer.

```html
<button class="btn" disabled>Save</button>
```

## Accessibility

Use a `button` element for actions and an `a` element for navigation. An icon-only button needs an `aria-label`. The focus ring is 2 px of the theme colour, 2 px outside the button.
