import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router-dom";

import { ReaderPage } from "@/routes/ReaderPage";
import { server } from "@/test/msw/server";
import { makeAnnotation } from "@/test/utils/bible";
import { renderWithProviders } from "@/test/utils/renderWithProviders";
import type { Annotation, AnnotationUpdate } from "@/types/api";

/**
 * Integration tests for the 5c-3 annotation panel wired into ReaderPage:
 * click a highlight → AnnotationPanel → color PATCH / note / Delete, against a
 * STATEFUL MSW backend so a delete/recolor actually round-trips to a re-render.
 */

function installAnnotationStore(initial: Annotation[]): void {
  let store = [...initial];
  server.use(
    http.get("/api/v1/annotations", () =>
      HttpResponse.json({ annotations: store }, { status: 200 }),
    ),
    http.patch("/api/v1/annotations/:id", async ({ params, request }) => {
      const id = Number(params.id);
      const body = (await request.json()) as AnnotationUpdate;
      store = store.map((a) => (a.id === id ? { ...a, ...body } : a));
      const updated = store.find((a) => a.id === id);
      return HttpResponse.json({ annotation: updated }, { status: 200 });
    }),
    http.delete("/api/v1/annotations/:id", ({ params }) => {
      const id = Number(params.id);
      store = store.filter((a) => a.id !== id);
      return new HttpResponse(null, { status: 204 });
    }),
  );
}

function renderReader() {
  return renderWithProviders(
    <Routes>
      <Route
        path="/read/:translationCode/:bookName/:chapterNumber"
        element={<ReaderPage />}
      />
    </Routes>,
    { initialEntries: ["/read/BSB/John/3"] },
  );
}

function bsbAnnotation(overrides: Partial<Annotation>): Annotation {
  return makeAnnotation({
    translation_code: "BSB",
    book: "John",
    chapter: 3,
    verse_start: 16,
    verse_end: 16,
    ...overrides,
  });
}

function highlightSpan(id: number): HTMLElement | null {
  return document.querySelector<HTMLElement>(
    `[data-text-segment][data-highlight-id="${id}"]`,
  );
}

describe("ReaderPage — annotation panel (5c-3)", () => {
  it("clicking a highlight opens the panel; Delete removes it (no note → immediate) and the span disappears", async () => {
    installAnnotationStore([
      bsbAnnotation({ id: 5, char_start: 0, char_end: 7, color: "yellow", note: null }),
    ]);
    renderReader();

    await screen.findByTestId("verse-16");
    await waitFor(() => expect(highlightSpan(5)).toBeInTheDocument());

    fireEvent.mouseUp(highlightSpan(5)!);
    const panel = await screen.findByTestId("annotation-panel");

    fireEvent.click(within(panel).getByRole("button", { name: "Delete annotation" }));

    await waitFor(() => expect(highlightSpan(5)).not.toBeInTheDocument());
    expect(screen.queryByTestId("annotation-panel")).not.toBeInTheDocument();
  });

  it("changing the color in the panel PATCHes and re-renders the span in the new color", async () => {
    installAnnotationStore([
      bsbAnnotation({ id: 5, char_start: 0, char_end: 7, color: "yellow", note: null }),
    ]);
    renderReader();

    await screen.findByTestId("verse-16");
    await waitFor(() => expect(highlightSpan(5)).toBeInTheDocument());
    expect(highlightSpan(5)!.style.backgroundColor).toBe("var(--hl-yellow)");

    fireEvent.mouseUp(highlightSpan(5)!);
    const panel = await screen.findByTestId("annotation-panel");
    fireEvent.click(within(panel).getByLabelText("Set color Green"));

    await waitFor(() =>
      expect(highlightSpan(5)!.style.backgroundColor).toBe("var(--hl-green)"),
    );
  });

  it("from a stacked run, the chooser lets you delete the one UNDERNEATH the top", async () => {
    // id 1 [0,12] yellow (bottom), id 2 [6,20] green (top). Overlap run [6,12].
    installAnnotationStore([
      bsbAnnotation({ id: 1, char_start: 0, char_end: 12, color: "yellow", note: null }),
      bsbAnnotation({ id: 2, char_start: 6, char_end: 20, color: "green", note: null }),
    ]);
    renderReader();

    await screen.findByTestId("verse-16");
    const badge = await waitFor(() => {
      const b = document.querySelector<HTMLElement>('[data-testid="highlight-stack-badge"]');
      if (!b) throw new Error("no stack badge yet");
      return b;
    });

    fireEvent.mouseUp(badge);
    const panel = await screen.findByTestId("annotation-panel");

    // Chooser is newest-first → row 0 = id 2 (active top), row 1 = id 1.
    const rows = within(panel).getAllByTestId("stack-row");
    expect(rows).toHaveLength(2);
    fireEvent.click(rows[1]!); // select the bottom one (id 1)

    fireEvent.click(within(panel).getByRole("button", { name: "Delete annotation" }));

    // id 1 is gone; id 2 (the former top) remains.
    await waitFor(() => expect(highlightSpan(1)).not.toBeInTheDocument());
    expect(highlightSpan(2)).toBeInTheDocument();
    // No overlap remains → no badge.
    expect(
      document.querySelector('[data-testid="highlight-stack-badge"]'),
    ).toBeNull();
  });

  it("deletes a whole multi-verse highlight from the panel (opened via a covered span)", async () => {
    installAnnotationStore([
      bsbAnnotation({
        id: 8,
        verse_start: 16,
        char_start: 8,
        verse_end: 18,
        char_end: 8,
        color: "blue",
        note: null,
      }),
    ]);
    renderReader();

    await screen.findByTestId("verse-16");
    // The annotation paints across verses 16, 17, 18 — open it from the MIDDLE.
    const spanV17 = await waitFor(() => {
      const el = document.querySelector<HTMLElement>(
        '[data-testid="verse-17"] [data-text-segment][data-highlight-id="8"]',
      );
      if (!el) throw new Error("multi-verse span not rendered yet");
      return el;
    });

    fireEvent.mouseUp(spanV17);
    const panel = await screen.findByTestId("annotation-panel");
    fireEvent.click(within(panel).getByRole("button", { name: "Delete annotation" }));

    // Gone from every covered verse, by id.
    await waitFor(() =>
      expect(document.querySelectorAll('[data-highlight-id="8"]')).toHaveLength(0),
    );
  });

  it("hosts the panel in the responsive shell, rendered exactly once", async () => {
    installAnnotationStore([bsbAnnotation({ id: 5, char_start: 0, char_end: 7 })]);
    renderReader();
    await screen.findByTestId("verse-16");
    await waitFor(() => expect(highlightSpan(5)).toBeInTheDocument());

    fireEvent.mouseUp(highlightSpan(5)!);
    expect(await screen.findByTestId("reader-panel-shell")).toBeInTheDocument();
    // Single render — no desktop+mobile duplication (would break ids/testids).
    expect(screen.getAllByTestId("annotation-panel")).toHaveLength(1);
  });

  it("closes the shell on Escape and on a backdrop tap", async () => {
    installAnnotationStore([bsbAnnotation({ id: 5, char_start: 0, char_end: 7 })]);
    renderReader();
    await screen.findByTestId("verse-16");
    await waitFor(() => expect(highlightSpan(5)).toBeInTheDocument());

    // Escape.
    fireEvent.mouseUp(highlightSpan(5)!);
    await screen.findByTestId("annotation-panel");
    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() =>
      expect(screen.queryByTestId("annotation-panel")).not.toBeInTheDocument(),
    );

    // Backdrop tap.
    fireEvent.mouseUp(highlightSpan(5)!);
    await screen.findByTestId("annotation-panel");
    fireEvent.click(screen.getByTestId("panel-backdrop"));
    await waitFor(() =>
      expect(screen.queryByTestId("annotation-panel")).not.toBeInTheDocument(),
    );
  });

  it("deleting a highlight that HAS a note asks for confirmation first", async () => {
    installAnnotationStore([
      bsbAnnotation({ id: 5, char_start: 0, char_end: 7, note: "keep me?" }),
    ]);
    renderReader();

    await screen.findByTestId("verse-16");
    await waitFor(() => expect(highlightSpan(5)).toBeInTheDocument());

    fireEvent.mouseUp(highlightSpan(5)!);
    const panel = await screen.findByTestId("annotation-panel");
    fireEvent.click(within(panel).getByRole("button", { name: "Delete annotation" }));

    // Still present — a confirm step intervened.
    expect(highlightSpan(5)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Delete" })); // confirm

    await waitFor(() => expect(highlightSpan(5)).not.toBeInTheDocument());
  });
});

describe("ReaderPage — mutation error feedback (5c-6)", () => {
  function failPatch(): void {
    server.use(
      http.patch("/api/v1/annotations/:id", () =>
        HttpResponse.json(
          { detail: { code: "SERVER_ERROR", message: "boom" } },
          { status: 500 },
        ),
      ),
    );
  }

  it("surfaces a dismissible error when a color change fails; the highlight is unchanged", async () => {
    installAnnotationStore([
      bsbAnnotation({ id: 5, char_start: 0, char_end: 7, color: "yellow", note: null }),
    ]);
    failPatch();
    renderReader();
    await screen.findByTestId("verse-16");
    await waitFor(() => expect(highlightSpan(5)).toBeInTheDocument());

    fireEvent.mouseUp(highlightSpan(5)!);
    const panel = await screen.findByTestId("annotation-panel");
    fireEvent.click(within(panel).getByLabelText("Set color Green"));

    expect(await screen.findByTestId("annotation-error")).toBeInTheDocument();
    // Coherent: the failed PATCH didn't change the rendered color.
    expect(highlightSpan(5)!.style.backgroundColor).toBe("var(--hl-yellow)");

    // Dismiss clears it.
    fireEvent.click(
      within(screen.getByTestId("annotation-error")).getByRole("button", {
        name: /dismiss/i,
      }),
    );
    await waitFor(() =>
      expect(screen.queryByTestId("annotation-error")).not.toBeInTheDocument(),
    );
  });

  it("surfaces an error when saving a note fails, and keeps the typed text", async () => {
    installAnnotationStore([
      bsbAnnotation({ id: 5, char_start: 0, char_end: 7, note: null }),
    ]);
    failPatch();
    renderReader();
    await screen.findByTestId("verse-16");
    await waitFor(() => expect(highlightSpan(5)).toBeInTheDocument());

    fireEvent.mouseUp(highlightSpan(5)!);
    const panel = await screen.findByTestId("annotation-panel");
    fireEvent.change(within(panel).getByLabelText("Note"), {
      target: { value: "my thought" },
    });
    fireEvent.click(within(panel).getByRole("button", { name: "Save" }));

    expect(await screen.findByTestId("annotation-error")).toBeInTheDocument();
    // The user's text isn't lost.
    expect(within(panel).getByLabelText("Note")).toHaveValue("my thought");
  });

  it("surfaces an error when delete fails, keeping the panel open and the highlight present", async () => {
    installAnnotationStore([
      bsbAnnotation({ id: 5, char_start: 0, char_end: 7, note: null }),
    ]);
    server.use(
      http.delete("/api/v1/annotations/:id", () =>
        HttpResponse.json(
          { detail: { code: "SERVER_ERROR", message: "boom" } },
          { status: 500 },
        ),
      ),
    );
    renderReader();
    await screen.findByTestId("verse-16");
    await waitFor(() => expect(highlightSpan(5)).toBeInTheDocument());

    fireEvent.mouseUp(highlightSpan(5)!);
    const panel = await screen.findByTestId("annotation-panel");
    fireEvent.click(within(panel).getByRole("button", { name: "Delete annotation" }));

    expect(await screen.findByTestId("annotation-error")).toBeInTheDocument();
    // No half-applied limbo: panel stays open, highlight remains.
    expect(screen.getByTestId("annotation-panel")).toBeInTheDocument();
    expect(highlightSpan(5)).toBeInTheDocument();
  });

  it("clears a stale error when a later mutation succeeds", async () => {
    installAnnotationStore([
      bsbAnnotation({ id: 5, char_start: 0, char_end: 7, color: "yellow", note: null }),
    ]);
    failPatch(); // PATCH fails; DELETE still succeeds via the store handler
    renderReader();
    await screen.findByTestId("verse-16");
    await waitFor(() => expect(highlightSpan(5)).toBeInTheDocument());

    fireEvent.mouseUp(highlightSpan(5)!);
    const panel = await screen.findByTestId("annotation-panel");
    fireEvent.click(within(panel).getByLabelText("Set color Green"));
    expect(await screen.findByTestId("annotation-error")).toBeInTheDocument();

    // A successful delete clears the lingering error (and removes the highlight).
    fireEvent.click(within(panel).getByRole("button", { name: "Delete annotation" }));
    await waitFor(() => expect(highlightSpan(5)).not.toBeInTheDocument());
    expect(screen.queryByTestId("annotation-error")).not.toBeInTheDocument();
  });
});
