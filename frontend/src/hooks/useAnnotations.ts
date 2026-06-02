import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";

import {
  createAnnotation,
  deleteAnnotation,
  listAnnotations,
} from "@/lib/annotations";
import type { AnnotationCreate, AnnotationListResponse } from "@/types/api";

/**
 * TanStack Query hooks for the reader's per-chapter highlights.
 *
 * The list query is keyed by (translation, book, chapter) so each chapter
 * fetches only its own annotations; create/delete invalidate the whole
 * `["annotations","list"]` subtree so the active chapter re-renders.
 */

interface UseAnnotationsParams {
  translation?: string;
  book?: string;
  chapter?: number;
}

export function useAnnotations(
  params: UseAnnotationsParams,
): UseQueryResult<AnnotationListResponse> {
  const { translation, book, chapter } = params;
  return useQuery({
    queryKey: [
      "annotations",
      "list",
      translation ?? null,
      book ?? null,
      chapter ?? null,
    ] as const,
    queryFn: () => listAnnotations({ translation, book, chapter }),
    enabled:
      typeof translation === "string" &&
      typeof book === "string" &&
      typeof chapter === "number" &&
      chapter >= 1,
  });
}

export function useCreateAnnotation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AnnotationCreate) => createAnnotation(body),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["annotations", "list"] });
    },
  });
}

export function useDeleteAnnotation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (annotationId: number) => deleteAnnotation(annotationId),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["annotations", "list"] });
    },
  });
}
