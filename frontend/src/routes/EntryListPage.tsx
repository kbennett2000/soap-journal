import { Link, useSearchParams } from "react-router-dom";

import { EntryCard } from "@/components/EntryCard";
import { useEntryList } from "@/hooks/useEntries";

const DEFAULT_LIMIT = 20;

export function EntryListPage(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const limit = clampInt(searchParams.get("limit"), DEFAULT_LIMIT, 1, 100);
  const offset = clampInt(searchParams.get("offset"), 0, 0, Number.MAX_SAFE_INTEGER);
  const order = searchParams.get("order") === "oldest" ? "oldest" : "newest";

  const query = useEntryList({ limit, offset, order });

  function setParam(key: string, value: string | null): void {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (value === null || value === "") {
          next.delete(key);
        } else {
          next.set(key, value);
        }
        return next;
      },
      { replace: false },
    );
  }

  function setOffset(nextOffset: number): void {
    setParam("offset", nextOffset > 0 ? String(nextOffset) : null);
  }

  function setOrder(nextOrder: "newest" | "oldest"): void {
    // Update both keys in a single setSearchParams call. Calling
    // setParam twice in a row doesn't batch — the second call sees the
    // pre-update searchParams and clobbers the first update.
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (nextOrder === "oldest") {
          next.set("order", "oldest");
        } else {
          next.delete("order");
        }
        next.delete("offset");
        return next;
      },
      { replace: false },
    );
  }

  const total = query.data?.total ?? 0;
  const entries = query.data?.entries ?? [];
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

      {query.isError && (
        <div
          role="alert"
          className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-200"
        >
          Couldn't load your entries.
        </div>
      )}

      {query.data && entries.length === 0 && (
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
      )}

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
