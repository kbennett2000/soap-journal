import { apiRequest } from "@/lib/api";
import type {
  ChapterResponse,
  PassageEntriesResponse,
  ResolvedReferenceResponse,
  SearchResponse,
  SearchScope,
  TranslationDetailResponse,
  TranslationListResponse,
} from "@/types/api";

/**
 * Thin wrappers around `apiRequest` for the Bible reader endpoints.
 * Centralizes path construction so callers can't drift on URL shape.
 */

export async function listTranslations(): Promise<TranslationListResponse> {
  return apiRequest<TranslationListResponse>("GET", "/bible/translations");
}

export async function getTranslationDetail(
  code: string,
): Promise<TranslationDetailResponse> {
  return apiRequest<TranslationDetailResponse>(
    "GET",
    `/bible/translations/${encodeURIComponent(code)}`,
  );
}

export async function getChapter(
  code: string,
  bookName: string,
  chapterNumber: number,
): Promise<ChapterResponse> {
  return apiRequest<ChapterResponse>(
    "GET",
    `/bible/translations/${encodeURIComponent(code)}` +
      `/books/${encodeURIComponent(bookName)}` +
      `/chapters/${chapterNumber}`,
  );
}

export async function resolveReference(
  ref: string,
  translationCode?: string,
): Promise<ResolvedReferenceResponse> {
  return apiRequest<ResolvedReferenceResponse>("GET", "/bible/resolve", {
    query: { ref, translation: translationCode },
  });
}

export async function getPassageEntries(
  ref: string,
  translationCode?: string,
): Promise<PassageEntriesResponse> {
  return apiRequest<PassageEntriesResponse>("GET", "/bible/passages/entries", {
    query: { ref, translation: translationCode },
  });
}

export interface SearchBibleParams {
  q: string;
  /** A translation code, or "ALL" for grouped cross-translation search. */
  translation?: string;
  scope?: SearchScope;
  limit?: number;
  offset?: number;
}

export async function searchBible(params: SearchBibleParams): Promise<SearchResponse> {
  return apiRequest<SearchResponse>("GET", "/bible/search", {
    query: {
      q: params.q,
      translation: params.translation,
      scope: params.scope,
      limit: params.limit,
      offset: params.offset,
    },
  });
}
