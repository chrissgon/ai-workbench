# ADR-0002: Where the example block takes the code it shows

- Status: proposed
- Date: 2026-04-29
- Serves: REQ-4

## Context

REQ-4 asks an example block to show the live result of its content and the code of that content exactly as the author wrote it, written once. A block component has one input, its slot (design, "Component interfaces"). The live preview is the slot. The open point is where the code panel's text comes from.

Not verified when this record was written: whether the slot a component receives still is, or still contains, the text the author wrote. The spike T-cm-4 verifies it.

## Options

### Option A: the component reads the code from its slot
- The example block shows its slot twice: as it is for the preview, and passed through the highlighter for the code panel.
- Consequences: no change to the renderer or to the component interface; one file changes. Works only if the authored text can be taken from the slot.

### Option B: the author writes the code a second time
- The page carries the example and, next to it, the same markup again as a code block.
- Consequences: no change to the renderer. Two copies that drift apart; it contradicts the decision of 2026-04-27 that an example is written once.

### Option C: the renderer hands the authored text to the component
- The renderer passes a block's body twice: the slot, and the unprocessed text as a second argument, `(slot: string, source: string) => string`.
- Consequences: the code panel is exact by construction. It changes `app/markdown.ts` and the component interface of the design, which every block shares.

## Decision

Proposed: Option A, because it touches one file and leaves the shared interface alone. It holds only if the spike T-cm-4 passes its check.

If the spike fails, Option A is not adapted until the check passes: the outcome is recorded below, and the user chooses between Option B and Option C before any file outside the spike's task is changed.

## Spike outcome

- Pending: T-cm-4 has not run.

## Consequences

- To be written when the decision is accepted.
