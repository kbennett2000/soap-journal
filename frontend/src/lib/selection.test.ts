import { afterEach, describe, expect, it } from "vitest";

import {
  rangeToVerseSelection,
  type RangeLike,
} from "@/lib/selection";

/**
 * Build a verse element whose plain-text coordinate space is exactly
 * "For God " + "so loved" (positions 0..16) — with a verse-number control and
 * an inline note marker that are NOT data-text-segment and so must count as
 * zero-width. Real text nodes are returned so tests can build genuine Ranges.
 */
function buildVerse(verseNumber: number, body = document.body): {
  verseEl: HTMLElement;
  seg1: Text;
  seg2: Text;
  numberText: Text;
  markerText: Text;
} {
  const verseEl = document.createElement("div");
  verseEl.setAttribute("data-verse", String(verseNumber));

  const numberBtn = document.createElement("button");
  numberBtn.textContent = String(verseNumber);
  verseEl.appendChild(numberBtn);

  const s1 = document.createElement("span");
  s1.setAttribute("data-text-segment", "");
  s1.textContent = "For God ";
  verseEl.appendChild(s1);

  const marker = document.createElement("button");
  marker.textContent = "1"; // a note marker — not a text segment
  verseEl.appendChild(marker);

  const s2 = document.createElement("span");
  s2.setAttribute("data-text-segment", "");
  s2.textContent = "so loved";
  verseEl.appendChild(s2);

  body.appendChild(verseEl);
  return {
    verseEl,
    seg1: s1.firstChild as Text,
    seg2: s2.firstChild as Text,
    numberText: numberBtn.firstChild as Text,
    markerText: marker.firstChild as Text,
  };
}

function realRange(
  startNode: Node,
  startOffset: number,
  endNode: Node,
  endOffset: number,
): Range {
  const range = document.createRange();
  range.setStart(startNode, startOffset);
  range.setEnd(endNode, endOffset);
  return range;
}

afterEach(() => {
  document.body.innerHTML = "";
});

describe("rangeToVerseSelection", () => {
  it("maps a single-word selection within one segment", () => {
    const { seg1 } = buildVerse(16);
    const sel = rangeToVerseSelection(realRange(seg1, 0, seg1, 3)); // "For"
    expect(sel).toEqual(
      expect.objectContaining({
        verseStart: 16,
        verseEnd: 16,
        charStart: 0,
        charEnd: 3,
      }),
    );
  });

  it("accumulates across segments, treating an inline marker as zero-width", () => {
    const { seg1, seg2 } = buildVerse(16);
    // "For God " (8) then 2 chars into seg2 → "For God so". Marker contributes 0.
    const sel = rangeToVerseSelection(realRange(seg1, 0, seg2, 2));
    expect(sel?.charStart).toBe(0);
    expect(sel?.charEnd).toBe(10);
  });

  it("handles selections that start/end exactly at segment boundaries", () => {
    const { seg1, seg2 } = buildVerse(16);
    // From end of seg1 (offset 8) to end of seg2 (offset 8) → chars 8..16.
    const sel = rangeToVerseSelection(realRange(seg1, 8, seg2, 8));
    expect(sel?.charStart).toBe(8);
    expect(sel?.charEnd).toBe(16);
  });

  it("normalizes a backward selection (end before start)", () => {
    const { seg1, seg2 } = buildVerse(16);
    // Construct a backward RangeLike: start in seg2@4, end in seg1@0.
    const backward: RangeLike = {
      startContainer: seg2,
      startOffset: 4,
      endContainer: seg1,
      endOffset: 0,
      getBoundingClientRect: () => ({ top: 0, left: 0, width: 0, height: 0 }),
    };
    const sel = rangeToVerseSelection(backward);
    expect(sel?.charStart).toBe(0);
    expect(sel?.charEnd).toBe(12); // 8 + 4
  });

  it("snaps a point inside the verse-number control to the segment boundary", () => {
    const { seg1, numberText } = buildVerse(16);
    // Start inside the number control (zero-width), end 3 into seg1.
    const sel = rangeToVerseSelection(realRange(numberText, 1, seg1, 3));
    expect(sel?.charStart).toBe(0); // number snaps to 0
    expect(sel?.charEnd).toBe(3);
  });

  it("reports a cross-verse selection with distinct start/end verses", () => {
    const { seg1 } = buildVerse(16);
    const second = buildVerse(17);
    const sel = rangeToVerseSelection(realRange(seg1, 0, second.seg1, 3));
    expect(sel?.verseStart).toBe(16);
    expect(sel?.verseEnd).toBe(17);
  });

  it("returns null for a collapsed selection", () => {
    const { seg1 } = buildVerse(16);
    expect(rangeToVerseSelection(realRange(seg1, 2, seg1, 2))).toBeNull();
  });

  it("returns null when the range is not anchored within a verse", () => {
    const orphan = document.createElement("p");
    orphan.textContent = "not a verse";
    document.body.appendChild(orphan);
    const t = orphan.firstChild as Text;
    expect(rangeToVerseSelection(realRange(t, 0, t, 3))).toBeNull();
  });
});

describe("rangeToVerseSelection — multi-verse (5c)", () => {
  function buildChapter(key: string, verseNumbers: number[]) {
    const chapterEl = document.createElement("div");
    chapterEl.setAttribute("data-chapter", key);
    document.body.appendChild(chapterEl);
    const verses = verseNumbers.map((n) => buildVerse(n, chapterEl));
    return { chapterEl, verses };
  }

  it("resolves a selection spanning verses 2→4, with the END offset in verse 4's space", () => {
    const { verses } = buildChapter("NET/John/3", [2, 3, 4]);
    const v2 = verses[0]!;
    const v4 = verses[2]!;
    // Start: 4 chars into v2's "For God " (after "For "). End: 2 chars into v4's
    // second segment ("so"). Each verse's plain space is "For God so loved" (16);
    // the marker between segments is zero-width in BOTH verses.
    const sel = rangeToVerseSelection(realRange(v2.seg1, 4, v4.seg2, 2));
    expect(sel?.verseStart).toBe(2);
    expect(sel?.charStart).toBe(4);
    expect(sel?.verseEnd).toBe(4);
    // 8 ("For God ") + 2 into seg2 = 10, computed in verse 4's element. A bug
    // that measured the end in verse 2's space would NOT find v4.seg2 there and
    // would fall back to v2's total length (16), so this asserts the right space.
    expect(sel?.charEnd).toBe(10);
  });

  it("normalizes a backward multi-verse selection (end verse before start verse)", () => {
    const { verses } = buildChapter("NET/John/3", [2, 3, 4]);
    const v2 = verses[0]!;
    const v4 = verses[2]!;
    // A real Range collapses a backward selection, so build a RangeLike literal:
    // anchored in v4 (start), focus back up into v2 (end), in reverse doc order.
    const backward: RangeLike = {
      startContainer: v4.seg2,
      startOffset: 2,
      endContainer: v2.seg1,
      endOffset: 4,
      getBoundingClientRect: () => ({ top: 0, left: 0, width: 0, height: 0 }),
    };
    const sel = rangeToVerseSelection(backward);
    expect(sel?.verseStart).toBe(2);
    expect(sel?.charStart).toBe(4);
    expect(sel?.verseEnd).toBe(4);
    expect(sel?.charEnd).toBe(10);
  });

  it("refuses a selection that crosses a chapter boundary", () => {
    const a = buildChapter("NET/John/3", [2]);
    const b = buildChapter("NET/John/4", [2]);
    const sel = rangeToVerseSelection(realRange(a.verses[0]!.seg1, 0, b.verses[0]!.seg1, 3));
    expect(sel).toBeNull();
  });
});
