import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { ChapterPane } from "@/components/reader/ChapterPane";
import { server } from "@/test/msw/server";
import {
  BSB_TRANSLATION,
  KJV_TRANSLATION,
  makeChapter,
} from "@/test/utils/bible";
import { renderWithProviders } from "@/test/utils/renderWithProviders";
import type { VerseResponse } from "@/types/api";

const TRANSLATIONS = [BSB_TRANSLATION, KJV_TRANSLATION];

function renderPane(overrides: {
  translationCode?: string;
  onClose?: () => void;
  onVerseClick?: (verse: VerseResponse, code: string) => void;
} = {}) {
  const onVerseClick = overrides.onVerseClick ?? vi.fn();
  return renderWithProviders(
    <ChapterPane
      translationCode={overrides.translationCode ?? "BSB"}
      bookName="John"
      chapterNumber={3}
      layout="verse"
      fontSize="M"
      translations={TRANSLATIONS}
      onTranslationChange={vi.fn()}
      onVerseClick={onVerseClick}
      onClose={overrides.onClose}
      label="Primary translation"
    />,
  );
}

describe("ChapterPane", () => {
  it("shows a loading skeleton while the chapter loads", () => {
    server.use(
      http.get(
        "/api/v1/bible/translations/:code/books/:bookName/chapters/:chapterNumber",
        () => new Promise(() => {}),
      ),
    );
    renderPane();
    expect(screen.getByTestId("chapter-skeleton")).toBeInTheDocument();
  });

  it("renders chapter content after load", async () => {
    renderPane();
    expect(
      await screen.findByRole("heading", { name: /^john 3$/i }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("verse-16")).toHaveTextContent(/for god so loved/i);
  });

  it("renders an error state when fetch fails", async () => {
    server.use(
      http.get(
        "/api/v1/bible/translations/:code/books/:bookName/chapters/:chapterNumber",
        () => HttpResponse.json(
          { detail: { code: "NOT_FOUND", message: "Chapter not found." } },
          { status: 404 },
        ),
      ),
    );
    renderPane();
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });

  it("renders a close button when onClose is provided", async () => {
    const onClose = vi.fn();
    renderPane({ onClose });
    await screen.findByTestId("verse-16");
    expect(screen.getByRole("button", { name: /close comparison/i })).toBeInTheDocument();
  });

  it("does not render a close button when onClose is omitted", async () => {
    renderPane();
    await screen.findByTestId("verse-16");
    expect(screen.queryByRole("button", { name: /close comparison/i })).not.toBeInTheDocument();
  });

  it("clicking close calls onClose", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderPane({ onClose });
    await screen.findByTestId("verse-16");
    await user.click(screen.getByRole("button", { name: /close comparison/i }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("verse click passes the pane's translation code", async () => {
    const user = userEvent.setup();
    const onVerseClick = vi.fn();

    server.use(
      http.get(
        "/api/v1/bible/translations/:code/books/:bookName/chapters/:chapterNumber",
        () => HttpResponse.json(
          makeChapter({
            translationCode: "KJV",
            bookName: "John",
            chapterNumber: 3,
            verses: [
              { id: 16, number: 16, text: "For God so loved the world.", is_red_letter: false, footnotes: [] },
            ],
          }),
          { status: 200 },
        ),
      ),
    );

    renderPane({ translationCode: "KJV", onVerseClick });
    await screen.findByTestId("verse-16");
    await user.click(screen.getByTestId("verse-16"));

    await waitFor(() => {
      expect(onVerseClick).toHaveBeenCalledWith(
        expect.objectContaining({ number: 16 }),
        "KJV",
      );
    });
  });
});
