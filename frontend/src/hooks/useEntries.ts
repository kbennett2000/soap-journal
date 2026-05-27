import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";

import {
  createEntry,
  deleteEntry,
  getCalendar,
  getEntry,
  getOnThisDay,
  listEntries,
  updateEntry,
  type ListEntriesParams,
} from "@/lib/entries";
import type {
  CalendarResponse,
  EntryCreateRequest,
  EntryListResponse,
  EntryResponse,
  EntryUpdateRequest,
  OnThisDayResponse,
} from "@/types/api";

/**
 * Build a stable filter key for the list query. TanStack Query already
 * does structural equality on query keys, so a plain object works — but
 * normalizing here lets us strip undefined fields and skip empty
 * strings so identical filter shapes don't accidentally produce
 * different keys.
 */
function normalizeListFilters(options: ListEntriesParams): ListEntriesParams {
  const out: ListEntriesParams = {};
  if (options.limit !== undefined) out.limit = options.limit;
  if (options.offset !== undefined && options.offset !== 0) out.offset = options.offset;
  if (options.order && options.order !== "newest") out.order = options.order;
  if (options.q && options.q.trim().length > 0) out.q = options.q.trim();
  if (options.book) out.book = options.book;
  if (options.tag) out.tag = options.tag;
  if (options.from_date) out.from_date = options.from_date;
  if (options.to_date) out.to_date = options.to_date;
  return out;
}

export function useEntryList(
  options: ListEntriesParams = {},
): UseQueryResult<EntryListResponse> {
  const normalized = normalizeListFilters(options);
  return useQuery({
    queryKey: ["entries", "list", normalized] as const,
    queryFn: () => listEntries(normalized),
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

export function useCalendar(
  year: number,
  month: number,
): UseQueryResult<CalendarResponse> {
  return useQuery({
    queryKey: ["entries", "calendar", year, month] as const,
    queryFn: () => getCalendar(year, month),
    staleTime: 60_000,
  });
}

export function useOnThisDay(
  date?: string,
  yearsBack?: number,
): UseQueryResult<OnThisDayResponse> {
  return useQuery({
    queryKey: ["entries", "onThisDay", date ?? null, yearsBack ?? null] as const,
    queryFn: () => getOnThisDay(date, yearsBack),
    staleTime: 60_000,
  });
}

function invalidateAllEntryViews(
  qc: ReturnType<typeof useQueryClient>,
): Promise<void> {
  return Promise.all([
    qc.invalidateQueries({ queryKey: ["entries", "list"] }),
    qc.invalidateQueries({ queryKey: ["entries", "calendar"] }),
    qc.invalidateQueries({ queryKey: ["entries", "onThisDay"] }),
    qc.invalidateQueries({ queryKey: ["bible", "passageEntries"] }),
    qc.invalidateQueries({ queryKey: ["tags", "list"] }),
  ]).then(() => undefined);
}

export function useCreateEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: EntryCreateRequest) => createEntry(body),
    onSuccess: async () => {
      await invalidateAllEntryViews(qc);
    },
  });
}

export function useUpdateEntry(entryId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: EntryUpdateRequest) => updateEntry(entryId, body),
    onSuccess: async () => {
      await Promise.all([
        invalidateAllEntryViews(qc),
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
      await invalidateAllEntryViews(qc);
    },
  });
}
