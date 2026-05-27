import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { EntryFormScripturePreview } from "@/components/EntryFormScripturePreview";
import { server } from "@/test/msw/server";
import { renderWithProviders } from "@/test/utils/renderWithProviders";

describe("EntryFormScripturePreview", () => {
  it("renders nothing when scriptureRef is empty", () => {
    const { container } = renderWithProviders(
      <EntryFormScripturePreview scriptureRef="" translationCode="BSB" />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders the resolved text after debounce and shows the canonical reference", async () => {
    server.use(
      http.get("/api/v1/bible/resolve", () =>
        HttpResponse.json(
          {
            reference: {
              canonical_string: "John 3:16",
              translation_code: "BSB",
              book: {
                name: "John",
                abbreviation: "John",
                order_index: 43,
                testament: "NT",
                chapter_count: 21,
              },
              chapter_number: 3,
              start_verse: 16,
              end_verse: 16,
            },
            verses: [
              {
                id: 1,
                number: 16,
                text: "For God so loved the world.",
                is_red_letter: false,
                footnotes: [],
              },
            ],
          },
          { status: 200 },
        ),
      ),
    );

    renderWithProviders(
      <EntryFormScripturePreview scriptureRef="jn 3:16" translationCode="BSB" />,
    );

    const preview = await screen.findByTestId("scripture-preview");
    expect(preview).toHaveTextContent("John 3:16");
    expect(preview).toHaveTextContent("For God so loved the world.");
  });

  it("renders the server's error message on 400", async () => {
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

    renderWithProviders(
      <EntryFormScripturePreview scriptureRef="Frodo 3:16" translationCode="BSB" />,
    );

    await waitFor(() =>
      expect(screen.getByTestId("scripture-preview-error")).toHaveTextContent(
        /unknown book/i,
      ),
    );
  });
});
