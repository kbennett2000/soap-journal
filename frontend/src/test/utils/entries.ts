/**
 * Test data builders for entries + tags. Tiny defaults; per-test
 * overrides via the partial-overrides arg.
 */

import type {
  AppliedFilters,
  CalendarDay,
  CalendarResponse,
  EntryEnvelope,
  EntryListResponse,
  EntryResponse,
  EntryTagSummary,
  OnThisDayResponse,
  PassageEntriesResponse,
  ResolvedReference,
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
  appliedFilters: Partial<AppliedFilters> = {},
): EntryListResponse {
  return {
    entries,
    total: pagination.total ?? entries.length,
    limit: pagination.limit ?? 20,
    offset: pagination.offset ?? 0,
    applied_filters: {
      q: appliedFilters.q ?? null,
      book: appliedFilters.book ?? null,
      tag: appliedFilters.tag ?? null,
      from_date: appliedFilters.from_date ?? null,
      to_date: appliedFilters.to_date ?? null,
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

export function makeCalendarResponse(
  overrides: { year?: number; month?: number; days?: CalendarDay[] } = {},
): CalendarResponse {
  const year = overrides.year ?? 2026;
  const month = overrides.month ?? 5;
  const days = overrides.days ?? [];
  const total = days.reduce((sum, d) => sum + d.count, 0);
  return { year, month, days, total };
}

export function makeOnThisDayResponse(
  entries: EntryResponse[] = [],
  target_date = "2026-05-27",
): OnThisDayResponse {
  return { target_date, entries };
}

const DEFAULT_PASSAGE_REF: ResolvedReference = {
  canonical_string: "John 3",
  translation_code: "BSB",
  book: {
    name: "John",
    abbreviation: "John",
    order_index: 43,
    testament: "NT",
    chapter_count: 21,
  },
  chapter_number: 3,
  start_verse: 1,
  end_verse: 36,
};

export function makePassageEntriesResponse(
  entries: EntryResponse[] = [],
  reference: ResolvedReference = DEFAULT_PASSAGE_REF,
): PassageEntriesResponse {
  return { reference, count: entries.length, entries };
}
