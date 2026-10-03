# Architecture: Lexiloom

- Owner: eng-codebase-map
- Status: approved
- Date: 2026-03-28

## Glossary service

- Holds every glossary and its terms. A glossary holds at most 20,000 terms; the service refuses the
  20,001st.
- Every read checks the member's read permission on the glossary it serves, on each request; nothing is
  cached across members.
- Responses that list terms are streamed in pages of 500 terms, so memory does not grow with the size of
  the glossary.
- Reads see a snapshot: a request that started keeps reading the terms as they were when it started.
