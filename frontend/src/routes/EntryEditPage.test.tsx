import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route, Routes, useLocation } from "react-router-dom";

import { EntryEditPage } from "@/routes/EntryEditPage";
import { server } from "@/test/msw/server";
import { makeEntryEnvelope } from "@/test/utils/entries";
import { renderWithProviders } from "@/test/utils/renderWithProviders";

function Stub({ label }: { label: string }): JSX.Element {
  const loc = useLocation();
  return (
    <div data-testid={label}>
      {label}:{loc.pathname}
    </div>
  );
}

function renderEdit() {
  return renderWithProviders(
    <Routes>
      <Route path="/entries/:entryId/edit" element={<EntryEditPage />} />
      <Route path="/entries/:entryId" element={<Stub label="detail" />} />
      <Route path="/entries" element={<Stub label="list" />} />
    </Routes>,
    { initialEntries: ["/entries/42/edit"] },
  );
}

describe("EntryEditPage", () => {
  it("pre-fills the form from the fetched entry", async () => {
    server.use(
      http.get("/api/v1/entries/:id", () =>
        HttpResponse.json(
          makeEntryEnvelope({
            id: 42,
            title: "First title",
            observation: "obs",
          }),
          { status: 200 },
        ),
      ),
    );

    renderEdit();

    expect(await screen.findByLabelText(/title/i)).toHaveValue("First title");
    expect(screen.getByLabelText(/observation/i)).toHaveValue("obs");
  });

  it("Save success navigates to the detail page", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("/api/v1/entries/:id", () =>
        HttpResponse.json(makeEntryEnvelope({ id: 42 }), { status: 200 }),
      ),
      http.put("/api/v1/entries/:id", () =>
        HttpResponse.json(makeEntryEnvelope({ id: 42 }), { status: 200 }),
      ),
    );

    renderEdit();

    await screen.findByLabelText(/title/i);
    await user.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() =>
      expect(screen.getByTestId("detail")).toHaveTextContent("/entries/42"),
    );
  });

  it("Delete success navigates to the list", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("/api/v1/entries/:id", () =>
        HttpResponse.json(makeEntryEnvelope({ id: 42 }), { status: 200 }),
      ),
      http.delete("/api/v1/entries/:id", () => new HttpResponse(null, { status: 204 })),
    );

    renderEdit();

    await screen.findByLabelText(/title/i);
    await user.click(screen.getByRole("button", { name: /delete entry/i }));

    const dialog = await screen.findByRole("dialog");
    await user.click(
      Array.from(dialog.querySelectorAll("button")).find(
        (b) => b.textContent?.trim().toLowerCase() === "delete",
      )!,
    );

    await waitFor(() =>
      expect(screen.getByTestId("list")).toHaveTextContent("/entries"),
    );
  });
});
