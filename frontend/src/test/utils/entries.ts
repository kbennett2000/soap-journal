/**
 * Test data builders for entries + tags. Tiny defaults; per-test
 * overrides via the partial-overrides arg.
 */

import type {
  EntryEnvelope,
  EntryListResponse,
  EntryResponse,
  EntryTagSummary,
  TagListResponse,
  TagSummary,
} from "@/types/api";

let _entryId = 100;
let _tagId = 200;

export function nextEntryId(): number {
  _entryId += 1;
  return _entryId;
}

export function nextTagId(): number {
  _tagId += 1;
  return _tagId;
}

export function makeEntryTag(overrides: Partial<EntryTagSummary> = {}): EntryTagSummary {
  return {
    id: nextTagId(),
    name: "faith",
    ...overrides,
  };
}

export function makeEntry(overrides: Partial<EntryResponse> = {}): EntryResponse {
  const id = overrides.id ?? nextEntryId();
  return {
    id,
    title: null,
    display_title: "John 3:16",
    entry_date: "2026-05-27",
    scripture_ref: "John 3:16",
    translation_code: "BSB",
    scripture_text: "For God so loved the world.",
    observation: "",
    application: "",
    prayer: "",
    tags: [],
    created_at: "2026-05-27T00:00:00Z",
    updated_at: "2026-05-27T00:00:00Z",
    ...overrides,
  };
}

export function makeEntryEnvelope(
  overrides: Partial<EntryResponse> = {},
): EntryEnvelope {
  return { entry: makeEntry(overrides) };
}

export function makeEntryList(
  entries: EntryResponse[] = [makeEntry()],
  pagination: Partial<Omit<EntryListResponse, "entries" | "applied_filters">> = {},
): EntryListResponse {
  return {
    entries,
    total: pagination.total ?? entries.length,
    limit: pagination.limit ?? 20,
    offset: pagination.offset ?? 0,
    applied_filters: {
      q: null,
      book: null,
      tag: null,
      from_date: null,
      to_date: null,
    },
  };
}

export function makeTagSummary(overrides: Partial<TagSummary> = {}): TagSummary {
  return {
    id: nextTagId(),
    name: "faith",
    entry_count: 1,
    ...overrides,
  };
}

export function makeTagList(tags: TagSummary[] = []): TagListResponse {
  return { tags };
}
