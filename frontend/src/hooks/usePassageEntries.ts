import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { getPassageEntries } from "@/lib/bible";
import type { PassageEntriesResponse } from "@/types/api";

/**
 * Used by the reader to surface "you have N entries on this passage."
 * The hook keys on (ref, translationCode) so every chapter / range gets
 * its own cache slot. Invalidated on every entry mutation
 * (see useEntries `invalidateAllEntryViews`).
 */
export function usePassageEntries(
  ref: string | undefined,
  translationCode: string | undefined,
): UseQueryResult<PassageEntriesResponse> {
  const trimmed = (ref ?? "").trim();
  return useQuery({
    queryKey: ["bible", "passageEntries", trimmed, translationCode ?? null] as const,
    queryFn: () => getPassageEntries(trimmed, translationCode),
    enabled: trimmed.length > 0,
    staleTime: 30_000,
    retry: false,
  });
}
