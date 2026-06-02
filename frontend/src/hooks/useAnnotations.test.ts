import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import {
  useAnnotations,
  useCreateAnnotation,
  useDeleteAnnotation,
  useUpdateAnnotation,
} from "@/hooks/useAnnotations";
import { server } from "@/test/msw/server";
import { makeAnnotation } from "@/test/utils/bible";
import { makeHookWrapper } from "@/test/utils/renderWithProviders";
import type { AnnotationCreate, AnnotationUpdate } from "@/types/api";

describe("useAnnotations", () => {
  it("lists annotations for a chapter and scopes the request to it", async () => {
    let seen: URL | null = null;
    server.use(
      http.get("/api/v1/annotations", ({ request }) => {
        seen = new URL(request.url);
        return HttpResponse.json(
          { annotations: [makeAnnotation({ id: 7, color: "green" })] },
          { status: 200 },
        );
      }),
    );
    const { HookWrapper } = makeHookWrapper();
    const { result } = renderHook(
      () => useAnnotations({ translation: "NET", book: "John", chapter: 3 }),
      { wrapper: HookWrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const data = result.current.data;
    if (!data) throw new Error("expected annotation data");
    expect(data.annotations).toHaveLength(1);
    expect(data.annotations[0]?.color).toBe("green");
    if (!seen) throw new Error("annotations endpoint was not called");
    const url = seen as URL;
    expect(url.searchParams.get("translation")).toBe("NET");
    expect(url.searchParams.get("book")).toBe("John");
    expect(url.searchParams.get("chapter")).toBe("3");
  });

  it("stays disabled (no fetch) until translation/book/chapter are all set", () => {
    server.use(
      http.get("/api/v1/annotations", () => {
        throw new Error("must not fetch with incomplete params");
      }),
    );
    const { HookWrapper } = makeHookWrapper();
    const { result } = renderHook(
      () => useAnnotations({ translation: "NET", book: "John" }),
      { wrapper: HookWrapper },
    );
    expect(result.current.fetchStatus).toBe("idle");
    expect(result.current.data).toBeUndefined();
  });

  it("createAnnotation POSTs the body and resolves the created row", async () => {
    let posted: AnnotationCreate | null = null;
    server.use(
      http.post("/api/v1/annotations", async ({ request }) => {
        posted = (await request.json()) as AnnotationCreate;
        return HttpResponse.json(
          { annotation: makeAnnotation({ ...posted, id: 123 }) },
          { status: 201 },
        );
      }),
    );
    const { HookWrapper } = makeHookWrapper();
    const { result } = renderHook(() => useCreateAnnotation(), {
      wrapper: HookWrapper,
    });

    const body: AnnotationCreate = {
      translation_code: "NET",
      book: "John",
      chapter: 3,
      verse_start: 16,
      verse_end: 16,
      char_start: 0,
      char_end: 5,
      color: "blue",
    };
    const created = await result.current.mutateAsync(body);
    expect(created.id).toBe(123);
    if (!posted) throw new Error("create endpoint was not called");
    expect((posted as AnnotationCreate).color).toBe("blue");
  });

  it("updateAnnotation PATCHes a color change and resolves the updated row", async () => {
    let patched: { id: string; body: AnnotationUpdate } | null = null;
    server.use(
      http.patch("/api/v1/annotations/:annotationId", async ({ params, request }) => {
        patched = {
          id: String(params.annotationId),
          body: (await request.json()) as AnnotationUpdate,
        };
        return HttpResponse.json(
          { annotation: makeAnnotation({ id: 42, color: "green" }) },
          { status: 200 },
        );
      }),
    );
    const { HookWrapper } = makeHookWrapper();
    const { result } = renderHook(() => useUpdateAnnotation(), {
      wrapper: HookWrapper,
    });

    const updated = await result.current.mutateAsync({
      annotationId: 42,
      body: { color: "green" },
    });
    expect(updated.color).toBe("green");
    if (!patched) throw new Error("PATCH was not called");
    const seen = patched as { id: string; body: AnnotationUpdate };
    expect(seen.id).toBe("42");
    expect(seen.body).toEqual({ color: "green" });
  });

  it("updateAnnotation PATCHes a note, and note:null clears it", async () => {
    const bodies: AnnotationUpdate[] = [];
    server.use(
      http.patch("/api/v1/annotations/:annotationId", async ({ request }) => {
        const body = (await request.json()) as AnnotationUpdate;
        bodies.push(body);
        return HttpResponse.json(
          { annotation: makeAnnotation({ id: 7, note: body.note ?? null }) },
          { status: 200 },
        );
      }),
    );
    const { HookWrapper } = makeHookWrapper();
    const { result } = renderHook(() => useUpdateAnnotation(), {
      wrapper: HookWrapper,
    });

    const set = await result.current.mutateAsync({
      annotationId: 7,
      body: { note: "a thought" },
    });
    expect(set.note).toBe("a thought");

    const cleared = await result.current.mutateAsync({
      annotationId: 7,
      body: { note: null },
    });
    expect(cleared.note).toBeNull();

    expect(bodies).toEqual([{ note: "a thought" }, { note: null }]);
  });

  it("deleteAnnotation issues a DELETE for the id", async () => {
    let deletedId: string | null = null;
    server.use(
      http.delete("/api/v1/annotations/:annotationId", ({ params }) => {
        deletedId = String(params.annotationId);
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { HookWrapper } = makeHookWrapper();
    const { result } = renderHook(() => useDeleteAnnotation(), {
      wrapper: HookWrapper,
    });

    await result.current.mutateAsync(55);
    expect(deletedId).toBe("55");
  });
});
