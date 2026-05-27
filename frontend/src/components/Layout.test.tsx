import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { Layout } from "@/components/Layout";
import { server } from "@/test/msw/server";
import { makeUser } from "@/test/utils/factories";
import { renderWithProviders } from "@/test/utils/renderWithProviders";

describe("Layout", () => {
  it("shows the Admin link in the top bar when the user is an admin", async () => {
    server.use(
      http.get("/api/v1/auth/me", () =>
        HttpResponse.json(
          { user: makeUser({ username: "alice", is_admin: true }) },
          { status: 200 },
        ),
      ),
    );

    renderWithProviders(
      <Layout>
        <div>BODY</div>
      </Layout>,
    );

    await waitFor(() =>
      expect(screen.getByRole("link", { name: /admin/i })).toBeInTheDocument(),
    );
  });

  it("hides the Admin link for non-admin users", async () => {
    server.use(
      http.get("/api/v1/auth/me", () =>
        HttpResponse.json(
          { user: makeUser({ username: "bob", is_admin: false }) },
          { status: 200 },
        ),
      ),
    );

    renderWithProviders(
      <Layout>
        <div>BODY</div>
      </Layout>,
    );

    // Wait for the username to render so /auth/me has resolved before we
    // assert the link is absent.
    await waitFor(() => expect(screen.getByText("bob")).toBeInTheDocument());
    expect(screen.queryByRole("link", { name: /admin/i })).not.toBeInTheDocument();
  });
});
