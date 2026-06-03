import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router-dom";

import { ReaderPage } from "@/routes/ReaderPage";
import { server } from "@/test/msw/server";
import {
  makeAnnotation,
  makeChapter,
  makeFootnote,
  makeVerse,
} from "@/test/utils/bible";
import { renderWithProviders } from "@/test/utils/renderWithProviders";

/**
 * 5c-4 step 3: translator notes converge into the responsive shell on the
 * primary pane. NoteView stays read-only (label + body + cross-ref links) — a
 * different surface from the editable AnnotationPanel; only one shows at a time.
 */

function netChapterWithNote() {
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
          makeFootnote({
            id: 1,
            note_type: "tn",
            char_offset: 3,
            ordinal: 0,
            text: "tn note body",
            cross_refs: [
              { to_book: "John", to_chapter: 1, to_verse_start: 1, to_verse_end: null },
            ],
          }),
        ],
      }),
    ],
  });
}

function useNetChapter() {
  server.use(
    http.get(
      "/api/v1/bible/translations/:code/books/:bookName/chapters/:chapterNumber",
      () => HttpResponse.json(netChapterWithNote(), { status: 200 }),
    ),
  );
}

function renderReader() {
  return renderWithProviders(
    <Routes>
      <Route
        path="/read/:translationCode/:bookName/:chapterNumber"
        element={<ReaderPage />}
      />
    </Routes>,
    { initialEntries: ["/read/NET/John/3"] },
  );
}

describe("ReaderPage — translator notes in the shell (5c-4)", () => {
  it("clicking a note marker shows the read-only NoteView in the shell with a working cross-ref link", async () => {
    useNetChapter();
    renderReader();
    await screen.findByTestId("verse-16");

    fireEvent.click(screen.getByTestId("note-marker"));

    const shell = await screen.findByTestId("reader-panel-shell");
    const view = within(shell).getByTestId("note-view");
    expect(view).toHaveTextContent("Translator's Note");
    expect(view).toHaveTextContent("tn note body");
    // Cross-ref still navigates into the reader with a range (ADR-0004 behavior).
    expect(within(view).getByRole("link", { name: "John 1:1" })).toHaveAttribute(
      "href",
      "/read/NET/John/1?range=1-1",
    );
  });

  it("swaps the shell to one surface at a time (highlight ↔ note)", async () => {
    useNetChapter();
    server.use(
      http.get("/api/v1/annotations", () =>
        HttpResponse.json(
          {
            annotations: [
              makeAnnotation({
                id: 9,
                translation_code: "NET",
                book: "John",
                chapter: 3,
                verse_start: 16,
                verse_end: 16,
                char_start: 0,
                char_end: 7,
                color: "yellow",
              }),
            ],
          },
          { status: 200 },
        ),
      ),
    );
    renderReader();
    await screen.findByTestId("verse-16");

    // Open the highlight → annotation panel; no note view.
    const span = await waitFor(() => {
      const el = document.querySelector<HTMLElement>(
        '[data-text-segment][data-highlight-id="9"]',
      );
      if (!el) throw new Error("highlight not rendered yet");
      return el;
    });
    fireEvent.mouseUp(span);
    expect(await screen.findByTestId("annotation-panel")).toBeInTheDocument();
    expect(screen.queryByTestId("note-view")).not.toBeInTheDocument();

    // Open the note → shell swaps to the read-only NoteView; panel gone.
    fireEvent.click(screen.getByTestId("note-marker"));
    expect(await screen.findByTestId("note-view")).toBeInTheDocument();
    expect(screen.queryByTestId("annotation-panel")).not.toBeInTheDocument();
  });

  it("closes an open note when navigating to another chapter", async () => {
    useNetChapter();
    renderReader();
    await screen.findByTestId("verse-16");

    fireEvent.click(screen.getByTestId("note-marker"));
    expect(await screen.findByTestId("note-view")).toBeInTheDocument();

    // Next chapter → the render-phase chapter-change reset closes the panel.
    fireEvent.click(screen.getByRole("button", { name: /^next/i }));
    await waitFor(() =>
      expect(screen.queryByTestId("note-view")).not.toBeInTheDocument(),
    );
  });
});
