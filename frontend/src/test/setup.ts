import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, beforeEach, vi } from "vitest";

import { server } from "@/test/msw/server";

// happy-dom doesn't ship a matchMedia. The theme module reads it on
// initial mount via `prefers-color-scheme`, so stub it before any
// component mounts.
if (typeof window !== "undefined" && typeof window.matchMedia !== "function") {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(), // legacy
      removeListener: vi.fn(), // legacy
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }),
  });
}

beforeAll(() => {
  // Fail loudly on any request the tests didn't anticipate. Catches
  // typos in handler URLs and silent fall-throughs to the real network.
  server.listen({ onUnhandledRequest: "error" });
});

beforeEach(() => {
  // Independent test isolation: each test starts with no persisted
  // theme and the `dark` class cleared from the document root.
  window.localStorage.clear();
  document.documentElement.className = "";
});

afterEach(() => {
  cleanup();
  // Drop any per-test `server.use(...)` overrides.
  server.resetHandlers();
});

afterAll(() => {
  server.close();
});
