import { setupServer } from "msw/node";

import { defaultHandlers } from "@/test/msw/handlers";

/**
 * Singleton MSW server for the test session. setup.ts wires the
 * before/after hooks. Tests override per-endpoint with `server.use(...)`.
 */
export const server = setupServer(...defaultHandlers);
