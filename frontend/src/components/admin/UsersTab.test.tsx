import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { UsersTab } from "@/components/admin/UsersTab";
import { server } from "@/test/msw/server";
import { makeAdminUserList } from "@/test/utils/admin";
import { makeUser } from "@/test/utils/factories";
import { renderWithProviders } from "@/test/utils/renderWithProviders";

function setup() {
  return renderWithProviders(<UsersTab />);
}

describe("UsersTab", () => {
  it("renders the users returned by adminListUsers, marking the current user as (you)", async () => {
    server.use(
      http.get("/api/v1/auth/me", () =>
        HttpResponse.json(
          { user: makeUser({ id: 1, username: "alice", is_admin: true }) },
          { status: 200 },
        ),
      ),
      http.get("/api/v1/admin/users", () =>
        HttpResponse.json(
          makeAdminUserList([
            makeUser({ id: 1, username: "alice", is_admin: true }),
            makeUser({ id: 2, username: "bob", is_admin: false }),
          ]),
          { status: 200 },
        ),
      ),
    );

    setup();

    expect(await screen.findByText("alice")).toBeInTheDocument();
    expect(screen.getByText("bob")).toBeInTheDocument();
    expect(screen.getByText(/\(you\)/i)).toBeInTheDocument();
  });

  it("does not render a Delete button on the current user's row", async () => {
    server.use(
      http.get("/api/v1/auth/me", () =>
        HttpResponse.json(
          { user: makeUser({ id: 1, username: "alice", is_admin: true }) },
          { status: 200 },
        ),
      ),
      http.get("/api/v1/admin/users", () =>
        HttpResponse.json(
          makeAdminUserList([
            makeUser({ id: 1, username: "alice", is_admin: true }),
            makeUser({ id: 2, username: "bob", is_admin: false }),
          ]),
          { status: 200 },
        ),
      ),
    );

    setup();

    const aliceRow = await screen.findByTestId("user-row-1");
    expect(
      within(aliceRow).queryByRole("button", { name: /^delete$/i }),
    ).not.toBeInTheDocument();
    const bobRow = screen.getByTestId("user-row-2");
    expect(
      within(bobRow).getByRole("button", { name: /^delete$/i }),
    ).toBeInTheDocument();
  });

  it("creates a new user via the New user dialog and shows a success banner", async () => {
    server.use(
      http.get("/api/v1/admin/users", () =>
        HttpResponse.json(makeAdminUserList([makeUser({ id: 1, username: "alice" })]), {
          status: 200,
        }),
      ),
      http.post("/api/v1/admin/users", () =>
        HttpResponse.json(
          { user: makeUser({ id: 42, username: "carol", is_admin: false }) },
          { status: 201 },
        ),
      ),
    );

    const user = userEvent.setup();
    setup();

    await user.click(await screen.findByRole("button", { name: /new user/i }));
    await user.type(screen.getByLabelText(/username/i), "carol");
    await user.type(screen.getByLabelText(/password/i), "hunter22!");
    await user.click(screen.getByRole("button", { name: /^create$/i }));

    await waitFor(() =>
      expect(screen.getByTestId("users-banner-success")).toHaveTextContent(
        /created carol/i,
      ),
    );
  });

  it("surfaces server-side LAST_ADMIN error when demoting the last admin", async () => {
    server.use(
      http.get("/api/v1/auth/me", () =>
        HttpResponse.json(
          { user: makeUser({ id: 1, username: "alice", is_admin: true }) },
          { status: 200 },
        ),
      ),
      http.get("/api/v1/admin/users", () =>
        HttpResponse.json(
          makeAdminUserList([makeUser({ id: 1, username: "alice", is_admin: true })]),
          { status: 200 },
        ),
      ),
      http.post("/api/v1/admin/users/:userId/demote", () =>
        HttpResponse.json(
          {
            detail: {
              code: "LAST_ADMIN",
              message: "cannot remove the last admin",
            },
          },
          { status: 409 },
        ),
      ),
    );

    const user = userEvent.setup();
    setup();

    const row = await screen.findByTestId("user-row-1");
    await user.click(within(row).getByRole("button", { name: /demote/i }));

    await waitFor(() =>
      expect(screen.getByTestId("users-banner-error")).toHaveTextContent(
        /last admin/i,
      ),
    );
  });

  it("deletes a user after confirmation", async () => {
    let deleted = false;
    server.use(
      http.get("/api/v1/auth/me", () =>
        HttpResponse.json(
          { user: makeUser({ id: 1, username: "alice", is_admin: true }) },
          { status: 200 },
        ),
      ),
      http.get("/api/v1/admin/users", () =>
        HttpResponse.json(
          makeAdminUserList([
            makeUser({ id: 1, username: "alice", is_admin: true }),
            makeUser({ id: 2, username: "bob", is_admin: false }),
          ]),
          { status: 200 },
        ),
      ),
      http.delete("/api/v1/admin/users/:userId", () => {
        deleted = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );

    const user = userEvent.setup();
    setup();

    const bobRow = await screen.findByTestId("user-row-2");
    await user.click(within(bobRow).getByRole("button", { name: /^delete$/i }));

    // ConfirmDialog renders the destructive confirm button inside a
    // native <dialog>. Scope to that dialog so we don't collide with
    // the row's own Delete button.
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: /^delete$/i }));

    await waitFor(() => expect(deleted).toBe(true));
    await waitFor(() =>
      expect(screen.getByTestId("users-banner-success")).toHaveTextContent(
        /deleted bob/i,
      ),
    );
  });

  it("resets a user's password via the Reset dialog", async () => {
    let receivedBody: { new_password: string } | null = null;
    server.use(
      http.get("/api/v1/admin/users", () =>
        HttpResponse.json(
          makeAdminUserList([makeUser({ id: 2, username: "bob", is_admin: false })]),
          { status: 200 },
        ),
      ),
      http.post(
        "/api/v1/admin/users/:userId/reset-password",
        async ({ request }) => {
          receivedBody = (await request.json()) as typeof receivedBody;
          return new HttpResponse(null, { status: 204 });
        },
      ),
    );

    const user = userEvent.setup();
    setup();

    const row = await screen.findByTestId("user-row-2");
    await user.click(
      within(row).getByRole("button", { name: /reset password/i }),
    );

    await user.type(screen.getByLabelText(/new password/i), "freshpass1");
    await user.click(screen.getByRole("button", { name: /^reset$/i }));

    await waitFor(() =>
      expect(receivedBody).toEqual({ new_password: "freshpass1" }),
    );
    await waitFor(() =>
      expect(screen.getByTestId("users-banner-success")).toHaveTextContent(
        /password reset for bob/i,
      ),
    );
  });
});
