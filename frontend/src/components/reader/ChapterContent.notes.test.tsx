import { fireEvent, screen } from "@testing-library/react";
import { useLocation } from "react-router-dom";

import { ChapterContent } from "@/components/reader/ChapterContent";
import { makeChapter, makeFootnote, makeVerse } from "@/test/utils/bible";
import { renderWithProviders } from "@/test/utils/renderWithProviders";
import type { ChapterResponse, VerseResponse } from "@/types/api";

function LocationProbe(): JSX.Element {
  const loc = useLocation();
  return <div data-testid="loc">{`${loc.pathname}${loc.search}`}</div>;
}

function renderChapter(
  chapter: ChapterResponse,
  onVerseClick: (v: VerseResponse) => void = () => {},
) {
  return renderWithProviders(
    <>
      <ChapterContent
        chapter={chapter}
        layout="verse"
        fontSize="M"
        onVerseClick={onVerseClick}
      />
      <LocationProbe />
    </>,
    { initialEntries: ["/read/NET/Genesis/1"] },
  );
}

const NET_VERSE = makeVerse({
  id: 1,
  number: 1,
  text: "In the beginning God created.",
  footnotes: [
    makeFootnote({ id: 1, note_type: "tn", char_offset: 2, ordinal: 0, text: "tn note body" }),
    makeFootnote({
      id: 2,
      note_type: "sn",
      char_offset: 10,
      ordinal: 1,
      text: "sn note body",
      cross_refs: [{ to_book: "John", to_chapter: 1, to_verse_start: 1, to_verse_end: null }],
    }),
  ],
});

function netChapter(): ChapterResponse {
  return makeChapter({
    translationCode: "NET",
    bookName: "Genesis",
    chapterNumber: 1,
    verses: [NET_VERSE],
  });
}

describe("ChapterContent — translator's notes", () => {
  it("renders inline markers in char_offset order", () => {
    renderChapter(netChapter());
    const markers = screen.getAllByTestId("note-marker");
    expect(markers).toHaveLength(2);
    expect(markers.map((m) => m.textContent)).toEqual(["1", "2"]);
  });

  it("shows the note view (type + body) when a marker is clicked", () => {
    renderChapter(netChapter());
    expect(screen.queryByTestId("note-view")).not.toBeInTheDocument();
    fireEvent.click(screen.getAllByTestId("note-marker")[0]!);
    const view = screen.getByTestId("note-view");
    expect(view).toHaveTextContent("Translator's Note");
    expect(view).toHaveTextContent("tn note body");
  });

  it("renders a cross-ref link that navigates into the reader with a range", () => {
    renderChapter(netChapter());
    fireEvent.click(screen.getAllByTestId("note-marker")[1]!); // the sn note
    const view = screen.getByTestId("note-view");
    expect(view).toHaveTextContent("Study Note");
    const link = screen.getByRole("link", { name: "John 1:1" });
    fireEvent.click(link);
    expect(screen.getByTestId("loc")).toHaveTextContent("/read/NET/John/1?range=1-1");
  });

  it("a marker click does NOT trigger the verse's new-entry click", () => {
    const onVerseClick = vi.fn();
    renderChapter(netChapter(), onVerseClick);
    fireEvent.click(screen.getAllByTestId("note-marker")[0]!);
    expect(onVerseClick).not.toHaveBeenCalled();
  });

  it("a click on the verse text DOES trigger the verse click", () => {
    const onVerseClick = vi.fn();
    renderChapter(netChapter(), onVerseClick);
    fireEvent.click(screen.getByTestId("verse-1"));
    expect(onVerseClick).toHaveBeenCalledTimes(1);
  });
});

describe("ChapterContent — plain translations unchanged", () => {
  it("renders no inline note markers for a plain (no typed notes) chapter", () => {
    // makeChapter defaults to BSB verses with no footnotes.
    renderChapter(makeChapter({ translationCode: "BSB" }));
    expect(screen.queryAllByTestId("note-marker")).toHaveLength(0);
    expect(screen.getByTestId("verse-16")).toHaveTextContent("For God so loved the world.");
  });

  it("keeps the end-of-verse FootnoteMarker for a plain footnote (char_offset null)", () => {
    const chapter = makeChapter({
      translationCode: "BSB",
      verses: [
        makeVerse({
          id: 2,
          number: 2,
          text: "And the earth was formless.",
          footnotes: [makeFootnote({ id: 9, text: "Heb. tohu wabohu" })], // plain: char_offset null
        }),
      ],
    });
    renderChapter(chapter);
    expect(screen.queryAllByTestId("note-marker")).toHaveLength(0);
    // The existing plain-footnote toggle (aria-label "Footnote") is present.
    expect(screen.getByRole("button", { name: "Footnote" })).toBeInTheDocument();
  });
});
