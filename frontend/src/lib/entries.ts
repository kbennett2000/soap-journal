import { apiRequest } from "@/lib/api";
import type {
  EntryCreateRequest,
  EntryEnvelope,
  EntryListResponse,
  EntryResponse,
  EntryUpdateRequest,
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

interface ListEntriesParams {
  limit?: number;
  offset?: number;
  order?: "newest" | "oldest";
}

export async function listEntries(
  params: ListEntriesParams = {},
): Promise<EntryListResponse> {
  return apiRequest<EntryListResponse>("GET", "/entries", {
    query: {
      limit: params.limit,
      offset: params.offset,
      order: params.order,
    },
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
