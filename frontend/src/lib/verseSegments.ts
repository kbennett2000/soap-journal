/**
 * Split a verse's plain text into ordered parts — text runs interleaved with
 * inline note markers (at each typed note's `char_offset`) and tagged with any
 * highlights that cover them.
 *
 * Pure and React-free (unit-tested in isolation). A re-implementation of the
 * NET app's verse-part splitting. Both note markers and highlight edges are
 * breakpoints; each emitted text run carries the highlights covering it (a
 * stack, top-most last) so 5c overlap stacking can reuse the shape — 5b renders
 * the single top highlight.
 *
 * Only typed notes participate as markers: a footnote with `char_offset === null`
 * (every plain-translation footnote) is ignored here and rendered separately as
 * an end-of-verse marker. A verse with no typed notes and no highlights returns
 * a single text part, so plain translations render exactly as before.
 */

import type { Annotation, FootnoteResponse } from "@/types/api";

export interface VerseTextPart {
  type: "text";
  text: string;
  /**
   * Highlights covering this run, ordered oldest→newest by annotation `id`
   * (top-most last); empty when unhighlighted. The last element is the
   * most-recently-created highlight, whose color is rendered on top (5c-2).
   */
  highlights: Annotation[];
}

export interface VerseMarkerPart {
  type: "marker";
  note: FootnoteResponse;
  /** 1-based display number for the marker (from the note's 0-based ordinal). */
  number: number;
}

export type VersePart = VerseTextPart | VerseMarkerPart;

/** A highlight's reach within a single verse, in plain-text char coordinates. */
export interface HighlightSpan {
  start: number;
  end: number;
  annotation: Annotation;
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(value, max));
}

export function buildVerseParts(
  text: string,
  footnotes: FootnoteResponse[],
  highlights: HighlightSpan[] = [],
): VersePart[] {
  const typed = footnotes
    .filter((f): f is FootnoteResponse & { char_offset: number } => f.char_offset !== null)
    .map((f) => ({ note: f, offset: clamp(f.char_offset, 0, text.length) }))
    // Stable order: by character position, then by the note's within-verse
    // ordinal so co-located markers render in a deterministic sequence.
    .sort((a, b) => a.offset - b.offset || a.note.ordinal - b.note.ordinal);

  const spans = highlights
    .map((h) => ({
      start: clamp(h.start, 0, text.length),
      end: clamp(h.end, 0, text.length),
      annotation: h.annotation,
    }))
    .filter((h) => h.end > h.start);

  // Fast path: nothing to interleave — one plain text part (unchanged output
  // for plain translations).
  if (typed.length === 0 && spans.length === 0) {
    return [{ type: "text", text, highlights: [] }];
  }

  // Breakpoints: text bounds ∪ marker offsets ∪ highlight edges.
  const breaks = new Set<number>([0, text.length]);
  for (const t of typed) breaks.add(t.offset);
  for (const s of spans) {
    breaks.add(s.start);
    breaks.add(s.end);
  }
  const sorted = [...breaks].sort((a, b) => a - b);

  const parts: VersePart[] = [];
  for (let i = 0; i < sorted.length; i++) {
    const at = sorted[i]!;
    // Markers anchored exactly here, in (offset, ordinal) order.
    for (const t of typed) {
      if (t.offset === at) {
        parts.push({ type: "marker", note: t.note, number: t.note.ordinal + 1 });
      }
    }
    const next = sorted[i + 1];
    if (next === undefined || next === at) continue;
    // Breakpoints include every highlight edge, so a segment [at, next) is
    // either fully inside a highlight or fully outside it — partial overlap is
    // impossible. Hence "contains" (start ≤ at && end ≥ next), not "overlaps".
    // Order the covering stack oldest→newest by id so the newest renders on top
    // deterministically, regardless of input order (5c-2).
    const covering = spans
      .filter((s) => s.start <= at && s.end >= next)
      .sort((a, b) => a.annotation.id - b.annotation.id);
    parts.push({
      type: "text",
      text: text.slice(at, next),
      highlights: covering.map((s) => s.annotation),
    });
  }
  return parts;
}
