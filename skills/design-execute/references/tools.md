# Tool notes

One entry per tool: what it is good at, the mode this workbench can use, and how to run a pack in it. Update an entry after every run that taught something; date the lesson.

## Choosing

| Artifact | First choice | Alternative |
|----------|--------------|-------------|
| screen, landing, documentation page | Claude Design (with the design system onboarded) | code prototype; Figma Make |
| mockup | an image generator with the real screen attached | Claude Design |
| logo | an image generator for exploration, then a vector redraw | Figma (design tool integration) for the vector |
| presentation | Gamma | Claude Design |
| animation | code prototype (CSS and HTML) | Claude Design |
| image (social card, Open Graph) | code prototype (it becomes the build template) | an image generator |

Recommend the first choice unless the user already works in another tool.

## Code prototype

- Mode: automatic, always available when a browser can be launched.
- Good at: real components with real behaviour, animations, templates that become product code, exact sizes.
- Weak at: wide visual exploration; the agent explores fewer ideas per round than a design tool.
- Run: see `code-prototype.md`.

## Claude Design

- Mode: assisted for generation (no generation interface for agents); its design-system projects can be written by an integration where the environment has one.
- Good at: screens and pages with a strong visual direction; reads a code repository to build a design system; accepts reference images; hands a chosen design back to the coding agent.
- Setup once per product: a design-system project built from the product's repository with an onboarding prompt that names the files to read, what to produce and what never to invent, ending with a verification page of every token and component. Check that page before any screen. (2026-09-24, perfectui: the onboarding produced a faithful system on the first try.)
- Run: one project per direction; attach the brief file and the reference images; paste the prompt; do not attach an earlier design of the same artifact in round 1.
- Collect: screenshots at each required width, the share link, and the exported code or the hand-off to the coding agent for the chosen direction.

## Figma Make

- Mode: assisted.
- Good at: interactive prototypes with code in the Figma ecosystem.
- Lessons (2026-09-23, perfectui landing): an attached frame triggered its design-to-code behaviour and the result was a copy of the frame; custom skills run only when invoked by their slash command in the prompt; importing a library's variables needs a paid plan and a published library and flattens variables into raw values; a Make kit can bundle an npm package and guidelines. The first result stayed "well below" the quality wanted.
- Run: a new Make file per direction from the file browser; attach the brief, not the frame; start the prompt with the product skill's slash command if one was uploaded; link the product's stylesheet explicitly.

## Figma (design tool integration)

- Mode: automatic where the integration exists.
- Good at: composing screens from the file's own variables and components with bound tokens; vectors; structural references and hand-off files.
- Weak at: invention. A composed landing was reviewed as "not bad, but too basic" (2026-09-23); use it for documentation-like screens, hand-off frames and vector clean-up, not for exploration.
- Run: follow the integration's own skills for writing to a file; sequential writes; one screenshot per frame; targeted fixes. Writes to the user's file pass the confirmation gate.

## Gamma

- Mode: assisted.
- Good at: presentations and simple one-page documents from text.
- Run: import the brief's Slides part as the outline; attach the design system's colours and fonts as the theme; one generation per direction.

## Image generator (class `generator:image`)

- Mode: automatic when a provider for the class is configured (`providers/generator/<impl>.py generate --prompt-file … --size WxH --out …`), assisted otherwise (the user pastes the prompt in their image tool).
- Good at: mockup scenes, illustration, logo exploration.
- Weak at: exact text and exact brand colours; never trust it for final text or vectors.
- Run: one prompt per direction; generation spends credits, so automatic runs pass the confirmation gate.
