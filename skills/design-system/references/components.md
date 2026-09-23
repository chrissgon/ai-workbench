# Component states and accessibility minimums

Loaded at step 6 of `design-system`.

## States to list per component

| State | List it when | What changes |
|-------|--------------|--------------|
| default | always | the resting look |
| hover | pointer-operable | fill, ink or underline change; never colour alone for meaning |
| focus-visible | focusable | a ring at least 2 px wide with 3:1 contrast against the adjacent colours, never removed |
| active | pressable | pressed look |
| selected or current | navigation items, tabs, results | a mark beyond colour (weight, bar, icon) |
| disabled | can be disabled | reduced contrast is allowed; must not receive focus |
| loading | fetches or computes | placeholder or spinner; the layout must not jump when content arrives |
| empty | lists and results | a message, never a blank area |
| error | forms and fetches | message text next to the control, `aria-invalid` on the control |
| open and closed | disclosures, dialogs, menus | both looks; the closed one is usually the default |

## Accessibility minimums

- Text contrast 4.5:1; large text (24 px, or 19 px bold) and interface elements 3:1 (WCAG 2.2 AA).
- Touch targets at least 24 × 24 CSS px (WCAG 2.2 AA, 2.5.8); 44 × 44 is the comfortable value for primary actions.
- Focus is visible on every focusable element in every mode.
- Motion respects `prefers-reduced-motion`; nothing essential is conveyed by animation.
- Every icon-only control has an accessible name.

## Site-only components a documentation site usually needs

Navigation item (levels, current), on-page heading link, code block (with copy control and language label), example block (preview and code tabs), search result, version switch item, callout or note, table with horizontal scroll, keyboard hint. Each is a row in the components table with an owner of `site`.
