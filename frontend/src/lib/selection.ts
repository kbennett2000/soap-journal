/**
 * DOM selection → verse/char-offset mapping for the highlight layer (ADR-0005).
 *
 * The crux: a verse's plain-text coordinate space must match the backend's
 * `char_offset` exactly, so highlights round-trip. We achieve that by counting
 * ONLY the text inside `[data-text-segment]` nodes — the verse-number control
 * and inline note markers are deliberately left outside any segment, so they
 * are zero-width here, just as they don't exist in the canonical verse text.
 *
 * The module is split into a PURE core (`rangeToVerseSelection`, operating on a
 * `Range`-like object — no `window`) and a thin live delegator
 * (`resolveSelection`, the only function touching `window.getSelection()`). The
 * pure core is unit-tested with jsdom-constructed Ranges; the live delegator's
 * real-drag behavior is manual/E2E only. See ADR-0005 Cycle 5b.
 */

const TEXT_SEGMENT_SELECTOR = "[data-text-segment]";
const VERSE_SELECTOR = "[data-verse]";

export interface VerseSelectionRect {
  top: number;
  left: number;
  width: number;
  height: number;
}

export interface VerseSelection {
  verseStart: number;
  verseEnd: number;
  charStart: number;
  charEnd: number;
  /** Bounding rect of the selection, for positioning the popover. */
  rect: VerseSelectionRect;
}

/** The subset of `Range` the pure mapper needs — lets tests pass a literal. */
export interface RangeLike {
  startContainer: Node;
  startOffset: number;
  endContainer: Node;
  endOffset: number;
  getBoundingClientRect(): {
    top: number;
    left: number;
    width: number;
    height: number;
  };
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(value, max));
}

/** Nearest ancestor element carrying `data-verse`, or null. */
export function closestVerse(node: Node | null): HTMLElement | null {
  if (!node) return null;
  const el =
    node.nodeType === Node.ELEMENT_NODE
      ? (node as Element)
      : node.parentElement;
  return (el?.closest(VERSE_SELECTOR) as HTMLElement | null) ?? null;
}

function verseNumberOf(verseEl: HTMLElement): number | null {
  const raw = verseEl.getAttribute("data-verse");
  if (raw === null) return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

/**
 * Char offset of (container, offset) within `verseEl`'s plain-text space —
 * summing only `[data-text-segment]` text. A point inside a non-segment node
 * (marker / verse number) snaps to the segment boundary before it. If the
 * container is never reached, returns the running total (end of verse) as a
 * deterministic best-effort for element-anchored endpoints.
 */
export function offsetWithinVerse(
  verseEl: HTMLElement,
  container: Node,
  offset: number,
): number {
  const doc = verseEl.ownerDocument;
  const walker = doc.createTreeWalker(verseEl, NodeFilter.SHOW_TEXT);
  let total = 0;
  let node = walker.nextNode();
  while (node) {
    const inSegment =
      node.parentElement?.closest(TEXT_SEGMENT_SELECTOR) != null;
    const len = node.textContent?.length ?? 0;
    if (node === container) {
      return inSegment ? total + clamp(offset, 0, len) : total;
    }
    if (inSegment) total += len;
    node = walker.nextNode();
  }
  return total;
}

/**
 * Map a DOM Range to a verse selection in canonical coordinates, normalizing
 * backward selections. Returns null when the range isn't anchored within
 * verses, or when it's collapsed (nothing selected).
 */
export function rangeToVerseSelection(range: RangeLike): VerseSelection | null {
  const startVerseEl = closestVerse(range.startContainer);
  const endVerseEl = closestVerse(range.endContainer);
  if (!startVerseEl || !endVerseEl) return null;

  const startVerse = verseNumberOf(startVerseEl);
  const endVerse = verseNumberOf(endVerseEl);
  if (startVerse === null || endVerse === null) return null;

  let a = {
    verse: startVerse,
    char: offsetWithinVerse(startVerseEl, range.startContainer, range.startOffset),
  };
  let b = {
    verse: endVerse,
    char: offsetWithinVerse(endVerseEl, range.endContainer, range.endOffset),
  };

  // Normalize backward selections to (start ≤ end) in document order.
  if (a.verse > b.verse || (a.verse === b.verse && a.char > b.char)) {
    [a, b] = [b, a];
  }

  // Collapsed (nothing actually selected).
  if (a.verse === b.verse && a.char === b.char) return null;

  const r = range.getBoundingClientRect();
  return {
    verseStart: a.verse,
    verseEnd: b.verse,
    charStart: a.char,
    charEnd: b.char,
    rect: { top: r.top, left: r.left, width: r.width, height: r.height },
  };
}

/**
 * Live reader of the current document selection — the ONLY function here that
 * touches `window.getSelection()`. Thin by design; delegates the math to the
 * pure, tested `rangeToVerseSelection`. Real-drag behavior is manual/E2E only.
 */
export function resolveSelection(): VerseSelection | null {
  const sel = typeof window !== "undefined" ? window.getSelection?.() : null;
  if (!sel || sel.rangeCount === 0 || sel.isCollapsed) return null;
  return rangeToVerseSelection(sel.getRangeAt(0));
}
