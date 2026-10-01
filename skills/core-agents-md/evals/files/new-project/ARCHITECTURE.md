# Architecture

Widgets is a library of small, dependency-free interface widgets.

## Components

- `core`: the widget base class, lifecycle (mount, update, destroy) and the event bus.
- `widgets`: one folder per widget (counter, toggle, tooltip); each exports a single class.
- `styles`: one stylesheet per widget, loaded only by that widget.

## Hard rules

1. A widget never imports another widget; shared behaviour goes into `core`.
2. `core` has no runtime dependency.
3. Every widget cleans up its listeners in `destroy`.
