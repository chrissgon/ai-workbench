# Profile: image (social card, Open Graph image, banner, illustration, icon set)

The Content section must contain:

- **Size:** every output size in pixels (for example 1200 × 630 for Open Graph, 1080 × 1080 for a square post) and the safe area where text must stay.
- **Format:** file format and weight ceiling (for example PNG under 300 KB).
- **Text:** every text on the image, verbatim with its source, its hierarchy, and the type role each text uses, by its token name and size from the design system. Text must stay legible in a feed preview (at least 40 px on a 1200 × 630 card): give each text a role at or above that size. Never write a size the design system does not have, scaled or derived: when the hierarchy needs a size no role gives (a title larger than the largest role), the text takes the largest role, and the missing size is an open question, `- OPEN-n: The design system has no type role above <largest role> (<size>) for <which text>. Blocks: <the card's type sizes>. Recommended: add a card role to the design system with design-system, because the brief copies values and never invents them.`, with Readiness `no, because OPEN-n`.
- For templates (one image per page), a **Variable fields** list: each field, where its values come from, and the longest real value it must fit with its character count, computed with `longest_value.py` (in the `scripts/` folder next to SKILL.md) over the real values (the page titles and section names in the flows or the content files). "Unknown" is written only when no source lists the values; then ask the user for the list.

Criteria that matter for images:

- Legible at thumbnail size (the image at 25% still reads).
- Identity: mark or wordmark, brand colour and type from the design system.
- Text verbatim; variable fields fit their longest value without overflow.
- Output size, format and weight as listed.
- Contrast of text on background passes AA.

Deliverables: round 1, one image per direction at the main size; round 2, every size and, for templates, three real pages rendered.
