import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route, Routes, useLocation } from "react-router-dom";

import { DashboardPage } from "@/routes/DashboardPage";
import { server } from "@/test/msw/server";
import {
  makeEntry,
  makeEntryList,
  makeOnThisDayResponse,
} from "@/test/utils/entries";
import { renderWithProviders } from "@/test/utils/renderWithProviders";

function LocationStub(): JSX.Element {
  const loc = useLocation();
  return (
    <div data-testid="landed-on">
      {loc.pathname}
      {loc.search}
    </div>
  );
}

function renderDashboard() {
  return renderWithProviders(
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route
        path="/read/:translationCode/:bookName/:chapterNumber"
        element={<LocationStub />}
      />
      <Route path="*" element={<LocationStub />} />
    </Routes>,
    { initialEntries: ["/"] },
  );
}

describe("DashboardPage", () => {
  it("renders the welcome line with the username", async () => {
    renderDashboard();
    expect(
      await screen.findByRole("heading", { name: /welcome, alice/i }),
    ).toBeInTheDocument();
  });

  it("recent-entries section renders cards from the mocked list", async () => {
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

    renderDashboard();

    expect(await screen.findByText("Love defined")).toBeInTheDocument();
    expect(screen.getByText("Working for good")).toBeInTheDocument();
  });

  it("on-this-day section renders cards when entries are present", async () => {
    server.use(
      http.get("/api/v1/entries/on-this-day", () =>
        HttpResponse.json(
          makeOnThisDayResponse([
            makeEntry({
              id: 11,
              display_title: "Five years ago",
              entry_date: "2021-05-27",
            }),
          ]),
          { status: 200 },
        ),
      ),
    );

    renderDashboard();
    expect(await screen.findByText("Five years ago")).toBeInTheDocument();
  });

  it("recent + on-this-day empty states render their messages", async () => {
    server.use(
      http.get("/api/v1/entries", () =>
        HttpResponse.json(makeEntryList([], { total: 0 }), { status: 200 }),
      ),
      http.get("/api/v1/entries/on-this-day", () =>
        HttpResponse.json(makeOnThisDayResponse([]), { status: 200 }),
      ),
    );

    renderDashboard();

    expect(await screen.findByTestId("dash-recent-empty")).toBeInTheDocument();
    expect(screen.getByTestId("dash-onthisday-empty")).toBeInTheDocument();
  });

  it("jump bar submits a ref and navigates to the reader", async () => {
    const user = userEvent.setup();
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
            verses: [],
          },
          { status: 200 },
        ),
      ),
    );

    renderDashboard();
    await screen.findByLabelText(/jump to reference/i);

    await user.type(screen.getByLabelText(/jump to reference/i), "John 3:16");
    await user.click(screen.getByRole("button", { name: /^go$/i }));

    await waitFor(() => {
      const landed = screen.getByTestId("landed-on");
      expect(landed.textContent).toContain("/read/BSB/John/3");
      expect(landed.textContent).toContain("range=16-16");
    });
  });
});
