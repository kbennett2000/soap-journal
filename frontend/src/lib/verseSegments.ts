/**
 * Split a verse's plain text into ordered parts — text runs interleaved with
 * inline note markers at each typed note's `char_offset`.
 *
 * Pure and React-free (unit-tested in isolation). A marker-only
 * re-implementation of the NET app's verse-part splitting; highlight spans are
 * deliberately out of scope here (ADR-0005).
 *
 * Only typed notes participate: a footnote with `char_offset === null` (every
 * plain-translation footnote) is ignored here and rendered separately as an
 * end-of-verse marker. A verse with no typed notes returns a single text part,
 * so plain translations render exactly as before.
 */

import type { FootnoteResponse } from "@/types/api";

export interface VerseTextPart {
  type: "text";
  text: string;
}

export interface VerseMarkerPart {
  type: "marker";
  note: FootnoteResponse;
  /** 1-based display number for the marker (from the note's 0-based ordinal). */
  number: number;
}

export type VersePart = VerseTextPart | VerseMarkerPart;

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(value, max));
}

export function buildVerseSegments(
  text: string,
  footnotes: FootnoteResponse[],
): VersePart[] {
  const typed = footnotes
    .filter((f): f is FootnoteResponse & { char_offset: number } => f.char_offset !== null)
    .map((f) => ({ note: f, offset: clamp(f.char_offset, 0, text.length) }))
    // Stable order: by character position, then by the note's within-verse
    // ordinal so co-located markers render in a deterministic sequence.
    .sort((a, b) => a.offset - b.offset || a.note.ordinal - b.note.ordinal);

  if (typed.length === 0) {
    return [{ type: "text", text }];
  }

  const parts: VersePart[] = [];
  let cursor = 0;
  for (const { note, offset } of typed) {
    if (offset > cursor) {
      parts.push({ type: "text", text: text.slice(cursor, offset) });
      cursor = offset;
    }
    parts.push({ type: "marker", note, number: note.ordinal + 1 });
  }
  if (cursor < text.length) {
    parts.push({ type: "text", text: text.slice(cursor) });
  }
  return parts;
}
