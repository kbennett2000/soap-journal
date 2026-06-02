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

// Three NET verses; verse 17 carries an inline note marker so multi-verse
// coverage can be checked to coexist with a marker in a middle verse.
const VERSE_16 = "For God so loved the world."; // slice(8) = "so loved the world."
const VERSE_17 = "that he gave his only Son,";
const VERSE_18 = "whoever believes in him."; // slice(0,8) = "whoever "

function netMultiVerseChapter(): ChapterResponse {
  return makeChapter({
    translationCode: "NET",
    bookName: "John",
    chapterNumber: 3,
    verses: [
      makeVerse({ id: 16, number: 16, text: VERSE_16 }),
      makeVerse({
        id: 17,
        number: 17,
        text: VERSE_17,
        footnotes: [
          makeFootnote({ id: 9, note_type: "tn", char_offset: 5, ordinal: 0, text: "tn body" }),
        ],
      }),
      makeVerse({ id: 18, number: 18, text: VERSE_18 }),
    ],
  });
}

/** Concatenated text of every highlighted run within a verse element. The
 * `[data-text-segment]` filter excludes the `+N` stack badge (which also carries
 * data-highlight-id but is not part of the verse text). */
function highlightedTextOf(verseEl: HTMLElement): string {
  return Array.from(verseEl.querySelectorAll("[data-text-segment][data-highlight-id]"))
    .map((s) => s.textContent)
    .join("");
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

  it("paints a multi-verse highlight as tail / full middle / head across the right verses", () => {
    const annotation = makeAnnotation({
      id: 7,
      translation_code: "NET",
      book: "John",
      chapter: 3,
      verse_start: 16,
      char_start: 8, // verse 16: from "so loved the world."
      verse_end: 18,
      char_end: 8, // verse 18: through "whoever "
      color: "green",
    });
    renderContent(netMultiVerseChapter(), { annotations: [annotation] });

    // verse_start: partial TAIL (char_start..end).
    expect(highlightedTextOf(screen.getByTestId("verse-16"))).toBe("so loved the world.");
    // middle verse: FULL coverage (marker excluded from text, both runs highlighted).
    expect(highlightedTextOf(screen.getByTestId("verse-17"))).toBe(VERSE_17);
    expect(within(screen.getByTestId("verse-17")).getByTestId("note-marker")).toBeInTheDocument();
    // verse_end: partial HEAD (0..char_end).
    expect(highlightedTextOf(screen.getByTestId("verse-18"))).toBe("whoever ");

    // Every covered run resolves back to the one annotation.
    for (const verse of ["verse-16", "verse-17", "verse-18"]) {
      for (const span of screen.getByTestId(verse).querySelectorAll("[data-highlight-id]")) {
        expect(span.getAttribute("data-highlight-id")).toBe("7");
      }
    }
  });

  it("hides a multi-verse highlight made in a different translation", () => {
    const kjv = makeAnnotation({
      id: 8,
      translation_code: "KJV",
      verse_start: 16,
      verse_end: 18,
      char_start: 0,
      char_end: 4,
    });
    const { container } = renderContent(netMultiVerseChapter(), { annotations: [kjv] });
    expect(container.querySelectorAll("[data-highlight-id]")).toHaveLength(0);
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

  it("opens the popover for a MULTI-verse selection and POSTs all four coordinates", () => {
    const onCreateHighlight = vi.fn();
    renderContent(netMultiVerseChapter(), {
      annotations: [],
      onCreateHighlight,
      resolveSelectionFn: () => ({
        verseStart: 16,
        verseEnd: 18,
        charStart: 8,
        charEnd: 8,
        rect: { top: 100, left: 50, width: 40, height: 16 },
      }),
    });

    fireEvent.mouseUp(screen.getByTestId("chapter-content"));
    fireEvent.click(
      within(screen.getByTestId("highlight-popover")).getByRole("button", {
        name: "Highlight Blue",
      }),
    );

    expect(onCreateHighlight).toHaveBeenCalledWith({
      translation_code: "NET",
      book: "John",
      chapter: 3,
      verse_start: 16,
      verse_end: 18,
      char_start: 8,
      char_end: 8,
      color: "blue",
    });
  });

  it("creates a multi-verse highlight whose end offset is smaller than its start", () => {
    // Across verses charStart/charEnd index DIFFERENT verses, so charEnd <
    // charStart is a legitimate ordering — it must create, not be mistaken for a
    // collapsed click (the bug class 5b's review caught, now exercised multi-verse).
    const onCreateHighlight = vi.fn();
    renderContent(netMultiVerseChapter(), {
      annotations: [],
      onCreateHighlight,
      resolveSelectionFn: () => ({
        verseStart: 16,
        verseEnd: 17,
        charStart: 20,
        charEnd: 4,
        rect: { top: 100, left: 50, width: 40, height: 16 },
      }),
    });

    fireEvent.mouseUp(screen.getByTestId("chapter-content"));
    fireEvent.click(
      within(screen.getByTestId("highlight-popover")).getByRole("button", {
        name: "Highlight Yellow",
      }),
    );

    expect(onCreateHighlight).toHaveBeenCalledWith(
      expect.objectContaining({ verse_start: 16, verse_end: 17, char_start: 20, char_end: 4 }),
    );
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

  it("removes a whole multi-verse highlight when any covered span is clicked", () => {
    const annotation: Annotation = makeAnnotation({
      id: 71,
      translation_code: "NET",
      book: "John",
      chapter: 3,
      verse_start: 16,
      char_start: 8,
      verse_end: 18,
      char_end: 8,
    });
    const onRemoveHighlight = vi.fn();
    renderContent(netMultiVerseChapter(), {
      annotations: [annotation],
      onRemoveHighlight,
      resolveSelectionFn: () => null,
    });

    // Click a covered span in the MIDDLE verse — still removes the whole row.
    const span = screen
      .getByTestId("verse-17")
      .querySelector<HTMLElement>('[data-highlight-id="71"]');
    if (!span) throw new Error("expected a covered span in verse 17");
    fireEvent.mouseUp(span);

    fireEvent.click(
      within(screen.getByTestId("highlight-popover")).getByRole("button", {
        name: /remove highlight/i,
      }),
    );

    expect(onRemoveHighlight).toHaveBeenCalledTimes(1);
    expect(onRemoveHighlight).toHaveBeenCalledWith(71);
  });
});

describe("ChapterContent — overlap +N (5c-2)", () => {
  // Two NET highlights overlapping in John 3:16 (which also has a marker at
  // char 3): id 1 yellow [0,12], id 2 green [6,20]. Union = "For God so loved the".
  function overlapAnnotations(): Annotation[] {
    return [
      makeAnnotation({ id: 1, char_start: 0, char_end: 12, color: "yellow" }),
      makeAnnotation({ id: 2, char_start: 6, char_end: 20, color: "green" }),
    ];
  }

  it("shows the newest color on the overlapped run with a +N badge, coexisting with a marker", () => {
    const { container } = renderContent(netChapterWithMarker(), {
      annotations: overlapAnnotations(),
    });
    const verse16 = screen.getByTestId("verse-16");

    // Union of both highlights, marker excluded from the highlighted text.
    expect(highlightedTextOf(verse16)).toBe("For God so loved the");
    expect(within(verse16).getByTestId("note-marker")).toBeInTheDocument();

    // Exactly one overlapped run → one badge; N counts highlights beyond the top.
    const badges = container.querySelectorAll('[data-testid="highlight-stack-badge"]');
    expect(badges).toHaveLength(1);
    expect(badges[0]).toHaveTextContent("+1");
    expect(badges[0]?.getAttribute("data-highlight-id")).toBe("2"); // newest on top

    // Newest (highest id) color shows on the overlapped run; the A-only run is yellow.
    const greenRun = verse16.querySelector<HTMLElement>(
      '[data-text-segment][data-highlight-id="2"]',
    );
    expect(greenRun?.style.backgroundColor).toBe("var(--hl-green)");
    const yellowRun = verse16.querySelector<HTMLElement>(
      '[data-text-segment][data-highlight-id="1"]',
    );
    expect(yellowRun?.style.backgroundColor).toBe("var(--hl-yellow)");
  });

  it("shows no badge where only one highlight covers the run", () => {
    const { container } = renderContent(netChapterWithMarker(), {
      annotations: [makeAnnotation({ id: 1, char_start: 0, char_end: 5 })],
    });
    expect(
      container.querySelectorAll('[data-testid="highlight-stack-badge"]'),
    ).toHaveLength(0);
  });

  it("resolves a stacked run to the top annotation; a single-coverage run removes its own", () => {
    const onRemoveHighlight = vi.fn();
    const { container } = renderContent(netChapterWithMarker(), {
      annotations: overlapAnnotations(),
      onRemoveHighlight,
      resolveSelectionFn: () => null,
    });

    // Click the +N badge (a stacked run) → Remove takes the newest (id 2).
    const badge = container.querySelector<HTMLElement>('[data-testid="highlight-stack-badge"]');
    if (!badge) throw new Error("expected a stack badge");
    fireEvent.mouseUp(badge);
    fireEvent.click(
      within(screen.getByTestId("highlight-popover")).getByRole("button", {
        name: /remove highlight/i,
      }),
    );
    expect(onRemoveHighlight).toHaveBeenLastCalledWith(2);

    // Click a single-coverage (yellow, id 1) run → Remove takes id 1.
    const yellowRun = screen
      .getByTestId("verse-16")
      .querySelector<HTMLElement>('[data-text-segment][data-highlight-id="1"]');
    if (!yellowRun) throw new Error("expected a single-coverage run");
    fireEvent.mouseUp(yellowRun);
    fireEvent.click(
      within(screen.getByTestId("highlight-popover")).getByRole("button", {
        name: /remove highlight/i,
      }),
    );
    expect(onRemoveHighlight).toHaveBeenLastCalledWith(1);
  });

  it("hides overlapping highlights made in a different translation", () => {
    const { container } = renderContent(netChapterWithMarker(), {
      annotations: overlapAnnotations().map((a) => ({ ...a, translation_code: "KJV" })),
    });
    expect(container.querySelectorAll("[data-highlight-id]")).toHaveLength(0);
  });
});
