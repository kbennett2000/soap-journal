import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { ConfirmDialog } from "@/components/ConfirmDialog";
import { useDeleteEntry, useEntry } from "@/hooks/useEntries";
import { ApiError } from "@/lib/apiError";
import type { EntryResponse } from "@/types/api";

export function EntryDetailPage(): JSX.Element {
  const { entryId: entryIdParam } = useParams<{ entryId: string }>();
  const entryId = Number.parseInt(entryIdParam ?? "", 10);
  const validId = Number.isFinite(entryId) && entryId > 0;

  const query = useEntry(validId ? entryId : undefined);
  const deleteMutation = useDeleteEntry();
  const navigate = useNavigate();

  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  if (!validId) {
    return <NotFoundPanel />;
  }

  if (query.isLoading) {
    return (
      <div data-testid="entry-detail-loading" className="space-y-3">
        <div className="h-7 w-2/3 animate-pulse rounded bg-slate-200 dark:bg-slate-800" />
        <div className="h-4 w-1/3 animate-pulse rounded bg-slate-200 dark:bg-slate-800" />
        <div className="h-24 animate-pulse rounded bg-slate-200 dark:bg-slate-800" />
      </div>
    );
  }

  if (query.isError) {
    const isNotFound = query.error instanceof ApiError && query.error.status === 404;
    if (isNotFound) return <NotFoundPanel />;
    return (
      <div
        role="alert"
        className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-200"
      >
        Unable to load this entry.
      </div>
    );
  }

  if (!query.data) return <NotFoundPanel />;
  const entry: EntryResponse = query.data;

  async function handleConfirmDelete(): Promise<void> {
    setDeleteError(null);
    try {
      await deleteMutation.mutateAsync(entryId);
      navigate("/entries");
    } catch (err) {
      if (err instanceof ApiError) {
        setDeleteError(err.message);
      } else {
        setDeleteError("Unable to delete entry.");
      }
      setConfirmingDelete(false);
    }
  }

  const openInReader = buildReaderHref(entry);

  return (
    <article className="space-y-5">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold">{entry.display_title}</h1>
        <div className="flex flex-wrap items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
          <span>{entry.scripture_ref}</span>
          <span>·</span>
          <span>{entry.entry_date}</span>
          <span>·</span>
          <span className="inline-flex h-6 items-center rounded bg-slate-100 px-2 text-xs font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-300">
            {entry.translation_code}
          </span>
        </div>
      </header>

      <section className="rounded-md border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-800">
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {entry.scripture_ref}
        </div>
        <div className="whitespace-pre-wrap text-slate-700 dark:text-slate-200">
          {entry.scripture_text}
        </div>
      </section>

      <Section title="Observation" body={entry.observation} />
      <Section title="Application" body={entry.application} />
      <Section title="Prayer" body={entry.prayer} />

      {entry.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {entry.tags.map((tag) => (
            <span
              key={tag.id}
              className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300"
            >
              {tag.name}
            </span>
          ))}
        </div>
      )}

      {deleteError && (
        <div
          role="alert"
          className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-200"
        >
          {deleteError}
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 pt-4 dark:border-slate-700">
        <div className="flex gap-2">
          <Link
            to={`/entries/${entry.id}/edit`}
            className="inline-flex h-9 items-center rounded-md bg-slate-900 px-4 text-sm font-medium text-white shadow-sm hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
          >
            Edit
          </Link>
          {openInReader && (
            <Link
              to={openInReader}
              className="inline-flex h-9 items-center rounded-md border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              Open in reader
            </Link>
          )}
        </div>
        <button
          type="button"
          onClick={() => setConfirmingDelete(true)}
          disabled={deleteMutation.isPending}
          className="inline-flex h-9 items-center rounded-md border border-rose-300 bg-white px-4 text-sm font-medium text-rose-700 hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-rose-800 dark:bg-slate-900 dark:text-rose-300 dark:hover:bg-rose-950"
        >
          Delete
        </button>
      </div>

      <ConfirmDialog
        open={confirmingDelete}
        title="Delete entry"
        message="Delete this entry? This cannot be undone."
        confirmLabel={deleteMutation.isPending ? "Deleting…" : "Delete"}
        destructive
        onConfirm={() => {
          void handleConfirmDelete();
        }}
        onCancel={() => setConfirmingDelete(false)}
      />
    </article>
  );
}

function Section({ title, body }: { title: string; body: string }): JSX.Element {
  return (
    <section>
      <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {title}
      </h2>
      {body.trim() ? (
        <div className="whitespace-pre-wrap text-slate-800 dark:text-slate-200">{body}</div>
      ) : (
        <div className="text-sm italic text-slate-400 dark:text-slate-500">(empty)</div>
      )}
    </section>
  );
}

function NotFoundPanel(): JSX.Element {
  return (
    <div
      data-testid="entry-not-found"
      className="rounded-md border border-dashed border-slate-300 bg-white p-6 text-center dark:border-slate-700 dark:bg-slate-900"
    >
      <p className="text-sm text-slate-600 dark:text-slate-300">Entry not found.</p>
      <Link
        to="/entries"
        className="mt-3 inline-flex h-9 items-center rounded-md bg-slate-900 px-4 text-sm font-medium text-white shadow-sm hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
      >
        Back to entries
      </Link>
    </div>
  );
}

/**
 * Build a `/read/...` URL pointing at the entry's scripture range.
 * Parses `scripture_ref` defensively — if we can't make sense of it
 * we just don't render the link.
 */
function buildReaderHref(entry: EntryResponse): string | null {
  // scripture_ref is the canonical form: "John 3", "John 3:16", or
  // "John 3:16-20" (possibly with multi-word books like "1 Corinthians").
  const match = /^(.*?)\s+(\d+)(?::(\d+)(?:-(\d+))?)?$/.exec(entry.scripture_ref);
  if (!match) return null;
  const bookName = match[1];
  const chapter = match[2];
  const startStr = match[3];
  const endStr = match[4];
  if (!bookName || !chapter) return null;
  const base = `/read/${encodeURIComponent(entry.translation_code)}/${encodeURIComponent(
    bookName,
  )}/${chapter}`;
  if (!startStr) return base;
  const range = endStr ? `${startStr}-${endStr}` : startStr;
  return `${base}?range=${range}`;
}
