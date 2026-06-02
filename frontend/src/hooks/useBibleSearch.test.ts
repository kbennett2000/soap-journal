import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { useBibleSearch } from "@/hooks/useBible";
import { server } from "@/test/msw/server";
import { makeSearchResponse } from "@/test/utils/bible";
import { makeHookWrapper } from "@/test/utils/renderWithProviders";

describe("useBibleSearch", () => {
  it("returns verse and note hits from /bible/search", async () => {
    const { HookWrapper } = makeHookWrapper();
    const { result } = renderHook(
      () => useBibleSearch({ q: "loved", translation: "BSB" }),
      { wrapper: HookWrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const data = result.current.data;
    if (!data) throw new Error("expected search data");
    expect(data.verse_hits).toHaveLength(1);
    expect(data.verse_hits[0]?.snippet).toContain("<mark>");
    expect(data.note_hits[0]?.note_type).toBe("tn");
  });

  it("stays disabled (no fetch) for a blank query", async () => {
    server.use(
      http.get("/api/v1/bible/search", () => {
        throw new Error("search must not be called for a blank query");
      }),
    );
    const { HookWrapper } = makeHookWrapper();
    const { result } = renderHook(() => useBibleSearch({ q: "   " }), {
      wrapper: HookWrapper,
    });

    // enabled:false → never fetches; query is idle/pending with no data.
    expect(result.current.fetchStatus).toBe("idle");
    expect(result.current.data).toBeUndefined();
  });

  it("passes scope and translation through to the request", async () => {
    let seen: URL | null = null;
    server.use(
      http.get("/api/v1/bible/search", ({ request }) => {
        seen = new URL(request.url);
        return HttpResponse.json(
          makeSearchResponse({ scope: "notes", translation_code: "ALL" }),
          { status: 200 },
        );
      }),
    );
    const { HookWrapper } = makeHookWrapper();
    const { result } = renderHook(
      () => useBibleSearch({ q: "hebrew", translation: "ALL", scope: "notes" }),
      { wrapper: HookWrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    if (!seen) throw new Error("search endpoint was not called");
    const seenUrl = seen as URL;
    expect(seenUrl.searchParams.get("q")).toBe("hebrew");
    expect(seenUrl.searchParams.get("translation")).toBe("ALL");
    expect(seenUrl.searchParams.get("scope")).toBe("notes");
    expect(result.current.data?.translation_code).toBe("ALL");
  });
});
