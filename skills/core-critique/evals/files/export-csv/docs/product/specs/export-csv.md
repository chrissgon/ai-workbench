# Feature specification: export-csv

- Owner: product-feature-spec
- Status: approved
- Date: 2026-05-06
- Feature of: Lexiloom PRD, F-7 "Take a glossary out", phase P-2

## Summary

A translator downloads one glossary as a CSV file that opens in a spreadsheet with every term, its
translation and its note intact.

## Goal and users

- Problem: translators must hand a client's glossary to agencies that do not use Lexiloom, and today
  they copy terms out by hand. Source: 9 of 14 support requests in March 2026 (user's count, 2026-04-02)
- Users: freelance translators with at least one glossary (PRD U-1)
- Success: at least 30% of active translators export a glossary within 60 days of release, and support
  requests about copying terms out fall from 9 a month to 2 or fewer. An active translator is a member who
  exported or edited a glossary in the last 30 days. Measured by: the analytics event `glossary_exported`
  (REQ-7) and the support tag `export`. Source: user answer 2026-04-02

## Scope

- In: export of one glossary at a time, from the glossary page, as a CSV file.
- Out: export of several glossaries in one file; TBX, XLSX or any format other than CSV; scheduled
  exports; importing a CSV (that is F-8, its own specification); exporting the change history of a term.

## Sources

- docs/product/prd.md, F-7 and U-1
- User answers, 2026-04-02 (metric, limits, formats left out)
- docs/engineering/architecture.md, "Glossary service" (the 20,000-term limit per glossary)

## Functional requirements

- REQ-1: The glossary page shows an "Export CSV" control to every member who can read the glossary. Source: PRD F-7
- REQ-2: Activating the control downloads a file named `<glossary-slug>-<YYYY-MM-DD>.csv` with one header row and one row per term, in the order the page shows. Source: PRD F-7
- REQ-3: The columns are `term`, `translation`, `part_of_speech`, `note`, `updated_at`, in that order; `updated_at` is ISO 8601 in UTC. Source: user answer 2026-04-02
- REQ-4: The file is UTF-8 with a byte order mark, comma separated, CRLF line endings, and fields quoted per RFC 4180 when they contain a comma, a quote or a line break. Source: user answer 2026-04-02
- REQ-5: A field that starts with `=`, `+`, `-` or `@` is written with a leading apostrophe so a spreadsheet does not run it as a formula. Source: user answer 2026-04-02
- REQ-6: The export contains only the glossary the member opened; the server checks read permission on that glossary for every request. Source: architecture, "Glossary service"
- REQ-7: When the last row of an export has been sent, the server records one `glossary_exported` event with the member and the glossary; a failed or refused export records none. Source: user answer 2026-04-02

## Non-functional requirements

- NFR-1: A glossary of 20,000 terms, the maximum a glossary holds, downloads completely within 5 seconds at the 95th percentile. Source: user answer 2026-04-02
- NFR-2: The export is streamed; server memory used per export stays under 50 MB at 20,000 terms. Source: architecture, "Glossary service"

## Constraints

- technical: no new runtime dependency; the server already streams responses. Source: architecture
- operational: at most 10 exports per member per minute; further requests get an error state. Source: user answer 2026-04-02

## Edge cases

- EDGE-1: The glossary has no terms → the file has the header row only and the download succeeds.
- EDGE-2: The member loses read permission between opening the page and activating the control → no file; the page shows "You no longer have access to this glossary." and a link to the glossary list.
- EDGE-3: The connection drops during the download → the browser reports a failed download; the page shows "Export failed. Try again." with a retry control; no partial file is offered as complete.
- EDGE-4: A term contains a comma, a double quote and a line break → the field is quoted and the quote doubled; the row count in a spreadsheet equals the term count.
- EDGE-5: The member passes 10 exports in one minute → no file; the page shows "Too many exports. Try again in a minute."
- EDGE-6: A term is edited while the export runs → the file holds the state at the moment the export started.
- Categories skipped: localisation of column names (the user decided the names stay in English, 2026-04-02).

## Acceptance criteria

- AC-1:
  Given a member with read permission on a glossary of 3 terms
  When they activate "Export CSV"
  Then a file named `<glossary-slug>-<today>.csv` downloads with 4 rows and the 5 columns in order
  Covers: REQ-1, REQ-2, REQ-3
- AC-2:
  Given a term whose note is `"a, b"` followed by a line break and `c`
  When the glossary is exported and the file is parsed by an RFC 4180 parser
  Then the note field equals the original text and the file starts with the UTF-8 byte order mark
  Covers: REQ-4, EDGE-4
- AC-3:
  Given a term whose translation is `=SUM(A1:A2)`
  When the glossary is exported
  Then the field in the file is `'=SUM(A1:A2)`
  Covers: REQ-5
- AC-4:
  Given a member without read permission on glossary G
  When they request the export address of G directly
  Then the response is 403 and no term of G is in the response body
  Covers: REQ-6
- AC-5:
  Given a glossary of 20,000 terms
  When it is exported 100 times in the load test, by 20 load-test members, at most 10 per member per minute
  Then the 95th percentile of the complete download is 5 seconds or less and peak memory per export is under 50 MB
  Covers: NFR-1, NFR-2
- AC-6:
  Given an empty glossary
  When it is exported
  Then the file has exactly 1 row, the header
  Covers: REQ-2, EDGE-1
- AC-7:
  Given a member whose read permission on glossary G is removed after they opened its page
  When they activate "Export CSV"
  Then no file downloads and the page shows "You no longer have access to this glossary." with a link to the glossary list
  Covers: EDGE-2, REQ-6
- AC-8:
  Given an export of a 20,000-term glossary whose connection is cut after half of the rows
  When the download fails
  Then the page shows "Export failed. Try again." with a retry control, and no `glossary_exported` event is recorded
  Covers: EDGE-3, REQ-7
- AC-9:
  Given a member who has exported 10 times in the last minute
  When they activate "Export CSV" an eleventh time
  Then no file downloads and the page shows "Too many exports. Try again in a minute."
  Covers: EDGE-5
- AC-10:
  Given an export of a 20,000-term glossary that has started
  When another member edits term 15,000 before the export reaches it
  Then the file holds the text of term 15,000 as it was when the export started
  Covers: EDGE-6
- AC-11:
  Given a member who exports a glossary of 3 terms and the download completes
  When the analytics events of that minute are read
  Then exactly one `glossary_exported` event names that member and that glossary
  Covers: REQ-7

## Assumptions

- ASSUMPTION-1: Agencies open the file in a spreadsheet or a translation tool that reads RFC 4180 CSV. Safe because: the 9 support requests of March 2026 all named a spreadsheet as the destination.

## Open questions

- none

## Readiness

- Ready for architecture: yes
