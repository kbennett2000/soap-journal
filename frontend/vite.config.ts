/// <reference types="vitest/config" />
import path from "node:path";
import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Dev server proxies /api -> FastAPI so the React dev server and the
// backend can run on different ports without CORS gymnastics. The
// proxy target is configurable via VITE_API_PROXY_TARGET; default is
// the FastAPI default port.
const apiProxyTarget = process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8080";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: apiProxyTarget,
        changeOrigin: true,
        secure: false,
      },
    },
  },
  // Vitest config — kept here rather than in a separate vitest.config.ts so
  // there's one source of truth for path aliases / plugins. The build
  // pipeline doesn't include src/test/** because Vite tree-shakes anything
  // not reachable from src/main.tsx, so no separate prod exclusion is
  // needed.
  test: {
    globals: true,
    environment: "happy-dom",
    setupFiles: ["src/test/setup.ts"],
    css: true,
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
  },
});
