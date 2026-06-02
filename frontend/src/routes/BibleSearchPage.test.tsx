import { fireEvent, screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { useLocation } from "react-router-dom";

import { BibleSearchPage } from "@/routes/BibleSearchPage";
import { server } from "@/test/msw/server";
import { makeSearchResponse } from "@/test/utils/bible";
import { renderWithProviders } from "@/test/utils/renderWithProviders";

function LocationProbe(): JSX.Element {
  const loc = useLocation();
  return <div data-testid="loc">{`${loc.pathname}${loc.search}`}</div>;
}

function renderSearch(entry = "/read/search?translation=BSB") {
  return renderWithProviders(
    <>
      <BibleSearchPage />
      <LocationProbe />
    </>,
    { initialEntries: [entry] },
  );
}

function typeQuery(value: string): void {
  fireEvent.change(screen.getByLabelText("Search scripture and notes"), {
    target: { value },
  });
}

describe("BibleSearchPage", () => {
  it("renders verse hits with highlighted snippet and a reader link with the right range", async () => {
    renderSearch();
    typeQuery("loved");

    const verses = await screen.findByTestId("verse-results");
    const link = await within(verses).findByRole("link", { name: "John 3:16" });
    // Snippet renders a real <mark>, not literal tag text.
    const mark = verses.querySelector("mark");
    expect(mark?.textContent).toBe("loved");
    expect(verses.textContent).not.toContain("<mark>");

    fireEvent.click(link);
    expect(screen.getByTestId("loc")).toHaveTextContent("/read/BSB/John/3?range=16-16");
  });

  it("shows matched translation codes for a grouped (translation=ALL) verse hit", async () => {
    server.use(
      http.get("/api/v1/bible/search", () =>
        HttpResponse.json(
          makeSearchResponse({
            translation_code: "ALL",
            verse_hits: [
              {
                translation_code: "BSB",
                book: "John",
                chapter: 3,
                verse: 16,
                snippet: "For God so <mark>loved</mark> the world.",
                translation_codes: ["BSB", "KJV"],
              },
            ],
            note_hits: [],
          }),
        ),
      ),
    );
    renderSearch();
    fireEvent.change(screen.getByLabelText("Search translation"), {
      target: { value: "ALL" },
    });
    typeQuery("loved");

    expect(await screen.findByTestId("verse-codes")).toHaveTextContent("BSB, KJV");
  });

  it("scope=both shows note hits with their note_type in a separate list", async () => {
    renderSearch();
    typeQuery("hebrew");

    const notes = await screen.findByTestId("note-results");
    expect(within(notes).getByText("Translator's Note")).toBeInTheDocument();
    expect(within(notes).getByRole("link", { name: "Gen 1:1" })).toBeInTheDocument();
    // scope=both → the verse list is also present.
    expect(screen.getByTestId("verse-results")).toBeInTheDocument();
  });

  it("scope=notes with no note matches shows an empty note result, not an error", async () => {
    server.use(
      http.get("/api/v1/bible/search", () =>
        HttpResponse.json(
          makeSearchResponse({ scope: "notes", note_hits: [], total_note_hits: 0 }),
        ),
      ),
    );
    renderSearch();
    fireEvent.click(screen.getByRole("button", { name: "Notes" }));
    typeQuery("loved");

    const notes = await screen.findByTestId("note-results");
    expect(within(notes).getByText("No note matches.")).toBeInTheDocument();
    // scope=notes → the verse section is not shown.
    expect(screen.queryByTestId("verse-results")).not.toBeInTheDocument();
  });

  it("is a distinct surface from entry search (own heading + placeholder)", () => {
    renderSearch();
    expect(screen.getByRole("heading", { name: "Search Scripture" })).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText("Search scripture and notes…"),
    ).toBeInTheDocument();
    // Not the entry-search placeholder.
    expect(
      screen.queryByPlaceholderText("Search titles, observations, prayer…"),
    ).not.toBeInTheDocument();
  });

  it("shows a prompt and does not query for a blank search", () => {
    renderSearch();
    expect(
      screen.getByText(/type a word or phrase to search/i),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("verse-results")).not.toBeInTheDocument();
  });
});
