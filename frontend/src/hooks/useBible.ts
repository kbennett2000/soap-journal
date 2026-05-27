import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import {
  getChapter,
  getTranslationDetail,
  listTranslations,
} from "@/lib/bible";
import type {
  ChapterResponse,
  TranslationDetailResponse,
  TranslationListResponse,
} from "@/types/api";

/**
 * TanStack Query hooks for the reader's read-paths.
 *
 * Bible content doesn't change between page loads, so chapter and
 * translation-detail queries use `staleTime: Infinity`. The translation
 * list is essentially fixed for the life of an install but uses a 5-min
 * stale time in case an admin loads a second translation while the
 * user is browsing.
 */

const FIVE_MIN = 5 * 60 * 1_000;

export function useTranslations(): UseQueryResult<TranslationListResponse> {
  return useQuery({
    queryKey: ["bible", "translations"] as const,
    queryFn: listTranslations,
    staleTime: FIVE_MIN,
  });
}

export function useTranslationDetail(
  code: string | undefined,
): UseQueryResult<TranslationDetailResponse> {
  return useQuery({
    queryKey: ["bible", "translation", code] as const,
    queryFn: () => getTranslationDetail(code as string),
    enabled: typeof code === "string" && code.length > 0,
    staleTime: Infinity,
  });
}

export function useChapter(
  code: string | undefined,
  bookName: string | undefined,
  chapterNumber: number | undefined,
): UseQueryResult<ChapterResponse> {
  return useQuery({
    queryKey: ["bible", "chapter", code, bookName, chapterNumber] as const,
    queryFn: () =>
      getChapter(code as string, bookName as string, chapterNumber as number),
    enabled:
      typeof code === "string" &&
      typeof bookName === "string" &&
      typeof chapterNumber === "number" &&
      chapterNumber >= 1,
    staleTime: Infinity,
  });
}
