# Profile: screen (page, dialog, landing, documentation page)

The Content section must contain these labelled parts (the lint looks for the labels):

- **Regions:** every region of the SCREEN in the flows, in priority order, each with its copy verbatim, the component or real markup it uses, and what the reader does there. Priority order is reading order at every width.
- **States:** every state the flows list for the SCREEN (empty, loading, no results, notice, copied, no JavaScript, reduced motion…), each as a difference from the default.
- **Breakpoints:** the widths to design (the design system's widest and narrowest at least) and what changes at each; what must stay inside the first viewport on the narrowest.
- **Motion:** per region, what moves, why (the claim it proves), duration, and the final state shown under reduced motion. Documentation and application screens move little; landing pages carry the motion.

Criteria that matter for screens:

- Faithful: every colour, type size, radius and spacing traces to the design system.
- Real components: demos and controls are the product's real markup with real behaviour.
- Copy verbatim, no added sentence.
- Narrow first viewport: what the flows require is visible without scrolling at the narrowest width.
- Accessibility: contrast pairs the design system passes, targets, visible focus, reading order.
- For marketing pages, drama: one element at a scale nothing else reaches.
- Buildable within the performance budget of the product's specs.

Deliverables: round 1, the top of the page (or the main state) at the widest width in light mode, one run per direction; round 2, all breakpoints, modes and states of the chosen direction.
