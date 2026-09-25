# Prompting AI design tools

Lessons from real runs (Figma Make, Claude Design, design-tool integrations), written as rules.

## What makes a tool produce something worth keeping

- Say it is an exploration and describe the failure case in one sentence ("a plain stack of equal cards with text left and demo right is the failure we already have"). Tools default to the safest layout unless told the safe layout is the problem.
- Name one element at a scale nothing else reaches: a 96 px headline, a demo filling half the viewport, a number as the hero. Drama is a measurable instruction, not an adjective.
- Give depth explicitly: layered bands, an inverted band, blurred glows, grid lines or dot fields, whatever the design system allows.
- Motion must prove a claim of the section (classes type themselves, bars grow, items strike through) and have a final state; otherwise tools add decorative motion.
- Illustration from the product's own parts (its components, its mark) beats stock art, device frames and 3D scenes, and stays on brand.
- End the prompt with a self-check the tool must answer ("list three things this does that a plain version would not"); it pushes the tool past its first draft.

## What makes a tool copy or drift

- An attached design of the same artifact: the tool switches to design-to-code and reproduces it. Attach the brief and reference images instead; attach the old design only in round 2, as structure.
- Three directions in one run: the tool blends them. One run, one project or one file per direction.
- Token names without values: the tool falls back to its own palette. Write the values, or confirm the tool loaded the design system and still restate the brand colour and display size.
- A library the tool cannot load: the tool imitates the components with its own CSS. Make linking the real stylesheet (CDN URL pinned to a version) non-negotiable, and give real markup.
- Tool-side skills and kits are often invoked explicitly (a slash command); an uploaded skill that is never invoked does nothing.

## Shape of the prompt

1. One line: what to design, for whom, and that it is an exploration.
2. The failure case and the references as attitudes.
3. `Direction:` slot, filled per run with one direction from the brief.
4. Non-negotiables: real assets or stylesheet, fonts, colours only from the brief, what never to add.
5. Drama and motion instructions specific to the artifact.
6. Deliverables for this round (sizes, modes, states) and the self-check.

Keep the prompt short when the brief is attached (the prompt points at it); make it self-contained, with the copy and the structure inside, when the tool will not receive the brief as a file.
