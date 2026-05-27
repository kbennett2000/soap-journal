import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router-dom";

import { EntryListPage } from "@/routes/EntryListPage";
import { server } from "@/test/msw/server";
import { makeEntry, makeEntryList } from "@/test/utils/entries";
import { renderWithProviders } from "@/test/utils/renderWithProviders";

function renderList(initialEntries: string[] = ["/entries"]) {
  return renderWithProviders(
    <Routes>
      <Route path="/entries" element={<EntryListPage />} />
      <Route path="/entries/new" element={<div>NEW</div>} />
    </Routes>,
    { initialEntries },
  );
}

describe("EntryListPage", () => {
  it("renders the entries returned by listEntries", async () => {
    server.use(
      http.get("/api/v1/entries", () =>
        HttpResponse.json(
          makeEntryList([
            makeEntry({ id: 1, display_title: "Love defined" }),
            makeEntry({ id: 2, display_title: "Working for good" }),
          ]),
          { status: 200 },
        ),
      ),
    );

    renderList();

    expect(await screen.findByText("Love defined")).toBeInTheDocument();
    expect(screen.getByText("Working for good")).toBeInTheDocument();
  });

  it("renders the empty state CTA when there are no entries", async () => {
    server.use(
      http.get("/api/v1/entries", () =>
        HttpResponse.json(makeEntryList([], { total: 0 }), { status: 200 }),
      ),
    );

    renderList();

    expect(await screen.findByTestId("entries-empty")).toBeInTheDocument();
  });

  it("pagination disables Previous on page 0 and Next when on the last page", async () => {
    server.use(
      http.get("/api/v1/entries", ({ request }) => {
        const url = new URL(request.url);
        const offset = Number(url.searchParams.get("offset") ?? 0);
        const limit = Number(url.searchParams.get("limit") ?? 20);
        return HttpResponse.json(
          makeEntryList(
            [makeEntry({ id: offset + 1, display_title: `Entry ${offset + 1}` })],
            { total: 2, limit, offset },
          ),
          { status: 200 },
        );
      }),
    );

    const user = userEvent.setup();
    renderList(["/entries?limit=1"]);

    await screen.findByText("Entry 1");
    expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /next/i })).toBeEnabled();

    await user.click(screen.getByRole("button", { name: /next/i }));

    await screen.findByText("Entry 2");
    expect(screen.getByRole("button", { name: /previous/i })).toBeEnabled();
    expect(screen.getByRole("button", { name: /next/i })).toBeDisabled();
  });

  it("order toggle updates the URL and re-fetches", async () => {
    let lastOrder: string | null = null;
    server.use(
      http.get("/api/v1/entries", ({ request }) => {
        const url = new URL(request.url);
        lastOrder = url.searchParams.get("order");
        return HttpResponse.json(
          makeEntryList([makeEntry({ display_title: "An entry" })]),
          { status: 200 },
        );
      }),
    );

    const user = userEvent.setup();
    renderList();
    await screen.findByText("An entry");
    // Initial render fetches newest (the route default).
    expect(lastOrder).toBe("newest");

    await user.click(screen.getByRole("button", { name: /oldest first/i }));

    await waitFor(() => expect(lastOrder).toBe("oldest"));
  });
});
