import { apiRequest } from "@/lib/api";
import type {
  CalendarResponse,
  EntryCreateRequest,
  EntryEnvelope,
  EntryListResponse,
  EntryResponse,
  EntryUpdateRequest,
  OnThisDayResponse,
  TagAutocompleteResponse,
  TagListResponse,
} from "@/types/api";

/**
 * Thin wrappers around `apiRequest` for the entry + tag endpoints.
 *
 * The backend wraps single entries in `{ entry: ... }`; callers don't
 * benefit from the envelope so we unwrap here. List + tag responses
 * have meaningful top-level fields (`total`, `applied_filters`,
 * `entry_count`) so those pass through as-is.
 */

export interface ListEntriesParams {
  limit?: number;
  offset?: number;
  order?: "newest" | "oldest";
  q?: string;
  book?: string;
  tag?: string;
  from_date?: string; // YYYY-MM-DD
  to_date?: string;
}

export async function listEntries(
  params: ListEntriesParams = {},
): Promise<EntryListResponse> {
  return apiRequest<EntryListResponse>("GET", "/entries", {
    query: {
      limit: params.limit,
      offset: params.offset,
      order: params.order,
      q: params.q,
      book: params.book,
      tag: params.tag,
      from_date: params.from_date,
      to_date: params.to_date,
    },
  });
}

export async function getCalendar(
  year: number,
  month: number,
): Promise<CalendarResponse> {
  return apiRequest<CalendarResponse>("GET", "/entries/calendar", {
    query: { year, month },
  });
}

export async function getOnThisDay(
  date?: string,
  yearsBack?: number,
): Promise<OnThisDayResponse> {
  return apiRequest<OnThisDayResponse>("GET", "/entries/on-this-day", {
    query: { date, years_back: yearsBack },
  });
}

export async function getEntry(entryId: number): Promise<EntryResponse> {
  const envelope = await apiRequest<EntryEnvelope>("GET", `/entries/${entryId}`);
  return envelope.entry;
}

export async function createEntry(body: EntryCreateRequest): Promise<EntryResponse> {
  const envelope = await apiRequest<EntryEnvelope, EntryCreateRequest>(
    "POST",
    "/entries",
    { body },
  );
  return envelope.entry;
}

export async function updateEntry(
  entryId: number,
  body: EntryUpdateRequest,
): Promise<EntryResponse> {
  const envelope = await apiRequest<EntryEnvelope, EntryUpdateRequest>(
    "PUT",
    `/entries/${entryId}`,
    { body },
  );
  return envelope.entry;
}

export async function deleteEntry(entryId: number): Promise<void> {
  await apiRequest<void>("DELETE", `/entries/${entryId}`);
}

export async function listTags(): Promise<TagListResponse> {
  return apiRequest<TagListResponse>("GET", "/tags");
}

export async function autocompleteTags(q: string): Promise<TagAutocompleteResponse> {
  return apiRequest<TagAutocompleteResponse>("GET", "/tags/autocomplete", {
    query: { q },
  });
}
