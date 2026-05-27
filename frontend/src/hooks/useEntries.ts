import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";

import {
  createEntry,
  deleteEntry,
  getEntry,
  listEntries,
  updateEntry,
} from "@/lib/entries";
import type {
  EntryCreateRequest,
  EntryListResponse,
  EntryResponse,
  EntryUpdateRequest,
} from "@/types/api";

type ListOptions = {
  limit?: number;
  offset?: number;
  order?: "newest" | "oldest";
};

export function useEntryList(
  options: ListOptions = {},
): UseQueryResult<EntryListResponse> {
  return useQuery({
    queryKey: ["entries", "list", options] as const,
    queryFn: () => listEntries(options),
  });
}

export function useEntry(
  entryId: number | undefined,
): UseQueryResult<EntryResponse> {
  return useQuery({
    queryKey: ["entries", "detail", entryId] as const,
    queryFn: () => getEntry(entryId as number),
    enabled: typeof entryId === "number" && Number.isFinite(entryId),
  });
}

function invalidateLists(qc: ReturnType<typeof useQueryClient>): Promise<void> {
  return Promise.all([
    qc.invalidateQueries({ queryKey: ["entries", "list"] }),
    qc.invalidateQueries({ queryKey: ["tags", "list"] }),
  ]).then(() => undefined);
}

export function useCreateEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: EntryCreateRequest) => createEntry(body),
    onSuccess: async () => {
      await invalidateLists(qc);
    },
  });
}

export function useUpdateEntry(entryId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: EntryUpdateRequest) => updateEntry(entryId, body),
    onSuccess: async () => {
      await Promise.all([
        invalidateLists(qc),
        qc.invalidateQueries({ queryKey: ["entries", "detail", entryId] }),
      ]);
    },
  });
}

export function useDeleteEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (entryId: number) => deleteEntry(entryId),
    onSuccess: async () => {
      await invalidateLists(qc);
    },
  });
}
