import { Link, useSearchParams } from "react-router-dom";

import { AppliedFilterChips, type FilterKey } from "@/components/AppliedFilterChips";
import { EntryCard } from "@/components/EntryCard";
import { FilterBar, type FilterValues } from "@/components/FilterBar";
import { useEntryList } from "@/hooks/useEntries";
import { ApiError } from "@/lib/apiError";
import type { AppliedFilters } from "@/types/api";

const DEFAULT_LIMIT = 20;

export function EntryListPage(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();

  const limit = clampInt(searchParams.get("limit"), DEFAULT_LIMIT, 1, 100);
  const offset = clampInt(searchParams.get("offset"), 0, 0, Number.MAX_SAFE_INTEGER);
  const order = searchParams.get("order") === "oldest" ? "oldest" : "newest";
  const q = searchParams.get("q") ?? "";
  const book = searchParams.get("book") ?? "";
  const tag = searchParams.get("tag") ?? "";
  const fromDate = searchParams.get("from_date") ?? "";
  const toDate = searchParams.get("to_date") ?? "";

  const query = useEntryList({
    limit,
    offset,
    order,
    q: q || undefined,
    book: book || undefined,
    tag: tag || undefined,
    from_date: fromDate || undefined,
    to_date: toDate || undefined,
  });

  function updateParams(
    update: (next: URLSearchParams) => void,
    options: { resetOffset?: boolean } = {},
  ): void {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        update(next);
        if (options.resetOffset) next.delete("offset");
        return next;
      },
      { replace: false },
    );
  }

  function setOffset(nextOffset: number): void {
    updateParams((next) => {
      if (nextOffset > 0) next.set("offset", String(nextOffset));
      else next.delete("offset");
    });
  }

  function setOrder(nextOrder: "newest" | "oldest"): void {
    updateParams(
      (next) => {
        if (nextOrder === "oldest") next.set("order", "oldest");
        else next.delete("order");
      },
      { resetOffset: true },
    );
  }

  function applyFilters(filterValues: FilterValues): void {
    updateParams(
      (next) => {
        setOrDelete(next, "q", filterValues.q);
        setOrDelete(next, "book", filterValues.book);
        setOrDelete(next, "tag", filterValues.tag);
        setOrDelete(next, "from_date", filterValues.fromDate);
        setOrDelete(next, "to_date", filterValues.toDate);
      },
      { resetOffset: true },
    );
  }

  function removeFilter(key: FilterKey): void {
    updateParams(
      (next) => {
        next.delete(key);
      },
      { resetOffset: true },
    );
  }

  function clearFilters(): void {
    updateParams(
      (next) => {
        next.delete("q");
        next.delete("book");
        next.delete("tag");
        next.delete("from_date");
        next.delete("to_date");
      },
      { resetOffset: true },
    );
  }

  const filterValues: FilterValues = {
    q,
    book,
    tag,
    fromDate,
    toDate,
  };

  const hasAnyFilter = Boolean(q || book || tag || fromDate || toDate);
  const apiError = query.error instanceof ApiError ? query.error : null;
  const dateRangeError = apiError?.code === "INVALID_DATE_RANGE" ? apiError.message : null;
  const bookError = apiError?.code === "INVALID_BOOK" ? apiError.message : null;

  const total = query.data?.total ?? 0;
  const entries = query.data?.entries ?? [];
  // Server always echoes applied_filters back; default to "all null" so
  // the chip code stays simple while data is loading.
  const appliedFilters: AppliedFilters =
    query.data?.applied_filters ?? {
      q: null,
      book: null,
      tag: null,
      from_date: null,
      to_date: null,
    };
  const startNum = entries.length === 0 ? 0 : offset + 1;
  const endNum = offset + entries.length;
  const hasPrev = offset > 0;
  const hasNext = offset + entries.length < total;

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold">Your entries</h1>
        <Link
          to="/entries/new"
          className="inline-flex h-9 items-center rounded-md bg-slate-900 px-4 text-sm font-medium text-white shadow-sm hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
        >
          + New entry
        </Link>
      </header>

      <FilterBar
        values={filterValues}
        onChange={applyFilters}
        dateRangeError={dateRangeError}
      />

      <AppliedFilterChips applied={appliedFilters} onRemove={removeFilter} />

      {bookError && (
        <div
          role="alert"
          className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-200"
        >
          {bookError}
        </div>
      )}

      <div className="flex items-center gap-2 text-sm">
        <span className="text-slate-600 dark:text-slate-300">Order:</span>
        <button
          type="button"
          onClick={() => setOrder("newest")}
          className={orderButtonClass(order === "newest")}
        >
          Newest first
        </button>
        <button
          type="button"
          onClick={() => setOrder("oldest")}
          className={orderButtonClass(order === "oldest")}
        >
          Oldest first
        </button>
      </div>

      {query.isLoading && (
        <div data-testid="entries-loading" className="space-y-2">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-24 animate-pulse rounded-md bg-slate-100 dark:bg-slate-800"
            />
          ))}
        </div>
      )}

      {query.isError && !dateRangeError && !bookError && (
        <div
          role="alert"
          className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-200"
        >
          {query.error instanceof ApiError
            ? query.error.message
            : "Couldn't load your entries."}
        </div>
      )}

      {query.data &&
        entries.length === 0 &&
        (hasAnyFilter ? (
          <div
            data-testid="entries-filtered-empty"
            className="rounded-md border border-dashed border-slate-300 bg-white p-6 text-center dark:border-slate-700 dark:bg-slate-900"
          >
            <p className="text-sm text-slate-600 dark:text-slate-300">
              No entries match these filters.
            </p>
            <button
              type="button"
              onClick={clearFilters}
              className="mt-3 inline-flex h-9 items-center rounded-md bg-slate-900 px-4 text-sm font-medium text-white shadow-sm hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
            >
              Clear filters
            </button>
          </div>
        ) : (
          <div
            data-testid="entries-empty"
            className="rounded-md border border-dashed border-slate-300 bg-white p-6 text-center dark:border-slate-700 dark:bg-slate-900"
          >
            <p className="text-sm text-slate-600 dark:text-slate-300">
              No entries yet. Start a SOAP journal whenever a passage strikes you.
            </p>
            <Link
              to="/entries/new"
              className="mt-3 inline-flex h-9 items-center rounded-md bg-slate-900 px-4 text-sm font-medium text-white shadow-sm hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
            >
              Create your first entry
            </Link>
          </div>
        ))}

      {query.data && entries.length > 0 && (
        <div className="space-y-3">
          {entries.map((entry) => (
            <EntryCard key={entry.id} entry={entry} />
          ))}
        </div>
      )}

      {total > 0 && (
        <nav className="flex items-center justify-between border-t border-slate-200 pt-4 text-sm dark:border-slate-700">
          <button
            type="button"
            onClick={() => setOffset(Math.max(0, offset - limit))}
            disabled={!hasPrev}
            className="inline-flex h-9 items-center rounded-md border border-slate-300 bg-white px-3 font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            ← Previous
          </button>
          <span className="text-slate-600 dark:text-slate-400">
            {startNum}–{endNum} of {total}
          </span>
          <button
            type="button"
            onClick={() => setOffset(offset + limit)}
            disabled={!hasNext}
            className="inline-flex h-9 items-center rounded-md border border-slate-300 bg-white px-3 font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            Next →
          </button>
        </nav>
      )}
    </div>
  );
}

function orderButtonClass(active: boolean): string {
  return active
    ? "inline-flex h-8 items-center rounded-md bg-slate-900 px-3 text-xs font-medium text-white dark:bg-slate-100 dark:text-slate-900"
    : "inline-flex h-8 items-center rounded-md border border-slate-300 bg-white px-3 text-xs font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700";
}

function clampInt(
  raw: string | null,
  fallback: number,
  min: number,
  max: number,
): number {
  if (raw === null) return fallback;
  const n = Number.parseInt(raw, 10);
  if (!Number.isFinite(n)) return fallback;
  if (n < min) return min;
  if (n > max) return max;
  return n;
}

function setOrDelete(params: URLSearchParams, key: string, value: string): void {
  if (value && value.trim().length > 0) params.set(key, value);
  else params.delete(key);
}
