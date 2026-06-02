import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { useBibleSearch, useTranslations } from "@/hooks/useBible";
import { highlightSnippet } from "@/lib/highlightSnippet";
import type {
  NoteSearchHit,
  NoteType,
  SearchScope,
  VerseSearchHit,
} from "@/types/api";

/**
 * Full-text scripture + notes search. Deliberately distinct from the entry
 * keyword search at /entries — different feature, different data, its own route
 * and labelling. Verse and note hits are shown as two separate lists.
 */

const ALL_TRANSLATIONS = "ALL";

const NOTE_TYPE_LABELS: Record<NoteType, string> = {
  tn: "Translator's Note",
  sn: "Study Note",
  tc: "Text-Critical Note",
  map: "Map",
};

const SCOPES: { value: SearchScope; label: string }[] = [
  { value: "both", label: "Verses & notes" },
  { value: "verses", label: "Verses" },
  { value: "notes", label: "Notes" },
];

function readerUrl(code: string, book: string, chapter: number, verse: number): string {
  return (
    `/read/${encodeURIComponent(code)}/${encodeURIComponent(book)}/${chapter}` +
    `?range=${verse}-${verse}`
  );
}

function reference(book: string, chapter: number, verse: number): string {
  return `${book} ${chapter}:${verse}`;
}

export function BibleSearchPage(): JSX.Element {
  const [searchParams] = useSearchParams();

  const translationsQuery = useTranslations();
  const translations = translationsQuery.data?.translations ?? [];

  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQ(q), 300);
    return () => window.clearTimeout(timer);
  }, [q]);

  const [scope, setScope] = useState<SearchScope>("both");
  // null → fall back to the first-loaded translation once the list resolves.
  const [translation, setTranslation] = useState<string | null>(
    searchParams.get("translation"),
  );
  const effectiveTranslation = translation ?? translations[0]?.code ?? "";

  const query = useBibleSearch({
    q: debouncedQ,
    translation: effectiveTranslation || undefined,
    scope,
  });

  const showVerses = scope === "both" || scope === "verses";
  const showNotes = scope === "both" || scope === "notes";
  const data = query.data;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Search Scripture</h1>

      <div className="flex flex-wrap items-end gap-3 rounded-md border border-slate-200 bg-white p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <label className="flex min-w-[16rem] flex-1 flex-col text-xs font-medium text-slate-600 dark:text-slate-300">
          Search words or a phrase
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            aria-label="Search scripture and notes"
            placeholder="Search scripture and notes…"
            className="mt-1 h-9 rounded-md border border-slate-300 px-3 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          />
        </label>

        <label className="flex flex-col text-xs font-medium text-slate-600 dark:text-slate-300">
          Translation
          <select
            value={effectiveTranslation}
            onChange={(e) => setTranslation(e.target.value)}
            aria-label="Search translation"
            className="mt-1 h-9 rounded-md border border-slate-300 px-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          >
            {translations.map((t) => (
              <option key={t.code} value={t.code}>
                {t.code}
              </option>
            ))}
            <option value={ALL_TRANSLATIONS}>All translations</option>
          </select>
        </label>

        <div
          role="group"
          aria-label="Result scope"
          className="flex h-9 overflow-hidden rounded-md border border-slate-300 dark:border-slate-700"
        >
          {SCOPES.map((s) => (
            <button
              key={s.value}
              type="button"
              aria-pressed={scope === s.value}
              onClick={() => setScope(s.value)}
              className={`px-3 text-xs font-medium ${
                scope === s.value
                  ? "bg-sky-600 text-white"
                  : "bg-white text-slate-700 hover:bg-slate-100 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {debouncedQ.trim().length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Type a word or phrase to search verse text and translator's notes.
        </p>
      ) : (
        data && (
          <div className="grid gap-6 md:grid-cols-2">
            {showVerses && (
              <VerseResults
                hits={data.verse_hits}
                total={data.total_verse_hits}
              />
            )}
            {showNotes && (
              <NoteResults hits={data.note_hits} total={data.total_note_hits} />
            )}
          </div>
        )
      )}
    </div>
  );
}

function VerseResults({
  hits,
  total,
}: {
  hits: VerseSearchHit[];
  total: number;
}): JSX.Element {
  return (
    <section data-testid="verse-results">
      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        Verses ({total})
      </h2>
      {hits.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">No verse matches.</p>
      ) : (
        <ul className="space-y-2">
          {hits.map((h, i) => (
            <li
              key={`${h.translation_code}-${h.book}-${h.chapter}-${h.verse}-${i}`}
              className="rounded-md border border-slate-200 bg-white p-2 text-sm dark:border-slate-700 dark:bg-slate-900"
            >
              <div className="flex items-baseline justify-between gap-2">
                <Link
                  to={readerUrl(h.translation_code, h.book, h.chapter, h.verse)}
                  className="font-medium text-sky-700 hover:underline dark:text-sky-300"
                >
                  {reference(h.book, h.chapter, h.verse)}
                </Link>
                {h.translation_codes && (
                  <span
                    data-testid="verse-codes"
                    className="text-xs text-slate-500 dark:text-slate-400"
                  >
                    {h.translation_codes.join(", ")}
                  </span>
                )}
              </div>
              <p className="mt-1 text-slate-700 dark:text-slate-200">
                {highlightSnippet(h.snippet)}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function NoteResults({
  hits,
  total,
}: {
  hits: NoteSearchHit[];
  total: number;
}): JSX.Element {
  return (
    <section data-testid="note-results">
      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        Notes ({total})
      </h2>
      {hits.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">No note matches.</p>
      ) : (
        <ul className="space-y-2">
          {hits.map((h, i) => (
            <li
              key={`${h.translation_code}-${h.book}-${h.chapter}-${h.verse}-${i}`}
              className="rounded-md border border-slate-200 bg-white p-2 text-sm dark:border-slate-700 dark:bg-slate-900"
            >
              <div className="flex items-baseline justify-between gap-2">
                <Link
                  to={readerUrl(h.translation_code, h.book, h.chapter, h.verse)}
                  className="font-medium text-sky-700 hover:underline dark:text-sky-300"
                >
                  {reference(h.book, h.chapter, h.verse)}
                </Link>
                <span className="text-xs font-semibold uppercase tracking-wide text-sky-700 dark:text-sky-300">
                  {h.note_type ? NOTE_TYPE_LABELS[h.note_type] : "Note"}
                </span>
              </div>
              <p className="mt-1 text-slate-700 dark:text-slate-200">
                {highlightSnippet(h.snippet)}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
