import { buildVerseParts, type HighlightSpan } from "@/lib/verseSegments";
import { makeAnnotation, makeFootnote } from "@/test/utils/bible";

const TEXT = "In the beginning God created.";

describe("buildVerseParts — markers", () => {
  it("returns a single text part when there are no typed notes or highlights", () => {
    const parts = buildVerseParts(TEXT, []);
    expect(parts).toEqual([{ type: "text", text: TEXT, highlights: [] }]);
  });

  it("ignores plain footnotes (char_offset null) — single text part", () => {
    const parts = buildVerseParts(TEXT, [makeFootnote({ id: 1 })]);
    expect(parts).toEqual([{ type: "text", text: TEXT, highlights: [] }]);
  });

  it("splits text around a mid-verse marker", () => {
    const note = makeFootnote({ id: 1, note_type: "tn", char_offset: 6, ordinal: 0 });
    const parts = buildVerseParts(TEXT, [note]);
    expect(parts).toEqual([
      { type: "text", text: "In the", highlights: [] },
      { type: "marker", note, number: 1 },
      { type: "text", text: " beginning God created.", highlights: [] },
    ]);
  });

  it("places a marker at offset 0 with no leading blank text part", () => {
    const note = makeFootnote({ id: 1, note_type: "tn", char_offset: 0, ordinal: 0 });
    const parts = buildVerseParts(TEXT, [note]);
    expect(parts).toEqual([
      { type: "marker", note, number: 1 },
      { type: "text", text: TEXT, highlights: [] },
    ]);
  });

  it("places a marker at end-of-text with no trailing blank text part", () => {
    const note = makeFootnote({ id: 1, note_type: "tn", char_offset: TEXT.length, ordinal: 0 });
    const parts = buildVerseParts(TEXT, [note]);
    expect(parts).toEqual([
      { type: "text", text: TEXT, highlights: [] },
      { type: "marker", note, number: 1 },
    ]);
  });

  it("clamps an out-of-range char_offset to text length", () => {
    const note = makeFootnote({ id: 1, note_type: "tn", char_offset: 9999, ordinal: 0 });
    const parts = buildVerseParts(TEXT, [note]);
    expect(parts).toEqual([
      { type: "text", text: TEXT, highlights: [] },
      { type: "marker", note, number: 1 },
    ]);
  });

  it("orders co-located notes by ordinal with no blank text between", () => {
    const a = makeFootnote({ id: 1, note_type: "sn", char_offset: 6, ordinal: 1 });
    const b = makeFootnote({ id: 2, note_type: "tn", char_offset: 6, ordinal: 0 });
    const parts = buildVerseParts(TEXT, [a, b]);
    expect(parts).toEqual([
      { type: "text", text: "In the", highlights: [] },
      { type: "marker", note: b, number: 1 }, // ordinal 0 first
      { type: "marker", note: a, number: 2 },
      { type: "text", text: " beginning God created.", highlights: [] },
    ]);
  });

  it("interleaves multiple markers at distinct offsets in reading order", () => {
    const a = makeFootnote({ id: 1, note_type: "tn", char_offset: 2, ordinal: 0 });
    const b = makeFootnote({ id: 2, note_type: "sn", char_offset: 10, ordinal: 1 });
    const parts = buildVerseParts(TEXT, [b, a]); // unsorted input
    expect(parts.map((p) => (p.type === "marker" ? `m${p.number}` : p.text))).toEqual([
      "In",
      "m1",
      " the beg",
      "m2",
      "inning God created.",
    ]);
  });
});

describe("buildVerseParts — highlights", () => {
  it("splits text at a highlight's edges and tags the covered run", () => {
    const annotation = makeAnnotation({ id: 5, color: "green" });
    const span: HighlightSpan = { start: 0, end: 6, annotation };
    const parts = buildVerseParts(TEXT, [], [span]);
    expect(parts).toEqual([
      { type: "text", text: "In the", highlights: [annotation] },
      { type: "text", text: " beginning God created.", highlights: [] },
    ]);
  });

  it("clamps a highlight that runs past the verse end", () => {
    const annotation = makeAnnotation({ id: 5 });
    const parts = buildVerseParts(TEXT, [], [{ start: 18, end: 9999, annotation }]);
    expect(parts).toEqual([
      { type: "text", text: "In the beginning G", highlights: [] },
      { type: "text", text: "od created.", highlights: [annotation] },
    ]);
  });

  it("drops a zero-width (or inverted) highlight", () => {
    const annotation = makeAnnotation({ id: 5 });
    const parts = buildVerseParts(TEXT, [], [{ start: 6, end: 6, annotation }]);
    expect(parts).toEqual([{ type: "text", text: TEXT, highlights: [] }]);
  });

  it("coexists with an inline marker inside the highlighted span", () => {
    const note = makeFootnote({ id: 1, note_type: "tn", char_offset: 3, ordinal: 0 });
    const annotation = makeAnnotation({ id: 5, color: "blue" });
    const parts = buildVerseParts(TEXT, [note], [{ start: 0, end: 10, annotation }]);
    // The marker sits between two highlighted runs; both runs carry the highlight.
    expect(parts).toEqual([
      { type: "text", text: "In ", highlights: [annotation] },
      { type: "marker", note, number: 1 },
      { type: "text", text: "the beg", highlights: [annotation] },
      { type: "text", text: "inning God created.", highlights: [] },
    ]);
  });
});
