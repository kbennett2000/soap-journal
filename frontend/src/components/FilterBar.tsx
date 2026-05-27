import { useEffect, useRef, useState } from "react";

import { useTagList } from "@/hooks/useTags";
import { useTranslationDetail, useTranslations } from "@/hooks/useBible";
import type { BookSummary } from "@/types/api";

export interface FilterValues {
  q: string;
  book: string;
  tag: string;
  fromDate: string;
  toDate: string;
}

interface FilterBarProps {
  values: FilterValues;
  onChange: (next: FilterValues) => void;
  /** Server-side error to highlight the date inputs when present. */
  dateRangeError?: string | null;
}

const Q_DEBOUNCE_MS = 300;

/**
 * Search + book + tag + date-range row above the entry list.
 *
 * The parent owns the canonical filter state (URL params); this
 * component is a controlled view. `q` is debounced locally so live-
 * typing doesn't fire a request per keystroke; everything else is
 * applied immediately on change.
 */
export function FilterBar({
  values,
  onChange,
  dateRangeError,
}: FilterBarProps): JSX.Element {
  const [qDraft, setQDraft] = useState(values.q);
  const [skipDebounce, setSkipDebounce] = useState(false);
  const lastFiredQ = useRef(values.q);

  // Keep the local draft in sync with parent-driven changes (e.g. chip
  // ×, clear-filters button). The setState-in-effect rule discourages
  // this in general, but here the cascade is the desired behavior —
  // parent-driven resets must propagate into the local draft.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setQDraft(values.q);
    lastFiredQ.current = values.q;
  }, [values.q]);

  // Debounced q -> onChange. Submit on Enter / clear with × bypasses
  // the debounce via `skipDebounce`.
  useEffect(() => {
    if (qDraft === lastFiredQ.current) return;
    if (skipDebounce) {
      lastFiredQ.current = qDraft;
      // Reset the bypass flag after using it. Same rationale as above:
      // legitimate flag-cleanup tied to an external trigger.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSkipDebounce(false);
      onChange({ ...values, q: qDraft });
      return;
    }
    const timer = window.setTimeout(() => {
      lastFiredQ.current = qDraft;
      onChange({ ...values, q: qDraft });
    }, Q_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
    // values intentionally excluded — we read it via the latest closure
    // when the timer fires, and including it would re-arm the timer on
    // every parent state shift.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [qDraft, skipDebounce]);

  const translationsQuery = useTranslations();
  const defaultCode =
    translationsQuery.data?.translations[0]?.code ?? "BSB";
  const translationDetail = useTranslationDetail(defaultCode);
  const books: BookSummary[] = translationDetail.data?.books ?? [];
  const tagList = useTagList();
  const tags = tagList.data?.tags ?? [];

  const dateBorderClass = dateRangeError
    ? "border-rose-400 dark:border-rose-700"
    : "border-slate-300 dark:border-slate-700";

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-end gap-2">
        <div className="min-w-[14rem] flex-1">
          <label
            htmlFor="filter-q"
            className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300"
          >
            Search
          </label>
          <div className="relative">
            <input
              id="filter-q"
              type="search"
              value={qDraft}
              onChange={(e) => setQDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  setSkipDebounce(true);
                }
              }}
              placeholder="Search titles, observations, prayer…"
              className="block h-9 w-full rounded-md border border-slate-300 bg-white px-3 pr-8 text-sm text-slate-900 shadow-sm focus:outline-none focus:ring-1 focus:ring-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            />
            {qDraft && (
              <button
                type="button"
                aria-label="Clear search"
                onClick={() => {
                  setSkipDebounce(true);
                  setQDraft("");
                }}
                className="absolute right-1.5 top-1/2 inline-flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-700 dark:hover:text-slate-200"
              >
                ×
              </button>
            )}
          </div>
        </div>

        <div className="min-w-[10rem]">
          <label
            htmlFor="filter-book"
            className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300"
          >
            Book
          </label>
          <select
            id="filter-book"
            value={values.book}
            onChange={(e) => onChange({ ...values, book: e.target.value })}
            className="block h-9 w-full rounded-md border border-slate-300 bg-white px-2 text-sm text-slate-900 shadow-sm focus:outline-none focus:ring-1 focus:ring-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          >
            <option value="">(All books)</option>
            {books.map((b) => (
              <option key={b.name} value={b.name}>
                {b.name}
              </option>
            ))}
          </select>
        </div>

        <div className="min-w-[10rem]">
          <label
            htmlFor="filter-tag"
            className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300"
          >
            Tag
          </label>
          <select
            id="filter-tag"
            value={values.tag}
            disabled={tags.length === 0}
            onChange={(e) => onChange({ ...values, tag: e.target.value })}
            className="block h-9 w-full rounded-md border border-slate-300 bg-white px-2 text-sm text-slate-900 shadow-sm focus:outline-none focus:ring-1 focus:ring-slate-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          >
            <option value="">(All tags)</option>
            {tags.map((t) => (
              <option key={t.id} value={t.name}>
                {t.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label
            htmlFor="filter-from"
            className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300"
          >
            From
          </label>
          <input
            id="filter-from"
            type="date"
            value={values.fromDate}
            onChange={(e) => onChange({ ...values, fromDate: e.target.value })}
            className={`block h-9 rounded-md ${dateBorderClass} border bg-white px-2 text-sm text-slate-900 shadow-sm focus:outline-none focus:ring-1 focus:ring-slate-500 dark:bg-slate-800 dark:text-slate-100`}
          />
        </div>

        <div>
          <label
            htmlFor="filter-to"
            className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300"
          >
            To
          </label>
          <input
            id="filter-to"
            type="date"
            value={values.toDate}
            onChange={(e) => onChange({ ...values, toDate: e.target.value })}
            className={`block h-9 rounded-md ${dateBorderClass} border bg-white px-2 text-sm text-slate-900 shadow-sm focus:outline-none focus:ring-1 focus:ring-slate-500 dark:bg-slate-800 dark:text-slate-100`}
          />
        </div>
      </div>
      {dateRangeError && (
        <p
          role="alert"
          className="text-xs text-rose-700 dark:text-rose-300"
        >
          {dateRangeError}
        </p>
      )}
    </div>
  );
}
