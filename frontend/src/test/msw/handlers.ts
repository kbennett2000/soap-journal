import { http, HttpResponse } from "msw";

import { makeUser } from "@/test/utils/factories";
import type { AuthEnvelope } from "@/types/api";

/**
 * Default happy-path handlers. Each test overrides the specific
 * endpoint(s) it wants to behave differently via `server.use(...)`.
 *
 * Handlers are exported individually so a test can pluck `meHandler`
 * and replace it with its own version without redefining the URL or
 * thinking about request shape.
 */

export const meHandler = http.get("/api/v1/auth/me", () => {
  const envelope: AuthEnvelope = { user: makeUser() };
  return HttpResponse.json(envelope, { status: 200 });
});

export const loginHandler = http.post("/api/v1/auth/login", () => {
  const envelope: AuthEnvelope = { user: makeUser() };
  return HttpResponse.json(envelope, { status: 200 });
});

export const registerHandler = http.post("/api/v1/auth/register", () => {
  const envelope: AuthEnvelope = { user: makeUser() };
  return HttpResponse.json(envelope, { status: 201 });
});

export const logoutHandler = http.post("/api/v1/auth/logout", () => {
  return new HttpResponse(null, { status: 204 });
});

export const defaultHandlers = [
  meHandler,
  loginHandler,
  registerHandler,
  logoutHandler,
];
