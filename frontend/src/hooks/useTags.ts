import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { autocompleteTags, listTags } from "@/lib/entries";
import type { TagAutocompleteResponse, TagListResponse } from "@/types/api";

export function useTagList(): UseQueryResult<TagListResponse> {
  return useQuery({
    queryKey: ["tags", "list"] as const,
    queryFn: listTags,
  });
}

export function useTagAutocomplete(
  q: string,
): UseQueryResult<TagAutocompleteResponse> {
  const trimmed = q.trim();
  return useQuery({
    queryKey: ["tags", "autocomplete", trimmed] as const,
    queryFn: () => autocompleteTags(trimmed),
    enabled: trimmed.length > 0,
    staleTime: 30_000,
  });
}
