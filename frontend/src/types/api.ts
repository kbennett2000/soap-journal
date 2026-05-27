/**
 * Shapes mirroring backend response/request types.
 *
 * Kept narrow on purpose — only what the scaffolded flows actually use.
 * Future feature work will extend these alongside their endpoints.
 */

export interface UserResponse {
  id: number;
  username: string;
  is_admin: boolean;
  created_at: string;
}

export interface AuthEnvelope {
  user: UserResponse;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  password: string;
}

/** Shape of the `detail` payload on a structured error response. */
export interface ApiErrorDetail {
  code: string;
  message: string;
}

// ---- Bible reader ---------------------------------------------------------

export type Testament = "OT" | "NT";

export interface TranslationSummary {
  code: string;
  name: string;
  language: string;
  copyright: string;
}

export interface TranslationListResponse {
  translations: TranslationSummary[];
}

export interface BookSummary {
  name: string;
  abbreviation: string;
  order_index: number;
  testament: Testament;
  chapter_count: number;
}

export interface TranslationDetailResponse {
  translation: TranslationSummary;
  books: BookSummary[];
}

export interface FootnoteResponse {
  id: number;
  text: string;
}

export interface VerseResponse {
  id: number;
  number: number;
  text: string;
  is_red_letter: boolean;
  footnotes: FootnoteResponse[];
}

export interface HeadingResponse {
  before_verse: number;
  text: string;
}

export interface ChapterPointer {
  book_name: string;
  chapter_number: number;
}

export interface ChapterResponse {
  translation_code: string;
  book: BookSummary;
  chapter_number: number;
  verses: VerseResponse[];
  headings: HeadingResponse[];
  previous: ChapterPointer | null;
  next: ChapterPointer | null;
}

export interface ResolvedReference {
  canonical_string: string;
  translation_code: string;
  book: BookSummary;
  chapter_number: number;
  start_verse: number;
  end_verse: number;
}

export interface ResolvedReferenceResponse {
  reference: ResolvedReference;
  verses: VerseResponse[];
}

// ---- Entries + tags -------------------------------------------------------

export interface EntryTagSummary {
  id: number;
  name: string;
}

export interface EntryResponse {
  id: number;
  title: string | null;
  display_title: string;
  entry_date: string; // ISO YYYY-MM-DD
  scripture_ref: string;
  translation_code: string;
  scripture_text: string;
  observation: string;
  application: string;
  prayer: string;
  tags: EntryTagSummary[];
  created_at: string;
  updated_at: string;
}

export interface EntryEnvelope {
  entry: EntryResponse;
}

export interface AppliedFilters {
  q: string | null;
  book: string | null;
  tag: string | null;
  from_date: string | null;
  to_date: string | null;
}

export interface EntryListResponse {
  entries: EntryResponse[];
  total: number;
  limit: number;
  offset: number;
  applied_filters: AppliedFilters;
}

export interface EntryCreateRequest {
  title?: string | null;
  entry_date?: string | null; // ISO YYYY-MM-DD
  scripture_ref: string;
  translation_code?: string | null;
  observation?: string;
  application?: string;
  prayer?: string;
  tags?: string[];
}

export type EntryUpdateRequest = EntryCreateRequest;

export interface TagSummary {
  id: number;
  name: string;
  entry_count: number;
}

export interface TagListResponse {
  tags: TagSummary[];
}

export interface TagAutocompleteResponse {
  tags: TagSummary[];
}

// ---- Retrieval: calendar, on-this-day, passage cross-references -----------

export interface CalendarDay {
  entry_date: string; // ISO YYYY-MM-DD
  count: number;
}

export interface CalendarResponse {
  year: number;
  month: number;
  days: CalendarDay[];
  total: number;
}

export interface OnThisDayResponse {
  target_date: string;
  entries: EntryResponse[];
}

export interface PassageEntriesResponse {
  reference: ResolvedReference;
  count: number;
  entries: EntryResponse[];
}
