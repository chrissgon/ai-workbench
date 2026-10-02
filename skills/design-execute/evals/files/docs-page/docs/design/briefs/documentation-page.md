# Design brief: documentation-page

- Owner: design-brief
- Status: approved
- Date: 2026-10-01
- Type: screen
- For: SCREEN-2 (Documentation page) of the Marlow documentation site, shown with the guide page "Retries and backoff"
- Values: inline
- Direction: open: three directions
- Lint: ok (2026-10-01)

## Summary

Explore three directions for the documentation page of the Marlow documentation site at 1440 px wide in light mode, with the guide page "Retries and backoff" as the example. The texts, the colours, the typefaces, the mark and the regions of the page are fixed; the composition, the scale of the page title and the treatment of code blocks are open.

## Sources

- docs/design/design-system.md (colours, type, spacing, radii, motion, 2026-09-12)
- docs/design/flows.md (SCREEN-2: regions, states, breakpoints, 2026-09-14)
- content/guide/retries-and-backoff.md (every text of the example page, 2026-09-20)
- site/logo.svg (the mark)
- User answer, 2026-09-22: the example page and the widths of each round

## Subject

Marlow is a small open-source library that runs background jobs for Node.js applications and stores them in a PostgreSQL table the application already has. A developer defines a job as a function, enqueues it with a payload, and Marlow runs it, retries it when it fails and keeps a record of what happened. There is no separate server to operate.

Its documentation site has a landing page, a guide of five pages and a reference of three pages. The documentation page is the template of all eight. Example: the guide page "Retries and backoff" explains that a failed job is retried five times, shows the waiting time before each attempt and gives the code that changes the schedule.

## Audience and voice

- Back-end developers who arrive from a search engine with a failing job and want the answer in the first screen; they fear a page that hides the code under prose.
- Developers evaluating Marlow who read one guide page to judge whether the library is maintained with care; they distrust decoration that slows reading.
- Voice: plain, technical, second person, short sentences, no exclamation marks.
- Words to use: job, queue, attempt, retry, schedule.
- Words to avoid: simply, just, easy, powerful, seamless.

## Creative direction

No previous version.

References as attitudes: the calm of a printed technical manual (one column of text that never exceeds a comfortable measure), the precision of a terminal (code is the most finished thing on the page), no illustration of people, devices or abstract shapes.

- Direction A, "Manual": the page reads like a printed manual. The page title is set very large over a full-width rule, section numbers hang in the left margin of the content, and code blocks sit flush with the text column with a single rule on their left edge.
- Direction B, "Console": code is the hero. Code blocks are dark panels wider than the text column, breaking out to the right over the space of the on-page headings list, and the prose is a quiet commentary between them.
- Direction C, "Timeline": the content is threaded on a vertical line in the brand colour that runs from the page header to the previous and next links; each section heading is a stop on the line, and the on-page headings list mirrors the same line as a miniature.

Every direction keeps the mark, the brand colour as the only accent, the two typefaces and every region of the screen. Allowed: changing the scale of the title, the width of code blocks, the position of the on-page headings list, rules and borders in the border colour. Not allowed: gradients, shadows deeper than the elevation value, illustrations, a second accent colour, any text not listed under Content, restyled syntax colours.

## Visual language

Colours:

| Role | Light | Dark |
| --- | --- | --- |
| Background | #FFFFFF | #0F1115 |
| Surface (sidebar, code block in light mode) | #F6F5F2 | #181B21 |
| Text | #1B1D22 | #ECEAE4 |
| Muted text | #5E636E | #A2A7B1 |
| Border | #DDDAD2 | #2C3038 |
| Brand (the only accent) | #C2410C | #F0703A |
| Code panel (Direction B) | #14161A | #14161A |

Type: Inter for text and JetBrains Mono for code, both served by the site as font files.

| Role | Size | Line height | Weight |
| --- | --- | --- | --- |
| Page title | 44 px (directions may scale it up to 72 px) | 1.1 | 700 |
| Section heading | 26 px | 1.25 | 600 |
| Body | 17 px | 1.65 | 400 |
| Sidebar and on-page list | 15 px | 1.5 | 400, current item 600 |
| Code | 15 px | 1.6 | 400 |
| Small label | 13 px | 1.4 | 500 |

Space: multiples of 4 px; the usual steps are 8 px, 16 px, 24 px, 40 px and 64 px. The text column is at most 720 px wide. Corner radius 8 px on code blocks and controls, 4 px on inline code. Border width 1 px. Elevation: one level only, 0 1 px 2 px at 8% black, for the copy control. Focus: a 2 px outline in the brand colour with a 2 px offset. Motion: 150 ms ease-out for hover and copy feedback; nothing else moves.

Breakpoints: 1440 px (design width), 900 px (the sidebar becomes a panel), 390 px (narrow).

The mark is a clock face in the brand colour:

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><circle cx="24" cy="24" r="20" fill="none" stroke="#C2410C" stroke-width="4"/><path d="M24 12v12l8 6" fill="none" stroke="#C2410C" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/></svg>

## Content

**Regions**, in priority order, with the copy verbatim:

1. Page header: the title "Retries and backoff" and the description "How Marlow retries a failed job, and how to change the schedule."
2. Content with code blocks, each with a copy control labelled "Copy":
   - Section "Default schedule": "A job that throws is retried five times. Marlow waits longer before each attempt: 10 seconds, 1 minute, 5 minutes, 30 minutes and 2 hours."
   - Section "Changing the schedule": "Pass a retry option when you define the job. The list holds the waiting time before each attempt, in seconds." followed by the code block:
     `queue.define("send-receipt", sendReceipt, { retry: [5, 30, 300] });`
   - Section "Giving up": "After the last attempt the job is marked failed and stays in the table for 14 days. Use the failed hook to be told." followed by the code block:
     `queue.on("failed", (job, error) => report(job.id, error));`
3. Sidebar navigation: section "Guide" with the pages "Getting started", "Defining jobs", "Retries and backoff" (current page, marked), "Scheduling", "Monitoring"; section "Reference" with the pages "Queue options", "Job options", "Command line".
4. On-page headings list, titled "On this page": "Default schedule", "Changing the schedule", "Giving up".
5. Previous and next page links: "Previous: Defining jobs" and "Next: Scheduling".
6. Site header: the mark with the wordmark "Marlow", the links "Guide", "Reference" and "GitHub".

**States**: default; copied (the copy control reads "Copied" for 2 seconds, then "Copy" again); narrow (the sidebar is behind a menu control labelled "Menu").

**Breakpoints**: 1440 px: sidebar, content and on-page headings list side by side. Below 900 px: the sidebar becomes a panel behind the menu control and the on-page headings list is hidden. 390 px: one column, code blocks scroll inside their own box and the page never scrolls sideways.

**Motion**: hover and copy feedback only, 150 ms ease-out; with reduced motion the feedback changes without a transition.

## Constraints

- Colours, typefaces, sizes, radii and spacing only from Visual language.
- Texts verbatim from Content; no other text on the page, no invented navigation items.
- Text on its background passes WCAG AA (at least 4.5:1); the brand colour #C2410C on #FFFFFF is 5.2:1 and may be used for links and the current sidebar item.
- Every interactive element has a visible focus state and is reachable with the keyboard in reading order.
- Code is real text in the code typeface, never an image.
- The layout is a template: it must hold a page with ten sections and a page with one.

## Deliverables

- Round 1: one design per direction (A, B, C) of the example page, 1440 px wide, light mode, default state: three designs.
- Round 2: the chosen direction complete: 1440 px, 900 px and 390 px wide, light and dark mode, with the copied and the narrow states.

## Evaluation criteria

- CRIT-1: Every region of Content is present: site header, sidebar navigation, page header, content with code blocks, on-page headings list, previous and next page links.
- CRIT-2: Every text is verbatim from the brief and no other text appears.
- CRIT-3: Only the colours of Visual language are used, and #C2410C is the only accent.
- CRIT-4: The text is set in Inter and the code in JetBrains Mono, and the body text column is at most 720 px wide.
- CRIT-5: The first code block is visible without scrolling at 1440 × 900 px.
- CRIT-6: The current page "Retries and backoff" is marked in the sidebar and can be told from the other items without relying on colour alone.
- CRIT-7: The direction's own idea is unmistakable at a glance: the hanging section numbers and the oversized title (A), the code panels wider than the text column (B), or the line in the brand colour through the content (C).

## Attachments

- Send: this brief; site/logo.svg
- Do not send in round 1: a screenshot or an export of the current documentation page

## Prompt

```text
This is an exploration, not a production page. Design the documentation page of Marlow, a small
open-source library that runs background jobs for Node.js applications on a PostgreSQL table.
A result that looks like every other documentation template has failed.

Design one page: the guide page "Retries and backoff", 1440 px wide, light mode.

Non-negotiables:
- Regions: a site header (the attached mark, the wordmark "Marlow", the links "Guide", "Reference",
  "GitHub"); a sidebar with the section "Guide" (Getting started, Defining jobs, Retries and backoff
  as the current page, Scheduling, Monitoring) and the section "Reference" (Queue options, Job
  options, Command line); a page header; the content; a list "On this page"; the links
  "Previous: Defining jobs" and "Next: Scheduling".
- Texts verbatim, and no other text:
  Title: "Retries and backoff"
  Description: "How Marlow retries a failed job, and how to change the schedule."
  Section "Default schedule": "A job that throws is retried five times. Marlow waits longer before
  each attempt: 10 seconds, 1 minute, 5 minutes, 30 minutes and 2 hours."
  Section "Changing the schedule": "Pass a retry option when you define the job. The list holds the
  waiting time before each attempt, in seconds."
  Code: queue.define("send-receipt", sendReceipt, { retry: [5, 30, 300] });
  Section "Giving up": "After the last attempt the job is marked failed and stays in the table for
  14 days. Use the failed hook to be told."
  Code: queue.on("failed", (job, error) => report(job.id, error));
  Each code block has a control labelled "Copy".
- Colours: background #FFFFFF, surface #F6F5F2, text #1B1D22, muted text #5E636E, border #DDDAD2,
  brand #C2410C as the only accent, dark code panel #14161A.
- Type: Inter for text (title 44 to 72 px weight 700, section heading 26 px weight 600, body 17 px,
  sidebar 15 px); JetBrains Mono for code (15 px). Body text column at most 720 px wide.
- Radius 8 px on code blocks and controls, borders 1 px, spacing in multiples of 4 px.
- No gradients, no illustrations, no second accent colour, no shadows beyond a 1 px lift on the
  copy control.
- The first code block must be visible without scrolling at 1440 x 900 px.

The page needs one idea a reader remembers after closing the tab. Push the direction below as far
as the non-negotiables allow.

Deliver: the page at 1440 px wide, and a short list of what this design does that a plain
documentation template would not.

Direction:
```

## Open questions

- none

## Readiness

- Ready for design-execute: yes
