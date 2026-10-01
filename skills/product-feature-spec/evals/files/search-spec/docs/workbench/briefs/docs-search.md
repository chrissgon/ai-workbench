# Brief: docs search

- Date: 2026-09-20
- Topic: docs-search
- Status: approved by the user

## Problem

Readers of the Tessera UI docs cannot find a component page without knowing which section it is in.

## Decisions

1. A search box in the header searches the titles, headings and body text of the pages of the selected version only.
2. Results show the page title, its section and a text excerpt: at most 8 results, ordered by relevance. Choosing a result opens the page.
3. The index is a static file built at deploy time and searched in the browser. There is no search server.
4. Search runs from 2 characters. An empty or one-character query shows no results and the hint "Type at least 2 characters".
5. Results can be filtered by section (Components, Guides, API).

## Not decided

- How quickly results must appear after the reader types.
- The largest number of pages the index must handle.
