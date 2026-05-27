import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route, Routes, useLocation } from "react-router-dom";

import { EntryNewPage } from "@/routes/EntryNewPage";
import { server } from "@/test/msw/server";
import { makeEntryEnvelope } from "@/test/utils/entries";
import { renderWithProviders } from "@/test/utils/renderWithProviders";

function PageStub(): JSX.Element {
  const loc = useLocation();
  return <div data-testid="landed-on">{loc.pathname}</div>;
}

function renderPage(initialEntries: string[], state?: unknown) {
  return renderWithProviders(
    <Routes>
      <Route path="/entries/new" element={<EntryNewPage />} />
      <Route path="/entries/:entryId" element={<PageStub />} />
    </Routes>,
    {
      initialEntries: initialEntries.map((path) =>
        state === undefined ? path : { pathname: path, state },
      ),
    },
  );
}

describe("EntryNewPage", () => {
  it("pre-fills form from location.state", async () => {
    renderPage(["/entries/new"], {
      scriptureRef: "Psalm 23:1",
      translationCode: "BSB",
    });

    expect(await screen.findByLabelText(/scripture reference/i)).toHaveValue(
      "Psalm 23:1",
    );
  });

  it("defaults to today's date when no state is provided", async () => {
    renderPage(["/entries/new"]);

    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, "0");
    const dd = String(today.getDate()).padStart(2, "0");
    const expected = `${yyyy}-${mm}-${dd}`;

    expect(await screen.findByLabelText(/date/i)).toHaveValue(expected);
  });

  it("navigates to /entries/:id on successful create", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("/api/v1/entries", () =>
        HttpResponse.json(makeEntryEnvelope({ id: 4242 }), { status: 201 }),
      ),
    );

    renderPage(["/entries/new"]);

    await user.type(screen.getByLabelText(/scripture reference/i), "John 3:16");
    await user.click(screen.getByRole("button", { name: /create entry/i }));

    await waitFor(() =>
      expect(screen.getByTestId("landed-on")).toHaveTextContent("/entries/4242"),
    );
  });
});
