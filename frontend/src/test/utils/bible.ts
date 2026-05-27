/**
 * Bible-related test data builders.
 *
 * `makeChapter` / `makeTranslationDetail` return shapes that look
 * like the backend responses without standing up the real database.
 * Tests override these per-case via `server.use(...)`.
 */

import type {
  BookSummary,
  ChapterResponse,
  TranslationDetailResponse,
  TranslationListResponse,
  TranslationSummary,
  VerseResponse,
} from "@/types/api";

export const BSB_TRANSLATION: TranslationSummary = {
  code: "BSB",
  name: "Berean Standard Bible",
  language: "en",
  copyright: "Public domain — test fixture.",
};

export const KJV_TRANSLATION: TranslationSummary = {
  code: "KJV",
  name: "King James Version",
  language: "en",
  copyright: "Public domain — test fixture.",
};

const BSB = BSB_TRANSLATION;

const JOHN_SUMMARY: BookSummary = {
  name: "John",
  abbreviation: "John",
  order_index: 43,
  testament: "NT",
  chapter_count: 21,
};

const GENESIS_SUMMARY: BookSummary = {
  name: "Genesis",
  abbreviation: "Gen",
  order_index: 1,
  testament: "OT",
  chapter_count: 50,
};

const PSALMS_SUMMARY: BookSummary = {
  name: "Psalms",
  abbreviation: "Ps",
  order_index: 19,
  testament: "OT",
  chapter_count: 150,
};

export const TEST_BOOKS: BookSummary[] = [GENESIS_SUMMARY, PSALMS_SUMMARY, JOHN_SUMMARY];

export function makeTranslationList(
  translations?: TranslationSummary[],
): TranslationListResponse {
  return { translations: translations ?? [BSB] };
}

export function makeTranslationDetail(
  overrides: Partial<TranslationDetailResponse> = {},
): TranslationDetailResponse {
  return {
    translation: BSB,
    books: TEST_BOOKS,
    ...overrides,
  };
}

export function makeVerse(overrides: Partial<VerseResponse> = {}): VerseResponse {
  return {
    id: 1,
    number: 1,
    text: "Sample verse text.",
    is_red_letter: false,
    footnotes: [],
    ...overrides,
  };
}

interface ChapterOverrides {
  translationCode?: string;
  bookName?: string;
  chapterNumber?: number;
  verses?: VerseResponse[];
  previous?: ChapterResponse["previous"];
  next?: ChapterResponse["next"];
  book?: BookSummary;
}

export function makeChapter(overrides: ChapterOverrides = {}): ChapterResponse {
  const book =
    overrides.book ??
    TEST_BOOKS.find((b) => b.name === overrides.bookName) ??
    JOHN_SUMMARY;
  // `null` is a valid value for previous/next — `??` would treat it as
  // "not provided" and fall back. Use `in` to distinguish "passed null"
  // (we want the null) from "absent" (use the default).
  const previous = "previous" in overrides
    ? overrides.previous ?? null
    : { book_name: "John", chapter_number: 2 };
  const next = "next" in overrides
    ? overrides.next ?? null
    : { book_name: "John", chapter_number: 4 };
  return {
    translation_code: overrides.translationCode ?? "BSB",
    book,
    chapter_number: overrides.chapterNumber ?? 3,
    verses:
      overrides.verses ?? [
        makeVerse({ id: 16, number: 16, text: "For God so loved the world." }),
        makeVerse({ id: 17, number: 17, text: "For God did not send His Son to condemn." }),
        makeVerse({ id: 18, number: 18, text: "Whoever believes in Him is not condemned." }),
      ],
    headings: [],
    previous,
    next,
  };
}
