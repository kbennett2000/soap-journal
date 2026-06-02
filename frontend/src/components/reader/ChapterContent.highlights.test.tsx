import { fireEvent, screen, within } from "@testing-library/react";

import { ChapterContent } from "@/components/reader/ChapterContent";
import { makeAnnotation, makeChapter, makeFootnote, makeVerse } from "@/test/utils/bible";
import { renderWithProviders } from "@/test/utils/renderWithProviders";
import type { VerseSelection } from "@/lib/selection";
import type { Annotation, ChapterResponse } from "@/types/api";

function netChapterWithMarker(): ChapterResponse {
  return makeChapter({
    translationCode: "NET",
    bookName: "John",
    chapterNumber: 3,
    verses: [
      makeVerse({
        id: 16,
        number: 16,
        text: "For God so loved the world.",
        footnotes: [
          makeFootnote({ id: 1, note_type: "tn", char_offset: 3, ordinal: 0, text: "tn body" }),
        ],
      }),
    ],
  });
}

function renderContent(
  chapter: ChapterResponse,
  props: Partial<React.ComponentProps<typeof ChapterContent>> = {},
) {
  return renderWithProviders(
    <ChapterContent
      chapter={chapter}
      layout="verse"
      fontSize="M"
      onVerseClick={() => {}}
      {...props}
    />,
    { initialEntries: ["/read/NET/John/3"] },
  );
}

describe("ChapterContent — highlight render", () => {
  it("renders a highlight as colored data-text-segment spans, coexisting with a note marker", () => {
    const annotation = makeAnnotation({
      id: 5,
      translation_code: "NET",
      book: "John",
      chapter: 3,
      verse_start: 16,
      verse_end: 16,
      char_start: 0,
      char_end: 9,
      color: "green",
    });
    const { container } = renderContent(netChapterWithMarker(), {
      annotations: [annotation],
    });

    // The inline note marker is still present.
    expect(screen.getByTestId("note-marker")).toBeInTheDocument();

    // The highlight is split around the marker into two colored runs.
    const spans = container.querySelectorAll<HTMLElement>("[data-highlight-id]");
    expect(spans).toHaveLength(2);
    const combined = Array.from(spans)
      .map((s) => s.textContent)
      .join("");
    expect(combined).toBe("For God s"); // chars 0..9
    for (const span of spans) {
      expect(span.getAttribute("data-highlight-id")).toBe("5");
      expect(span.style.backgroundColor).toBe("var(--hl-green)");
      // Every text run — highlighted or not — is a selection segment.
      expect(span.hasAttribute("data-text-segment")).toBe(true);
    }
  });

  it("does not render a highlight made in a different translation", () => {
    const kjvHighlight = makeAnnotation({ id: 9, translation_code: "KJV" });
    const { container } = renderContent(netChapterWithMarker(), {
      annotations: [kjvHighlight],
    });
    expect(container.querySelectorAll("[data-highlight-id]")).toHaveLength(0);
  });

  it("renders a plain (no-highlight) chapter unchanged", () => {
    const { container } = renderContent(makeChapter({ translationCode: "BSB" }));
    expect(container.querySelectorAll("[data-highlight-id]")).toHaveLength(0);
    expect(screen.getByTestId("verse-16")).toHaveTextContent("For God so loved the world.");
  });
});

describe("ChapterContent — create flow", () => {
  const singleVerseSelection: VerseSelection = {
    verseStart: 16,
    verseEnd: 16,
    charStart: 0,
    charEnd: 7,
    rect: { top: 100, left: 50, width: 40, height: 16 },
  };

  it("opens the popover for a single-verse selection and POSTs the picked color", () => {
    const onCreateHighlight = vi.fn();
    renderContent(netChapterWithMarker(), {
      annotations: [],
      onCreateHighlight,
      resolveSelectionFn: () => singleVerseSelection,
    });

    expect(screen.queryByTestId("highlight-popover")).not.toBeInTheDocument();
    fireEvent.mouseUp(screen.getByTestId("chapter-content"));

    const popover = screen.getByTestId("highlight-popover");
    fireEvent.click(within(popover).getByRole("button", { name: "Highlight Yellow" }));

    expect(onCreateHighlight).toHaveBeenCalledWith({
      translation_code: "NET",
      book: "John",
      chapter: 3,
      verse_start: 16,
      verse_end: 16,
      char_start: 0,
      char_end: 7,
      color: "yellow",
    });
    // Popover dismisses after creating.
    expect(screen.queryByTestId("highlight-popover")).not.toBeInTheDocument();
  });

  it("refuses a cross-verse selection (no popover)", () => {
    const onCreateHighlight = vi.fn();
    renderContent(netChapterWithMarker(), {
      annotations: [],
      onCreateHighlight,
      resolveSelectionFn: () => ({ ...singleVerseSelection, verseEnd: 17 }),
    });

    fireEvent.mouseUp(screen.getByTestId("chapter-content"));
    expect(screen.queryByTestId("highlight-popover")).not.toBeInTheDocument();
    expect(onCreateHighlight).not.toHaveBeenCalled();
  });

  it("refuses a cross-verse selection whose end offset is smaller than its start", () => {
    // Across verses charStart/charEnd index different verses, so charEnd <
    // charStart is a legitimate ordering — it must still be refused, not
    // mistaken for a collapsed click that could open the remove popover.
    const onCreateHighlight = vi.fn();
    const onRemoveHighlight = vi.fn();
    const annotation = makeAnnotation({
      id: 42,
      translation_code: "NET",
      book: "John",
      chapter: 3,
      verse_start: 16,
      verse_end: 16,
      char_start: 0,
      char_end: 5,
    });
    renderContent(netChapterWithMarker(), {
      annotations: [annotation],
      onCreateHighlight,
      onRemoveHighlight,
      resolveSelectionFn: () => ({
        ...singleVerseSelection,
        verseEnd: 17,
        charStart: 8,
        charEnd: 2,
      }),
    });

    fireEvent.mouseUp(screen.getByTestId("chapter-content"));
    expect(screen.queryByTestId("highlight-popover")).not.toBeInTheDocument();
    expect(onCreateHighlight).not.toHaveBeenCalled();
    expect(onRemoveHighlight).not.toHaveBeenCalled();
  });

  it("dismisses the popover on Escape", () => {
    renderContent(netChapterWithMarker(), {
      annotations: [],
      onCreateHighlight: vi.fn(),
      resolveSelectionFn: () => singleVerseSelection,
    });
    fireEvent.mouseUp(screen.getByTestId("chapter-content"));
    expect(screen.getByTestId("highlight-popover")).toBeInTheDocument();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByTestId("highlight-popover")).not.toBeInTheDocument();
  });
});

describe("ChapterContent — remove flow", () => {
  it("clicking an existing highlight opens a Remove action that DELETEs it", () => {
    const annotation: Annotation = makeAnnotation({
      id: 42,
      translation_code: "NET",
      book: "John",
      chapter: 3,
      verse_start: 16,
      verse_end: 16,
      char_start: 0,
      char_end: 5,
    });
    const onRemoveHighlight = vi.fn();
    const { container } = renderContent(netChapterWithMarker(), {
      annotations: [annotation],
      onRemoveHighlight,
      // Collapsed click → no selection.
      resolveSelectionFn: () => null,
    });

    const span = container.querySelector<HTMLElement>('[data-highlight-id="42"]');
    if (!span) throw new Error("expected a rendered highlight span");
    fireEvent.mouseUp(span);

    const popover = screen.getByTestId("highlight-popover");
    fireEvent.click(within(popover).getByRole("button", { name: /remove highlight/i }));

    expect(onRemoveHighlight).toHaveBeenCalledWith(42);
    expect(screen.queryByTestId("highlight-popover")).not.toBeInTheDocument();
  });
});
