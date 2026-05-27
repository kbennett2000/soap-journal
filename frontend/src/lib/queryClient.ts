import { QueryClient } from "@tanstack/react-query";

/**
 * Shared TanStack Query client.
 *
 * `staleTime: 30_000` — almost everything we read is "fresh enough" for
 * half a minute, which avoids refetch-on-focus pinging the backend for
 * trivial reasons.
 * `retry: 1` for queries, `retry: false` for mutations — mutations
 * surface their failures so the user can react.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
});
