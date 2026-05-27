# frontend

soap-journal React frontend. See the repo root `README.md` and `CLAUDE.md`
for project overview and conventions.

## Scripts

```bash
npm run dev          # vite dev server with /api proxy to localhost:8045
npm run build        # typecheck + production build
npm run preview      # serve the built bundle (no /api proxy — see below)
npm run lint         # eslint
npm run typecheck    # tsc --noEmit
npm run test         # vitest, one-shot
npm run test:watch   # vitest, watch mode
npm run test:ui      # vitest's web UI (handy for debugging)
```

## Tests

Tests live next to the code they cover, mirroring the backend convention:

- `Foo.tsx` → `Foo.test.tsx`
- `useFoo.ts` → `useFoo.test.ts`

Shared test infrastructure lives under `src/test/`:

- `setup.ts` — runs before every test file. Imports
  `@testing-library/jest-dom` for matchers, wires the MSW lifecycle
  (`listen` / `resetHandlers` / `close`), resets `localStorage` and the
  `<html>` className between tests (theme persistence would otherwise
  leak), and stubs `window.matchMedia` (happy-dom doesn't ship one and
  `useTheme` reads it on mount).
- `msw/server.ts` + `msw/handlers.ts` — default happy-path handlers for
  `/auth/{me,login,register,logout}`. Each test overrides the specific
  endpoint(s) it wants to behave differently via `server.use(...)`.
- `utils/renderWithProviders.tsx` — RTL `render` plus a fresh
  `QueryClient` (retry: false, staleTime: 0) plus a `MemoryRouter`.
  Returns the `queryClient` so tests can inspect cache state.
  `makeHookWrapper` is the equivalent for `renderHook`.
- `utils/factories.ts` — tiny builders for API shapes. Currently just
  `makeUser(...)`. Grow as needed.

### Vitest config lives in `vite.config.ts`

We extend the existing Vite config with a `test:` block rather than
keep a separate `vitest.config.ts`. One source of truth for path
aliases and plugins, one fewer file to maintain. The `test:` block
is type-aware via `/// <reference types="vitest/config" />` at the
top of the file.

## Preview server caveat

`vite preview` serves the built bundle on a static server with **no
`/api` proxy**. To exercise the production bundle against the backend,
either serve `dist/` from the backend's static mount (Docker slice) or
sit a reverse proxy in front of both. The dev server (`npm run dev`)
proxies `/api → localhost:8045` automatically.
