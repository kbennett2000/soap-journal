import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { Layout } from "@/components/Layout";
import { RequireAuth } from "@/components/RequireAuth";
import { BackupPage } from "@/routes/BackupPage";
import { server } from "@/test/msw/server";
import { makeImportReport, makeUser } from "@/test/utils/factories";
import { renderWithProviders } from "@/test/utils/renderWithProviders";

const VALID_BACKUP = {
  format: "soap-journal-backup",
  version: 1,
  exported_at: "2026-06-03T00:00:00Z",
  entries: [],
};

function jsonFile(value: unknown, name = "backup.json"): File {
  return new File([JSON.stringify(value)], name, { type: "application/json" });
}

function renderBackup() {
  return renderWithProviders(<BackupPage />, { initialEntries: ["/backup"] });
}

describe("BackupPage", () => {
  it("renders the export and import controls", async () => {
    renderBackup();
    expect(
      await screen.findByRole("link", { name: /export backup/i }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/backup file/i)).toBeInTheDocument();
  });

  it("export control links to the export endpoint", async () => {
    renderBackup();
    const link = await screen.findByRole("link", { name: /export backup/i });
    expect(link).toHaveAttribute("href", "/api/v1/backup/export");
  });

  it("imports in two steps: dry-run preview then a confirmed real import", async () => {
    const user = userEvent.setup();
    const dryRunFlags: boolean[] = [];
    server.use(
      http.post("/api/v1/backup/import", async ({ request }) => {
        const dryRun =
          new URL(request.url).searchParams.get("dry_run") === "true";
        dryRunFlags.push(dryRun);
        await request.json();
        return HttpResponse.json(
          makeImportReport({ inserted: 2, updated: 1, total_in_file: 3, dry_run: dryRun }),
          { status: 200 },
        );
      }),
    );

    const { queryClient } = renderBackup();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    await user.upload(screen.getByLabelText(/backup file/i), jsonFile(VALID_BACKUP));

    // Dry-run preview fired with dry_run=true and renders the counts.
    expect(
      await screen.findByText(/would import: 2 new, 1 updated, 0 unchanged/i),
    ).toBeInTheDocument();
    expect(dryRunFlags).toEqual([true]);

    // Confirm fires the real import with dry_run=false.
    await user.click(screen.getByRole("button", { name: /confirm import/i }));

    expect(
      await screen.findByText(/imported 2 new, 1 updated, 0 unchanged/i),
    ).toBeInTheDocument();
    expect(dryRunFlags).toEqual([true, false]);

    // The journal views are invalidated after the real import.
    await waitFor(() =>
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ["entries", "list"],
      }),
    );
  });

  it("preview surfaces translations not loaded on this server", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("/api/v1/backup/import", () =>
        HttpResponse.json(
          makeImportReport({
            inserted: 1,
            skipped_missing_translation: 1,
            missing_translations: ["ESV"],
            total_in_file: 2,
            dry_run: true,
          }),
          { status: 200 },
        ),
      ),
    );

    renderBackup();
    await user.upload(screen.getByLabelText(/backup file/i), jsonFile(VALID_BACKUP));

    expect(
      await screen.findByText(/translations not loaded on this server: ESV/i),
    ).toBeInTheDocument();
  });

  it("rejects a non-JSON file locally without POSTing", async () => {
    const user = userEvent.setup();
    let posted = false;
    server.use(
      http.post("/api/v1/backup/import", () => {
        posted = true;
        return HttpResponse.json(makeImportReport(), { status: 200 });
      }),
    );

    renderBackup();
    const badFile = new File(["this is not json"], "notes.json", {
      type: "application/json",
    });
    await user.upload(screen.getByLabelText(/backup file/i), badFile);

    expect(
      await screen.findByText(/isn't valid json/i),
    ).toBeInTheDocument();
    expect(posted).toBe(false);
    expect(
      screen.queryByRole("button", { name: /confirm import/i }),
    ).not.toBeInTheDocument();
  });

  it("maps a newer-version rejection to a friendly message", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("/api/v1/backup/import", () =>
        HttpResponse.json(
          {
            detail: {
              code: "BACKUP_VERSION_UNSUPPORTED",
              message: "this backup is from a newer version of the app",
            },
          },
          { status: 400 },
        ),
      ),
    );

    renderBackup();
    await user.upload(screen.getByLabelText(/backup file/i), jsonFile(VALID_BACKUP));

    expect(
      await screen.findByText(/newer version of the app/i),
    ).toBeInTheDocument();
  });

  it("shows the server message for an invalid-backup rejection", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("/api/v1/backup/import", () =>
        HttpResponse.json(
          {
            detail: {
              code: "INVALID_BACKUP",
              message: "entry 2 has an invalid date or timestamp",
            },
          },
          { status: 400 },
        ),
      ),
    );

    renderBackup();
    await user.upload(screen.getByLabelText(/backup file/i), jsonFile(VALID_BACKUP));

    expect(
      await screen.findByText(/entry 2 has an invalid date or timestamp/i),
    ).toBeInTheDocument();
  });

  it("shows the Backup link to a non-admin user (not gated like Admin)", async () => {
    server.use(
      http.get("/api/v1/auth/me", () =>
        HttpResponse.json(
          { user: makeUser({ is_admin: false, username: "bob" }) },
          { status: 200 },
        ),
      ),
    );

    renderWithProviders(
      <Layout>
        <BackupPage />
      </Layout>,
      { initialEntries: ["/backup"] },
    );

    expect(
      await screen.findByRole("link", { name: "Backup" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Admin" })).not.toBeInTheDocument();
  });

  it("redirects to /login when unauthenticated (behind RequireAuth)", async () => {
    server.use(
      http.get("/api/v1/auth/me", () =>
        HttpResponse.json(
          { detail: { code: "NOT_AUTHENTICATED", message: "NOT_AUTHENTICATED" } },
          { status: 401 },
        ),
      ),
    );

    function LoginStub(): JSX.Element {
      const loc = useLocation();
      return <div data-testid="login-stub">{loc.pathname}</div>;
    }

    renderWithProviders(
      <Routes>
        <Route
          path="/backup"
          element={
            <RequireAuth>
              <Layout>
                <BackupPage />
              </Layout>
            </RequireAuth>
          }
        />
        <Route path="/login" element={<LoginStub />} />
      </Routes>,
      { initialEntries: ["/backup"] },
    );

    await waitFor(() =>
      expect(screen.getByTestId("login-stub")).toBeInTheDocument(),
    );
    expect(
      screen.queryByRole("heading", { name: /backup & restore/i }),
    ).not.toBeInTheDocument();
  });
});
