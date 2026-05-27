import { screen, waitFor } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { Route, Routes } from "react-router-dom";

import { RequireAuth } from "@/components/RequireAuth";
import { server } from "@/test/msw/server";
import { renderWithProviders } from "@/test/utils/renderWithProviders";

function renderGuarded(initialEntries: string[] = ["/"]) {
  return renderWithProviders(
    <Routes>
      <Route
        path="/"
        element={
          <RequireAuth>
            <div>SECRET</div>
          </RequireAuth>
        }
      />
      <Route path="/login" element={<div>LOGIN</div>} />
    </Routes>,
    { initialEntries },
  );
}

describe("RequireAuth", () => {
  it("renders a loading placeholder while /auth/me is in flight", async () => {
    // Delay the auth response so we can observe the loading state.
    server.use(
      http.get("/api/v1/auth/me", async () => {
        await delay(50);
        return HttpResponse.json(
          { detail: { code: "NOT_AUTHENTICATED", message: "NOT_AUTHENTICATED" } },
          { status: 401 },
        );
      }),
    );

    renderGuarded();
    // Loading text shows up immediately, before the request resolves.
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
    // …and once resolved (to 401), we redirect to /login.
    await waitFor(() => expect(screen.getByText("LOGIN")).toBeInTheDocument());
  });

  it("redirects to /login when /auth/me returns 401", async () => {
    server.use(
      http.get("/api/v1/auth/me", () =>
        HttpResponse.json(
          { detail: { code: "NOT_AUTHENTICATED", message: "NOT_AUTHENTICATED" } },
          { status: 401 },
        ),
      ),
    );

    renderGuarded();
    await waitFor(() => expect(screen.getByText("LOGIN")).toBeInTheDocument());
    expect(screen.queryByText("SECRET")).not.toBeInTheDocument();
  });

  it("renders children when the user is authenticated", async () => {
    // Default handler returns the alice user with 200.
    renderGuarded();
    await waitFor(() => expect(screen.getByText("SECRET")).toBeInTheDocument());
    expect(screen.queryByText("LOGIN")).not.toBeInTheDocument();
  });
});
