import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderOptions, type RenderResult } from "@testing-library/react";
import { type ReactElement, type ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";

interface ProviderOptions extends Omit<RenderOptions, "wrapper"> {
  initialEntries?: string[];
  queryClient?: QueryClient;
}

export interface RenderWithProvidersResult extends RenderResult {
  queryClient: QueryClient;
}

function buildTestClient(): QueryClient {
  // retry: false + staleTime: 0 = deterministic test behavior. Anything
  // mocked-401 throws once; we don't want background retries delaying
  // the assertion.
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

/**
 * Render a UI tree wrapped in the same providers `main.tsx` does, plus a
 * MemoryRouter so route-aware components work without a real browser
 * history. Tests can inspect the QueryClient through the return value.
 */
export function renderWithProviders(
  ui: ReactElement,
  options: ProviderOptions = {},
): RenderWithProvidersResult {
  const { initialEntries = ["/"], queryClient = buildTestClient(), ...rest } = options;

  const Wrapper = ({ children }: { children: ReactNode }): JSX.Element => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
    </QueryClientProvider>
  );

  return { ...render(ui, { wrapper: Wrapper, ...rest }), queryClient };
}

/**
 * Bare-providers wrapper for `renderHook` from RTL. Hooks don't need a
 * router; they get a QueryClient.
 */
export function makeHookWrapper(queryClient: QueryClient = buildTestClient()) {
  function HookWrapper({ children }: { children: ReactNode }): JSX.Element {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  }
  return { HookWrapper, queryClient };
}
