import { http, HttpResponse } from "msw";

import {
  makeChapter,
  makeTranslationDetail,
  makeTranslationList,
} from "@/test/utils/bible";
import {
  makeEntryEnvelope,
  makeEntryList,
  makeTagList,
} from "@/test/utils/entries";
import { makeUser } from "@/test/utils/factories";
import type { AuthEnvelope } from "@/types/api";

/**
 * Default happy-path handlers. Each test overrides the specific
 * endpoint(s) it wants to behave differently via `server.use(...)`.
 *
 * Handlers are exported individually so a test can pluck `meHandler`
 * and replace it with its own version without redefining the URL or
 * thinking about request shape.
 */

export const meHandler = http.get("/api/v1/auth/me", () => {
  const envelope: AuthEnvelope = { user: makeUser() };
  return HttpResponse.json(envelope, { status: 200 });
});

export const loginHandler = http.post("/api/v1/auth/login", () => {
  const envelope: AuthEnvelope = { user: makeUser() };
  return HttpResponse.json(envelope, { status: 200 });
});

export const registerHandler = http.post("/api/v1/auth/register", () => {
  const envelope: AuthEnvelope = { user: makeUser() };
  return HttpResponse.json(envelope, { status: 201 });
});

export const logoutHandler = http.post("/api/v1/auth/logout", () => {
  return new HttpResponse(null, { status: 204 });
});

// ---- Bible reader ---------------------------------------------------------

export const translationsHandler = http.get("/api/v1/bible/translations", () => {
  return HttpResponse.json(makeTranslationList(), { status: 200 });
});

export const translationDetailHandler = http.get(
  "/api/v1/bible/translations/:code",
  () => HttpResponse.json(makeTranslationDetail(), { status: 200 }),
);

export const chapterHandler = http.get(
  "/api/v1/bible/translations/:code/books/:bookName/chapters/:chapterNumber",
  ({ params }) => {
    const bookName = String(params.bookName);
    const chapterNumber = Number(params.chapterNumber);
    return HttpResponse.json(
      makeChapter({ bookName, chapterNumber }),
      { status: 200 },
    );
  },
);

export const resolveHandler = http.get("/api/v1/bible/resolve", ({ request }) => {
  const url = new URL(request.url);
  const ref = url.searchParams.get("ref") ?? "";
  // Default: pretend everything resolves to John 3:16 unless overridden.
  return HttpResponse.json(
    {
      reference: {
        canonical_string: ref,
        translation_code: "BSB",
        book: {
          name: "John",
          abbreviation: "John",
          order_index: 43,
          testament: "NT",
          chapter_count: 21,
        },
        chapter_number: 3,
        start_verse: 16,
        end_verse: 16,
      },
      verses: [],
    },
    { status: 200 },
  );
});

// ---- entries + tags -------------------------------------------------------

export const entriesListHandler = http.get("/api/v1/entries", () => {
  return HttpResponse.json(makeEntryList(), { status: 200 });
});

export const entryDetailHandler = http.get("/api/v1/entries/:entryId", ({ params }) => {
  const id = Number.parseInt(String(params.entryId), 10);
  return HttpResponse.json(makeEntryEnvelope({ id }), { status: 200 });
});

export const createEntryHandler = http.post("/api/v1/entries", () => {
  return HttpResponse.json(makeEntryEnvelope({ id: 9999 }), { status: 201 });
});

export const updateEntryHandler = http.put("/api/v1/entries/:entryId", ({ params }) => {
  const id = Number.parseInt(String(params.entryId), 10);
  return HttpResponse.json(makeEntryEnvelope({ id }), { status: 200 });
});

export const deleteEntryHandler = http.delete("/api/v1/entries/:entryId", () => {
  return new HttpResponse(null, { status: 204 });
});

export const tagsListHandler = http.get("/api/v1/tags", () => {
  return HttpResponse.json(makeTagList(), { status: 200 });
});

export const tagsAutocompleteHandler = http.get(
  "/api/v1/tags/autocomplete",
  () => HttpResponse.json({ tags: [] }, { status: 200 }),
);

export const defaultHandlers = [
  meHandler,
  loginHandler,
  registerHandler,
  logoutHandler,
  translationsHandler,
  translationDetailHandler,
  chapterHandler,
  resolveHandler,
  entriesListHandler,
  entryDetailHandler,
  createEntryHandler,
  updateEntryHandler,
  deleteEntryHandler,
  tagsListHandler,
  tagsAutocompleteHandler,
];
