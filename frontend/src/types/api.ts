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

/** Typed translator-note category; null for a plain footnote. */
export type NoteType = "tn" | "sn" | "tc" | "map";

export interface CrossRefResponse {
  to_book: string; // target book abbreviation (display label + navigable alias)
  to_chapter: number;
  to_verse_start: number;
  to_verse_end: number | null;
}

export interface FootnoteResponse {
  id: number;
  text: string;
  // Rich-note fields (ADR-0002). Plain footnotes (the bundled translations)
  // come back with note_type/char_offset/marker null, ordinal 0, cross_refs [].
  note_type: NoteType | null;
  char_offset: number | null;
  marker: number | null;
  ordinal: number;
  cross_refs: CrossRefResponse[];
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

// ---- Bible full-text search (ADR-0003) ------------------------------------

export type SearchScope = "verses" | "notes" | "both";

export interface VerseSearchHit {
  translation_code: string;
  book: string; // abbreviation (display + navigable)
  chapter: number;
  verse: number;
  snippet: string; // contains <mark>...</mark> around matched terms
  // In translation=ALL mode, the sorted list of translations that matched this
  // canonical verse; null in single-translation mode.
  translation_codes: string[] | null;
}

export interface NoteSearchHit {
  translation_code: string;
  book: string;
  chapter: number;
  verse: number;
  note_type: NoteType | null;
  snippet: string;
}

export interface SearchResponse {
  query: string;
  scope: SearchScope;
  translation_code: string; // searched code, or "ALL" for cross-translation search
  verse_hits: VerseSearchHit[];
  note_hits: NoteSearchHit[];
  total_verse_hits: number;
  total_note_hits: number;
  limit: number;
  offset: number;
}

// ---- Annotations / highlights (ADR-0005) ----------------------------------

/** The six highlight colors — mirrors the backend `HighlightColor` Literal. */
export type HighlightColor =
  | "yellow"
  | "green"
  | "blue"
  | "pink"
  | "orange"
  | "purple";

export interface Annotation {
  id: number;
  translation_code: string;
  book: string; // canonical book name
  chapter: number;
  verse_start: number;
  verse_end: number;
  char_start: number;
  char_end: number;
  color: HighlightColor;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface AnnotationCreate {
  translation_code: string;
  book: string;
  chapter: number;
  verse_start: number;
  verse_end: number;
  char_start: number;
  char_end: number;
  color: HighlightColor;
  note?: string | null;
}

/**
 * Partial update for an annotation (mirrors the backend `AnnotationUpdate`).
 * Only fields present are applied; `note: null` clears the note.
 */
export interface AnnotationUpdate {
  color?: HighlightColor;
  note?: string | null;
}

export interface AnnotationEnvelope {
  annotation: Annotation;
}

export interface AnnotationListResponse {
  annotations: Annotation[];
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

// ---- Admin ---------------------------------------------------------------

export interface AdminUserListResponse {
  users: UserResponse[];
}

export interface AdminCreateUserRequest {
  username: string;
  password: string;
  is_admin?: boolean;
}

export interface AdminResetPasswordRequest {
  new_password: string;
}

export interface SettingsView {
  open_registration: boolean;
}

export interface SettingsEnvelope {
  settings: SettingsView;
}
