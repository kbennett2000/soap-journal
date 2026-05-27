import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { RequireAdmin } from "@/components/RequireAdmin";
import { server } from "@/test/msw/server";
import { makeUser } from "@/test/utils/factories";
import { renderWithProviders } from "@/test/utils/renderWithProviders";

function renderGuarded() {
  return renderWithProviders(
    <RequireAdmin>
      <div>ADMIN AREA</div>
    </RequireAdmin>,
  );
}

describe("RequireAdmin", () => {
  it("renders children for an admin user", async () => {
    // Default handler returns alice with is_admin: true.
    renderGuarded();
    await waitFor(() =>
      expect(screen.getByText("ADMIN AREA")).toBeInTheDocument(),
    );
  });

  it("renders a 403 when the authenticated user is not an admin", async () => {
    server.use(
      http.get("/api/v1/auth/me", () =>
        HttpResponse.json(
          { user: makeUser({ is_admin: false, username: "bob" }) },
          { status: 200 },
        ),
      ),
    );

    renderGuarded();

    await waitFor(() =>
      expect(screen.getByTestId("admin-forbidden")).toBeInTheDocument(),
    );
    expect(screen.queryByText("ADMIN AREA")).not.toBeInTheDocument();
  });

  it("renders 403 when no one is signed in (RequireAuth normally catches this; defense in depth)", async () => {
    server.use(
      http.get("/api/v1/auth/me", () =>
        HttpResponse.json(
          { detail: { code: "NOT_AUTHENTICATED", message: "not signed in" } },
          { status: 401 },
        ),
      ),
    );

    renderGuarded();
    await waitFor(() =>
      expect(screen.getByTestId("admin-forbidden")).toBeInTheDocument(),
    );
  });
});
