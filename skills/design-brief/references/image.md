# Profile: image (social card, Open Graph image, banner, illustration, icon set)

The Content section must contain:

- **Size:** every output size in pixels (for example 1200 × 630 for Open Graph, 1080 × 1080 for a square post) and the safe area where text must stay.
- **Format:** file format and weight ceiling (for example PNG under 300 KB).
- **Text:** every text on the image, verbatim with its source, and its hierarchy; the minimum text size that stays legible in a feed preview (at least 40 px on a 1200 × 630 card).
- For templates (one image per page), a **Variable fields** list: each field, where its values come from, and the longest real value it must fit with its character count, computed with `longest_value.py` (in the `scripts/` folder next to SKILL.md) over the real values (the page titles and section names in the flows or the content files). "Unknown" is written only when no source lists the values; then ask the user for the list.

Criteria that matter for images:

- Legible at thumbnail size (the image at 25% still reads).
- Identity: mark or wordmark, brand colour and type from the design system.
- Text verbatim; variable fields fit their longest value without overflow.
- Output size, format and weight as listed.
- Contrast of text on background passes AA.

Deliverables: round 1, one image per direction at the main size; round 2, every size and, for templates, three real pages rendered.
