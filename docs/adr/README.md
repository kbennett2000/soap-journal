# Architecture Decision Records

Design history for soap-journal. Each ADR captures the context, the decision, and
the consequences for one significant change; cycle addendums at the bottom of an
ADR record what actually shipped per implementation cycle.

The **NET-reader + annotations arc (ADR-0001 → ADR-0005) is complete** — NET is
ingested with typed translator's notes and cross-references, the read API and a
notes/verse full-text search expose them, and the full highlight/annotation layer
(create, multi-verse, overlap, edit, delete, responsive desktop panel / mobile
sheet, touch selection) is shipped.

| ADR | Title | Status |
| --- | --- | --- |
| [0001](0001-unified-bible-notes-data-model.md) | Unify the Bible/notes data model to carry typed, char-anchored notes + cross-references | Accepted — shipped |
| [0002](0002-surface-notes-and-cross-references-in-read-api.md) | Surface translator's notes and cross-references in the read API | Accepted — shipped |
| [0003](0003-full-text-search.md) | Full-text search over verses and translator's notes (single + grouped `ALL`) | Accepted — shipped |
| [0004](0004-frontend-net-reading-experience.md) | Frontend: NET reading experience — inline notes, cross-refs, scripture search UI | Accepted — shipped |
| [0005](0005-annotation-highlight-layer.md) | Annotation / highlight layer (5a backend → 5b–5c-6 frontend) | Accepted — **complete** |

Deliberately out of scope (recorded in ADR-0005 and `SPEC.md` §8): compare-pane
highlights, Markdown notes, a drag-to-resize mobile sheet, and an overlap
stack-cycler.
