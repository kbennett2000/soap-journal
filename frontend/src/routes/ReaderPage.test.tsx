import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router-dom";

import { ReaderPage } from "@/routes/ReaderPage";
import { STORAGE_KEYS } from "@/lib/storage";
import { server } from "@/test/msw/server";
import {
  BSB_TRANSLATION,
  KJV_TRANSLATION,
  makeChapter,
  makeTranslationList,
} from "@/test/utils/bible";
import { renderWithProviders } from "@/test/utils/renderWithProviders";
import { useLocation } from "react-router-dom";

function EntryNewStub(): JSX.Element {
  const loc = useLocation();
  const state = loc.state as
    | { scriptureRef?: string; translationCode?: string }
    | null;
  return (
    <div data-testid="new-entry-state">
      {state?.scriptureRef ?? "(none)"} / {state?.translationCode ?? "(none)"}
    </div>
  );
}

function renderReader(initialEntries: string[]) {
  return renderWithProviders(
    <Routes>
      <Route path="/read" element={<ReaderPage />} />
      <Route
        path="/read/:translationCode/:bookName/:chapterNumber"
        element={<ReaderPage />}
      />
    </Routes>,
    { initialEntries },
  );
}

describe("ReaderPage", () => {
  it("renders the chapter content from the chapter query", async () => {
    renderReader(["/read/BSB/John/3"]);
    expect(
      await screen.findByRole("heading", { name: /^john 3$/i }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("verse-16")).toHaveTextContent(/for god so loved/i);
  });

  it("selecting a different book navigates to that book's chapter 1", async () => {
    const user = userEvent.setup();
    renderReader(["/read/BSB/John/3"]);
    // Wait for the controls + chapter to be rendered.
    await screen.findByTestId("verse-16");

    // Override the chapter handler so the request for Psalms 1 returns
    // a Psalms chapter we can identify.
    server.use(
      http.get(
        "/api/v1/bible/translations/:code/books/:bookName/chapters/:chapterNumber",
        ({ params }) => {
          const bookName = String(params.bookName);
          const chapterNumber = Number(params.chapterNumber);
          if (bookName === "Psalms" && chapterNumber === 1) {
            return HttpResponse.json(
              makeChapter({
                bookName: "Psalms",
                chapterNumber: 1,
                verses: [
                  {
                    id: 1,
                    number: 1,
                    text: "Blessed is the man.",
                    is_red_letter: false,
                    footnotes: [],
                  },
                ],
                previous: { book_name: "Job", chapter_number: 42 },
                next: { book_name: "Psalms", chapter_number: 2 },
              }),
              { status: 200 },
            );
          }
          return HttpResponse.json(
            makeChapter({ bookName, chapterNumber }),
            { status: 200 },
          );
        },
      ),
    );

    await user.selectOptions(screen.getByRole("combobox", { name: /book/i }), "Psalms");

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /^psalms 1$/i })).toBeInTheDocument(),
    );
  });

  it("selecting a different chapter navigates within the current book", async () => {
    const user = userEvent.setup();
    renderReader(["/read/BSB/John/3"]);
    await screen.findByTestId("verse-16");

    server.use(
      http.get(
        "/api/v1/bible/translations/:code/books/:bookName/chapters/:chapterNumber",
        ({ params }) => {
          return HttpResponse.json(
            makeChapter({
              bookName: String(params.bookName),
              chapterNumber: Number(params.chapterNumber),
            }),
            { status: 200 },
          );
        },
      ),
    );

    await user.selectOptions(screen.getByRole("combobox", { name: /chapter/i }), "5");

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /^john 5$/i })).toBeInTheDocument(),
    );
  });

  it("submitting the jump bar with a valid ref navigates to the resolved chapter", async () => {
    const user = userEvent.setup();
    renderReader(["/read/BSB/John/3"]);
    await screen.findByTestId("verse-16");

    server.use(
      http.get("/api/v1/bible/resolve", ({ request }) => {
        const url = new URL(request.url);
        const ref = url.searchParams.get("ref") ?? "";
        return HttpResponse.json(
          {
            reference: {
              canonical_string: ref,
              translation_code: "BSB",
              book: {
                name: "Psalms",
                abbreviation: "Ps",
                order_index: 19,
                testament: "OT",
                chapter_count: 150,
              },
              chapter_number: 23,
              start_verse: 1,
              end_verse: 1,
            },
            verses: [],
          },
          { status: 200 },
        );
      }),
      http.get(
        "/api/v1/bible/translations/:code/books/:bookName/chapters/:chapterNumber",
        ({ params }) =>
          HttpResponse.json(
            makeChapter({
              bookName: String(params.bookName),
              chapterNumber: Number(params.chapterNumber),
            }),
            { status: 200 },
          ),
      ),
    );

    await user.type(screen.getByLabelText(/jump to reference/i), "Psalms 23:1");
    await user.click(screen.getByRole("button", { name: /^go$/i }));

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /^psalms 23$/i })).toBeInTheDocument(),
    );
  });

  it("shows the server's error message inline when the jump bar fails", async () => {
    const user = userEvent.setup();
    renderReader(["/read/BSB/John/3"]);
    await screen.findByTestId("verse-16");

    server.use(
      http.get("/api/v1/bible/resolve", () =>
        HttpResponse.json(
          {
            detail: {
              code: "INVALID_REFERENCE",
              message: "unknown book: 'Frodo'",
            },
          },
          { status: 400 },
        ),
      ),
    );

    await user.type(screen.getByLabelText(/jump to reference/i), "Frodo 3:16");
    await user.click(screen.getByRole("button", { name: /^go$/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("unknown book");
  });

  it("Next button navigates to the next chapter; disables when null", async () => {
    const user = userEvent.setup();
    renderReader(["/read/BSB/John/3"]);
    await screen.findByTestId("verse-16");

    // Override default chapter to have a known next, then for the next
    // chapter return null next.
    server.use(
      http.get(
        "/api/v1/bible/translations/:code/books/:bookName/chapters/:chapterNumber",
        ({ params }) => {
          const num = Number(params.chapterNumber);
          if (num === 4) {
            return HttpResponse.json(
              makeChapter({
                bookName: "John",
                chapterNumber: 4,
                next: null,
              }),
              { status: 200 },
            );
          }
          return HttpResponse.json(
            makeChapter({
              bookName: String(params.bookName),
              chapterNumber: num,
            }),
            { status: 200 },
          );
        },
      ),
    );

    await user.click(screen.getByRole("button", { name: /^next/i }));
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /^john 4$/i })).toBeInTheDocument(),
    );
    // Now the next button should be disabled.
    expect(screen.getByRole("button", { name: /^next/i })).toBeDisabled();
  });

  it("clicking a verse navigates to /entries/new with the reference in state", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <Routes>
        <Route
          path="/read/:translationCode/:bookName/:chapterNumber"
          element={<ReaderPage />}
        />
        <Route path="/entries/new" element={<EntryNewStub />} />
      </Routes>,
      { initialEntries: ["/read/BSB/John/3"] },
    );

    await screen.findByTestId("verse-16");
    // The verse number is the new-entry control; verse text is now selectable.
    await user.click(screen.getByTestId("verse-16-new-entry"));

    expect(await screen.findByTestId("new-entry-state")).toHaveTextContent(
      "John 3:16 / BSB",
    );
  });

  it("font-size change applies a Tailwind class and persists to localStorage", async () => {
    const user = userEvent.setup();
    renderReader(["/read/BSB/John/3"]);
    await screen.findByTestId("verse-16");

    await user.click(screen.getByRole("button", { name: /reader settings/i }));
    await user.click(
      within(screen.getByRole("dialog", { name: /reader settings/i })).getByRole(
        "button",
        { name: "L" },
      ),
    );

    expect(screen.getByTestId("chapter-content").className).toMatch(/text-lg/);
    expect(window.localStorage.getItem(STORAGE_KEYS.readerFontSize)).toBe('"L"');
  });

  it("switching layout to Paragraph renders verses inline as prose", async () => {
    const user = userEvent.setup();
    renderReader(["/read/BSB/John/3"]);
    await screen.findByTestId("verse-16");

    await user.click(screen.getByRole("button", { name: /reader settings/i }));
    await user.click(
      within(screen.getByRole("dialog", { name: /reader settings/i })).getByRole(
        "button",
        { name: "Paragraph" },
      ),
    );

    // In paragraph mode the chapter is wrapped in a <p>; each verse is now an
    // inline, selectable <span data-verse> with the verse-number new-entry
    // control as a button inside it.
    const verse = screen.getByTestId("verse-16");
    expect(verse.tagName).toBe("SPAN");
    expect(verse).toHaveAttribute("data-verse", "16");
    expect(verse.closest("p")).not.toBeNull();
    expect(within(verse).getByTestId("verse-16-new-entry").tagName).toBe("BUTTON");
    expect(window.localStorage.getItem(STORAGE_KEYS.readerLayout)).toBe('"paragraph"');
  });

  it("bare /read with no last-location redirects to Genesis 1", async () => {
    renderReader(["/read"]);
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /^genesis 1$/i })).toBeInTheDocument(),
    );
  });

  it("bare /read with a stored last-location redirects to that location", async () => {
    window.localStorage.setItem(
      STORAGE_KEYS.readerLastLocation,
      JSON.stringify({
        translationCode: "BSB",
        bookName: "Psalms",
        chapterNumber: 23,
      }),
    );
    renderReader(["/read"]);
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /^psalms 23$/i })).toBeInTheDocument(),
    );
  });
});

// ---- compare mode tests ----------------------------------------------------

function useMultiTranslationHandlers(): void {
  server.use(
    http.get("/api/v1/bible/translations", () =>
      HttpResponse.json(
        makeTranslationList([BSB_TRANSLATION, KJV_TRANSLATION]),
        { status: 200 },
      ),
    ),
  );
}

describe("ReaderPage — compare mode", () => {
  it("compare button is disabled when only one translation is loaded", async () => {
    renderReader(["/read/BSB/John/3"]);
    await screen.findByTestId("verse-16");
    expect(screen.getByRole("button", { name: /compare translations/i })).toBeDisabled();
  });

  it("compare button is enabled when two translations are loaded", async () => {
    useMultiTranslationHandlers();
    renderReader(["/read/BSB/John/3"]);
    await screen.findByTestId("verse-16");
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /compare translations/i }),
      ).toBeEnabled(),
    );
  });

  it("clicking compare renders two panes", async () => {
    useMultiTranslationHandlers();
    const user = userEvent.setup();
    renderReader(["/read/BSB/John/3"]);
    await screen.findByTestId("verse-16");

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /compare translations/i }),
      ).toBeEnabled(),
    );
    await user.click(screen.getByRole("button", { name: /compare translations/i }));

    await waitFor(() => {
      expect(screen.getByRole("region", { name: /primary translation/i })).toBeInTheDocument();
      expect(screen.getByRole("region", { name: /comparison translation/i })).toBeInTheDocument();
    });
  });

  it("closing the comparison pane returns to single-pane mode", async () => {
    useMultiTranslationHandlers();
    const user = userEvent.setup();
    renderReader(["/read/BSB/John/3?compare=KJV"]);

    await waitFor(() =>
      expect(screen.getByRole("region", { name: /comparison translation/i })).toBeInTheDocument(),
    );

    await user.click(screen.getByRole("button", { name: /close comparison/i }));

    await waitFor(() =>
      expect(screen.queryByRole("region", { name: /comparison translation/i })).not.toBeInTheDocument(),
    );
  });

  it("translation picker renders a select when two translations are loaded", async () => {
    useMultiTranslationHandlers();
    renderReader(["/read/BSB/John/3"]);
    await screen.findByTestId("verse-16");
    await waitFor(() =>
      expect(screen.getByRole("combobox", { name: /translation/i })).toBeInTheDocument(),
    );
  });

  it("compare button is hidden when already comparing", async () => {
    useMultiTranslationHandlers();
    renderReader(["/read/BSB/John/3?compare=KJV"]);
    await waitFor(() =>
      expect(screen.getByRole("region", { name: /comparison translation/i })).toBeInTheDocument(),
    );
    expect(screen.queryByRole("button", { name: /compare translations/i })).not.toBeInTheDocument();
  });

  it("verse click in pane B passes pane B's translation code", async () => {
    useMultiTranslationHandlers();
    const user = userEvent.setup();
    renderWithProviders(
      <Routes>
        <Route path="/read" element={<ReaderPage />} />
        <Route
          path="/read/:translationCode/:bookName/:chapterNumber"
          element={<ReaderPage />}
        />
        <Route path="/entries/new" element={<EntryNewStub />} />
      </Routes>,
      { initialEntries: ["/read/BSB/John/3?compare=KJV"] },
    );

    const comparisonPane = await screen.findByRole("region", { name: /comparison translation/i });
    const verse16NewEntry = await within(comparisonPane).findByTestId(
      "verse-16-new-entry",
    );
    await user.click(verse16NewEntry);

    expect(await screen.findByTestId("new-entry-state")).toHaveTextContent(
      "John 3:16 / KJV",
    );
  });

  it("next/prev navigation preserves compare mode", async () => {
    useMultiTranslationHandlers();
    const user = userEvent.setup();
    renderReader(["/read/BSB/John/3?compare=KJV"]);

    // Wait for chapter content to load so the nav buttons appear
    const primaryPane = await screen.findByRole("region", { name: /primary translation/i });
    await within(primaryPane).findByTestId("verse-16");

    await user.click(screen.getByRole("button", { name: /^next/i }));

    await waitFor(() => {
      const primaryPane = screen.getByRole("region", { name: /primary translation/i });
      expect(within(primaryPane).getByRole("heading", { name: /^john 4$/i })).toBeInTheDocument();
    });
    expect(screen.getByRole("region", { name: /comparison translation/i })).toBeInTheDocument();
  });
});
