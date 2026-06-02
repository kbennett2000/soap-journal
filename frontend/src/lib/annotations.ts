import { apiRequest } from "@/lib/api";
import type {
  Annotation,
  AnnotationCreate,
  AnnotationEnvelope,
  AnnotationListResponse,
} from "@/types/api";

/**
 * Thin wrappers around `apiRequest` for the annotation (highlight) endpoints.
 *
 * The backend wraps a single annotation in `{ annotation: ... }`; callers don't
 * benefit from the envelope so `createAnnotation` unwraps it. The list response
 * keeps its top-level `annotations` field.
 */

export interface ListAnnotationsParams {
  /** A translation code; highlights are scoped to (and hidden outside) it. */
  translation?: string;
  book?: string;
  chapter?: number;
}

export async function listAnnotations(
  params: ListAnnotationsParams = {},
): Promise<AnnotationListResponse> {
  return apiRequest<AnnotationListResponse>("GET", "/annotations", {
    query: {
      translation: params.translation,
      book: params.book,
      chapter: params.chapter,
    },
  });
}

export async function createAnnotation(body: AnnotationCreate): Promise<Annotation> {
  const res = await apiRequest<AnnotationEnvelope, AnnotationCreate>(
    "POST",
    "/annotations",
    { body },
  );
  return res.annotation;
}

export async function deleteAnnotation(annotationId: number): Promise<void> {
  await apiRequest<void>("DELETE", `/annotations/${annotationId}`);
}
