# UX flows: Fernleaf, phase P-1

- Owner: design-ux-flows
- Status: approved
- Date: 2027-02-08
- PRD: docs/product/prd.md
- Phase covered: P-1

## Summary

Two screens and one flow: a visitor reads the landing page and gets the app from a store; the app's own screens come in a later phase.

## Sources

- docs/product/prd.md (F-1, 2027-02-01)

## Screens

- SCREEN-1: Landing page. Purpose: show what Fernleaf does and send the visitor to a store. Regions: header with the wordmark, hero with headline and store buttons, three benefit cards, a screenshot of the watering schedule, footer. States: default. Breakpoints: below 720 px the benefit cards stack and the screenshot moves under the hero. Source: PRD F-1.
- SCREEN-2: Store page. Purpose: the store listing the store buttons open. Regions: owned by the store. States: default. Breakpoints: owned by the store. Source: PRD F-1.

## Flows

- FLOW-1: Get the app. Actor: U-1. Trigger: the visitor opens the landing page from a search engine. Steps: 1. on SCREEN-1: read the hero → knows the app reminds them to water each plant; 2. on SCREEN-1: activate a store button → SCREEN-2 opens. End: the visitor is on the store listing. Failures: step 2 with no network: the browser's own error page. Keyboard: Tab to the store button, Enter. Source: PRD F-1.

## Coverage

- F-1: FLOW-1, SCREEN-1, SCREEN-2

## Open questions

- none

## Readiness

- Ready for design-system and design-brief: yes: SCREEN-1 first, because it is the only screen of P-1 the project designs.
