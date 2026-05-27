import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route, Routes, useLocation } from "react-router-dom";

import { EntryDetailPage } from "@/routes/EntryDetailPage";
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

function renderDetail(initialEntries: string[] = ["/entries/42"]) {
  return renderWithProviders(
    <Routes>
      <Route path="/entries/:entryId" element={<EntryDetailPage />} />
      <Route path="/entries/:entryId/edit" element={<Stub label="edit" />} />
      <Route path="/entries" element={<Stub label="list" />} />
    </Routes>,
    { initialEntries },
  );
}

describe("EntryDetailPage", () => {
  it("renders the entry fields", async () => {
    server.use(
      http.get("/api/v1/entries/:id", () =>
        HttpResponse.json(
          makeEntryEnvelope({
            id: 42,
            title: "Love defined",
            display_title: "Love defined",
            observation: "What love is.",
            application: "Practice these.",
            prayer: "Lord, shape my heart.",
          }),
          { status: 200 },
        ),
      ),
    );

    renderDetail();

    expect(await screen.findByRole("heading", { name: /love defined/i })).toBeInTheDocument();
    expect(screen.getByText("What love is.")).toBeInTheDocument();
    expect(screen.getByText("Practice these.")).toBeInTheDocument();
    expect(screen.getByText("Lord, shape my heart.")).toBeInTheDocument();
  });

  it("Edit button navigates to the edit route", async () => {
    const user = userEvent.setup();
    renderDetail();

    const editLink = await screen.findByRole("link", { name: /edit/i });
    await user.click(editLink);

    await waitFor(() =>
      expect(screen.getByTestId("edit")).toHaveTextContent("/entries/42/edit"),
    );
  });

  it("Delete confirms and navigates to /entries", async () => {
    const user = userEvent.setup();
    renderDetail();

    await screen.findByRole("button", { name: /delete/i });
    await user.click(screen.getByRole("button", { name: /delete/i }));

    // The ConfirmDialog button is also labeled "Delete" — find the one
    // inside the dialog.
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

  it("renders 'not found' panel on 404", async () => {
    server.use(
      http.get("/api/v1/entries/:id", () =>
        HttpResponse.json(
          { detail: { code: "ENTRY_NOT_FOUND", message: "entry 42 not found" } },
          { status: 404 },
        ),
      ),
    );

    renderDetail();
    expect(await screen.findByTestId("entry-not-found")).toBeInTheDocument();
  });
});
