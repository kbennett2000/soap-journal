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
