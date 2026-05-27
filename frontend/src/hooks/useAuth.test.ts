import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { useAuth } from "@/hooks/useAuth";
import { server } from "@/test/msw/server";
import { makeHookWrapper } from "@/test/utils/renderWithProviders";
import { makeUser } from "@/test/utils/factories";

describe("useAuth", () => {
  it("populates `user` from /auth/me after mount", async () => {
    const { HookWrapper } = makeHookWrapper();
    const { result } = renderHook(() => useAuth(), { wrapper: HookWrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.user?.username).toBe("alice");
    expect(result.current.isAuthenticated).toBe(true);
  });

  it("treats a 401 from /auth/me as unauthenticated, not an error", async () => {
    server.use(
      http.get("/api/v1/auth/me", () =>
        HttpResponse.json(
          { detail: { code: "NOT_AUTHENTICATED", message: "NOT_AUTHENTICATED" } },
          { status: 401 },
        ),
      ),
    );

    const { HookWrapper } = makeHookWrapper();
    const { result } = renderHook(() => useAuth(), { wrapper: HookWrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.user).toBeUndefined();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it("login refetches /auth/me so the user shows up", async () => {
    // Start unauthenticated, then flip the handler after login is called.
    server.use(
      http.get("/api/v1/auth/me", () =>
        HttpResponse.json(
          { detail: { code: "NOT_AUTHENTICATED", message: "NOT_AUTHENTICATED" } },
          { status: 401 },
        ),
      ),
    );

    const { HookWrapper } = makeHookWrapper();
    const { result } = renderHook(() => useAuth(), { wrapper: HookWrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.isAuthenticated).toBe(false);

    // After a successful login the backend would set the cookie; the
    // mutation then refetches /auth/me. Swap the handler so the refetch
    // sees the user.
    server.use(
      http.get("/api/v1/auth/me", () =>
        HttpResponse.json({ user: makeUser({ username: "bob" }) }, { status: 200 }),
      ),
    );

    await act(async () => {
      await result.current.login("bob", "password123");
    });

    await waitFor(() => expect(result.current.isAuthenticated).toBe(true));
    expect(result.current.user?.username).toBe("bob");
  });

  it("logout clears the cached user and flips isAuthenticated to false", async () => {
    const { HookWrapper } = makeHookWrapper();
    const { result } = renderHook(() => useAuth(), { wrapper: HookWrapper });

    await waitFor(() => expect(result.current.isAuthenticated).toBe(true));

    // After the real backend processes logout the session cookie is
    // gone, so the next /auth/me would 401. Simulate that here:
    // `logout` calls `removeQueries`, which triggers useQuery to refetch
    // on next render — that refetch must see the 401 to land where the
    // user actually lands in production.
    server.use(
      http.get("/api/v1/auth/me", () =>
        HttpResponse.json(
          { detail: { code: "NOT_AUTHENTICATED", message: "NOT_AUTHENTICATED" } },
          { status: 401 },
        ),
      ),
    );

    await act(async () => {
      await result.current.logout();
    });

    await waitFor(() => expect(result.current.isAuthenticated).toBe(false));
    expect(result.current.user).toBeUndefined();
  });
});
