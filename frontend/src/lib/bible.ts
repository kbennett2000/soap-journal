import { apiRequest } from "@/lib/api";
import type {
  ChapterResponse,
  ResolvedReferenceResponse,
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
