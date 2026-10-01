# Brindle UI: migrating from v0 to v1

This document lists what changes for applications that use Brindle UI.

## Renamed components

| v0 | v1 |
|----|----|
| `BrDialog` | `BrModal` |
| `BrDropdown` | `BrMenu` |
| `BrSpinner` | `BrLoader` |

## Removed props

- `BrButton`: `flat` is removed; use `variant="ghost"`.
- `BrInput`: `dense` is removed; use `size="sm"`.

## Unchanged

The other 9 components keep their names and props: `BrAlert`, `BrBadge`, `BrCard`, `BrCheckbox`, `BrRadio`, `BrSelect`, `BrTabs`, `BrToast`, `BrTooltip`.

## Codemod

`npx brindle-codemod v1 <path>` applies the renames and the prop replacements. It does not touch documentation files.

## Minimum versions

v1 requires Vue 3.4 or later. Vue 2 is not supported.
