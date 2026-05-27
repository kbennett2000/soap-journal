import { http, HttpResponse } from "msw";

import {
  adminCreateUser,
  adminDeleteUser,
  adminDemoteUser,
  adminGetSettings,
  adminListUsers,
  adminPromoteUser,
  adminResetPassword,
  adminUpdateSettings,
} from "@/lib/admin";
import { ApiError } from "@/lib/apiError";
import { server } from "@/test/msw/server";
import { makeAdminUserList, makeSettingsEnvelope } from "@/test/utils/admin";
import { makeUser } from "@/test/utils/factories";

describe("lib/admin", () => {
  it("adminListUsers returns the wrapped user array shape", async () => {
    server.use(
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

    const res = await adminListUsers();
    expect(res.users.map((u) => u.username)).toEqual(["alice", "bob"]);
  });

  it("adminCreateUser unwraps { user } and posts the body", async () => {
    let received: { username: string; password: string; is_admin?: boolean } | null = null;
    server.use(
      http.post("/api/v1/admin/users", async ({ request }) => {
        received = (await request.json()) as typeof received;
        return HttpResponse.json(
          { user: makeUser({ id: 99, username: "carol", is_admin: true }) },
          { status: 201 },
        );
      }),
    );

    const created = await adminCreateUser({
      username: "carol",
      password: "hunter22!",
      is_admin: true,
    });

    expect(created.username).toBe("carol");
    expect(created.is_admin).toBe(true);
    expect(received).toEqual({
      username: "carol",
      password: "hunter22!",
      is_admin: true,
    });
  });

  it("adminCreateUser throws ApiError on 409 USERNAME_TAKEN", async () => {
    server.use(
      http.post("/api/v1/admin/users", () =>
        HttpResponse.json(
          { detail: { code: "USERNAME_TAKEN", message: "username taken" } },
          { status: 409 },
        ),
      ),
    );

    await expect(
      adminCreateUser({ username: "alice", password: "hunter22!" }),
    ).rejects.toMatchObject({
      status: 409,
      code: "USERNAME_TAKEN",
    });
  });

  it("adminDeleteUser resolves on 204", async () => {
    server.use(
      http.delete("/api/v1/admin/users/:userId", () =>
        new HttpResponse(null, { status: 204 }),
      ),
    );

    await expect(adminDeleteUser(7)).resolves.toBeUndefined();
  });

  it("adminDeleteUser surfaces LAST_ADMIN on 409", async () => {
    server.use(
      http.delete("/api/v1/admin/users/:userId", () =>
        HttpResponse.json(
          { detail: { code: "LAST_ADMIN", message: "cannot remove last admin" } },
          { status: 409 },
        ),
      ),
    );

    await expect(adminDeleteUser(1)).rejects.toBeInstanceOf(ApiError);
  });

  it("adminResetPassword posts new_password and resolves on 204", async () => {
    let received: { new_password: string } | null = null;
    server.use(
      http.post(
        "/api/v1/admin/users/:userId/reset-password",
        async ({ request }) => {
          received = (await request.json()) as typeof received;
          return new HttpResponse(null, { status: 204 });
        },
      ),
    );

    await adminResetPassword(7, "newpass123");
    expect(received).toEqual({ new_password: "newpass123" });
  });

  it("adminPromoteUser unwraps the user envelope", async () => {
    server.use(
      http.post("/api/v1/admin/users/:userId/promote", () =>
        HttpResponse.json(
          { user: makeUser({ id: 5, is_admin: true }) },
          { status: 200 },
        ),
      ),
    );

    const user = await adminPromoteUser(5);
    expect(user.is_admin).toBe(true);
  });

  it("adminDemoteUser unwraps the user envelope", async () => {
    server.use(
      http.post("/api/v1/admin/users/:userId/demote", () =>
        HttpResponse.json(
          { user: makeUser({ id: 5, is_admin: false }) },
          { status: 200 },
        ),
      ),
    );

    const user = await adminDemoteUser(5);
    expect(user.is_admin).toBe(false);
  });

  it("adminGetSettings unwraps the settings envelope", async () => {
    server.use(
      http.get("/api/v1/admin/settings", () =>
        HttpResponse.json(makeSettingsEnvelope({ open_registration: true }), {
          status: 200,
        }),
      ),
    );

    const settings = await adminGetSettings();
    expect(settings.open_registration).toBe(true);
  });

  it("adminUpdateSettings PUTs the body and unwraps the response", async () => {
    let received: { open_registration: boolean } | null = null;
    server.use(
      http.put("/api/v1/admin/settings", async ({ request }) => {
        received = (await request.json()) as typeof received;
        return HttpResponse.json(
          makeSettingsEnvelope({ open_registration: true }),
          { status: 200 },
        );
      }),
    );

    const settings = await adminUpdateSettings({ open_registration: true });
    expect(settings.open_registration).toBe(true);
    expect(received).toEqual({ open_registration: true });
  });
});
