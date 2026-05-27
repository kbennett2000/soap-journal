import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { CompactEntryCard } from "@/components/CompactEntryCard";
import { useAuth } from "@/hooks/useAuth";
import { useEntryList, useOnThisDay } from "@/hooks/useEntries";
import { useTranslations } from "@/hooks/useBible";
import { resolveReference } from "@/lib/bible";
import { ApiError } from "@/lib/apiError";

export function DashboardPage(): JSX.Element {
  const { user } = useAuth();
  const recentQuery = useEntryList({ limit: 5, order: "newest" });
  const onThisDayQuery = useOnThisDay();
  const translationsQuery = useTranslations();
  const defaultCode = translationsQuery.data?.translations[0]?.code ?? "BSB";

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">
        Welcome, {user?.username ?? "friend"}.
      </h1>

      <JumpAndNewEntry translationCode={defaultCode} />

      <div className="grid gap-6 lg:grid-cols-2">
        <section
          aria-labelledby="dash-recent-heading"
          className="rounded-md border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900"
        >
          <div className="mb-3 flex items-center justify-between">
            <h2
              id="dash-recent-heading"
              className="text-sm font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300"
            >
              Recent entries
            </h2>
            <Link
              to="/entries"
              className="text-xs font-medium text-slate-600 underline-offset-2 hover:underline dark:text-slate-300"
            >
              View all →
            </Link>
          </div>
          {recentQuery.isLoading && (
            <div data-testid="dash-recent-loading" className="space-y-2">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="h-10 animate-pulse rounded bg-slate-100 dark:bg-slate-800"
                />
              ))}
            </div>
          )}
          {recentQuery.data && recentQuery.data.entries.length === 0 && (
            <div
              data-testid="dash-recent-empty"
              className="text-sm text-slate-600 dark:text-slate-300"
            >
              No entries yet.{" "}
              <Link
                to="/entries/new"
                className="font-medium underline-offset-2 hover:underline"
              >
                Start your first entry.
              </Link>
            </div>
          )}
          {recentQuery.data && recentQuery.data.entries.length > 0 && (
            <div className="space-y-2">
              {recentQuery.data.entries.map((entry) => (
                <CompactEntryCard key={entry.id} entry={entry} />
              ))}
            </div>
          )}
        </section>

        <section
          aria-labelledby="dash-onthisday-heading"
          className="rounded-md border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900"
        >
          <div className="mb-3">
            <h2
              id="dash-onthisday-heading"
              className="text-sm font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300"
            >
              On this day in previous years
            </h2>
            {onThisDayQuery.data?.target_date && (
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {formatTargetDate(onThisDayQuery.data.target_date)}
              </p>
            )}
          </div>
          {onThisDayQuery.isLoading && (
            <div data-testid="dash-onthisday-loading" className="space-y-2">
              {[0, 1].map((i) => (
                <div
                  key={i}
                  className="h-10 animate-pulse rounded bg-slate-100 dark:bg-slate-800"
                />
              ))}
            </div>
          )}
          {onThisDayQuery.data && onThisDayQuery.data.entries.length === 0 && (
            <div
              data-testid="dash-onthisday-empty"
              className="text-sm text-slate-600 dark:text-slate-300"
            >
              Nothing from prior years on this date.
            </div>
          )}
          {onThisDayQuery.data && onThisDayQuery.data.entries.length > 0 && (
            <div className="space-y-2">
              {onThisDayQuery.data.entries.map((entry) => (
                <CompactEntryCard key={entry.id} entry={entry} showYear />
              ))}
            </div>
          )}
        </section>
      </div>

      <nav className="flex flex-wrap gap-2">
        <Link
          to="/read"
          className="inline-flex h-9 items-center rounded-md border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
        >
          Open the reader →
        </Link>
        <Link
          to="/calendar"
          className="inline-flex h-9 items-center rounded-md border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
        >
          Calendar
        </Link>
      </nav>
    </div>
  );
}

interface JumpAndNewEntryProps {
  translationCode: string;
}

function JumpAndNewEntry({ translationCode }: JumpAndNewEntryProps): JSX.Element {
  const navigate = useNavigate();
  const [value, setValue] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!value.trim()) return;
    setError(null);
    setSubmitting(true);
    try {
      const response = await resolveReference(value.trim(), translationCode);
      const ref = response.reference;
      const range = `?range=${ref.start_verse}-${ref.end_verse}`;
      navigate(
        `/read/${encodeURIComponent(ref.translation_code)}/${encodeURIComponent(
          ref.book.name,
        )}/${ref.chapter_number}${range}`,
      );
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Something went wrong.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">
        Jump to a passage
      </h2>
      <form onSubmit={handleSubmit} className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="text"
            aria-label="Jump to reference"
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              if (error) setError(null);
            }}
            placeholder='e.g. "John 3:16" or "Romans 8:28-30"'
            className="h-9 min-w-[14rem] flex-1 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900 shadow-sm focus:outline-none focus:ring-1 focus:ring-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          />
          <button
            type="submit"
            disabled={submitting || !value.trim()}
            className="inline-flex h-9 items-center rounded-md bg-slate-900 px-3 text-sm font-medium text-white shadow-sm hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
          >
            Go
          </button>
          <Link
            to="/entries/new"
            className="inline-flex h-9 items-center rounded-md border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            + New entry
          </Link>
        </div>
        {error && (
          <p role="alert" className="text-xs text-rose-700 dark:text-rose-300">
            {error}
          </p>
        )}
      </form>
    </section>
  );
}

function formatTargetDate(iso: string): string {
  const parts = iso.split("-");
  if (parts.length !== 3) return iso;
  const monthNum = Number.parseInt(parts[1] ?? "", 10);
  const dayNum = Number.parseInt(parts[2] ?? "", 10);
  if (!Number.isFinite(monthNum) || !Number.isFinite(dayNum)) return iso;
  const monthName =
    [
      "January", "February", "March", "April", "May", "June",
      "July", "August", "September", "October", "November", "December",
    ][monthNum - 1] ?? "";
  return `${monthName} ${dayNum}`;
}
