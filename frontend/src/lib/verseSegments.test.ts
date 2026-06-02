import { buildVerseSegments } from "@/lib/verseSegments";
import { makeFootnote } from "@/test/utils/bible";

const TEXT = "In the beginning God created.";

describe("buildVerseSegments", () => {
  it("returns a single text part when there are no typed notes", () => {
    const parts = buildVerseSegments(TEXT, []);
    expect(parts).toEqual([{ type: "text", text: TEXT }]);
  });

  it("ignores plain footnotes (char_offset null) — single text part", () => {
    const parts = buildVerseSegments(TEXT, [makeFootnote({ id: 1 })]);
    expect(parts).toEqual([{ type: "text", text: TEXT }]);
  });

  it("splits text around a mid-verse marker", () => {
    const note = makeFootnote({ id: 1, note_type: "tn", char_offset: 6, ordinal: 0 });
    const parts = buildVerseSegments(TEXT, [note]);
    expect(parts).toEqual([
      { type: "text", text: "In the" },
      { type: "marker", note, number: 1 },
      { type: "text", text: " beginning God created." },
    ]);
  });

  it("places a marker at offset 0 with no leading blank text part", () => {
    const note = makeFootnote({ id: 1, note_type: "tn", char_offset: 0, ordinal: 0 });
    const parts = buildVerseSegments(TEXT, [note]);
    expect(parts).toEqual([
      { type: "marker", note, number: 1 },
      { type: "text", text: TEXT },
    ]);
  });

  it("places a marker at end-of-text with no trailing blank text part", () => {
    const note = makeFootnote({ id: 1, note_type: "tn", char_offset: TEXT.length, ordinal: 0 });
    const parts = buildVerseSegments(TEXT, [note]);
    expect(parts).toEqual([
      { type: "text", text: TEXT },
      { type: "marker", note, number: 1 },
    ]);
  });

  it("clamps an out-of-range char_offset to text length", () => {
    const note = makeFootnote({ id: 1, note_type: "tn", char_offset: 9999, ordinal: 0 });
    const parts = buildVerseSegments(TEXT, [note]);
    expect(parts).toEqual([
      { type: "text", text: TEXT },
      { type: "marker", note, number: 1 },
    ]);
  });

  it("orders co-located notes by ordinal with no blank text between", () => {
    const a = makeFootnote({ id: 1, note_type: "sn", char_offset: 6, ordinal: 1 });
    const b = makeFootnote({ id: 2, note_type: "tn", char_offset: 6, ordinal: 0 });
    const parts = buildVerseSegments(TEXT, [a, b]);
    expect(parts).toEqual([
      { type: "text", text: "In the" },
      { type: "marker", note: b, number: 1 }, // ordinal 0 first
      { type: "marker", note: a, number: 2 },
      { type: "text", text: " beginning God created." },
    ]);
  });

  it("interleaves multiple markers at distinct offsets in reading order", () => {
    const a = makeFootnote({ id: 1, note_type: "tn", char_offset: 2, ordinal: 0 });
    const b = makeFootnote({ id: 2, note_type: "sn", char_offset: 10, ordinal: 1 });
    const parts = buildVerseSegments(TEXT, [b, a]); // unsorted input
    expect(parts.map((p) => (p.type === "marker" ? `m${p.number}` : p.text))).toEqual([
      "In",
      "m1",
      " the beg",
      "m2",
      "inning God created.",
    ]);
  });
});
