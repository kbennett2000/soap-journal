import { Link } from "react-router-dom";

import { ApiError } from "@/lib/apiError";

interface ChapterErrorProps {
  error: unknown;
  onRetry: () => void;
}

export function ChapterError({ error, onRetry }: ChapterErrorProps): JSX.Element {
  const message =
    error instanceof ApiError ? error.message : "Unable to load this passage.";
  const isNotFound = error instanceof ApiError && error.status === 404;
  return (
    <div
      role="alert"
      className="space-y-3 rounded-md border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-200"
    >
      <p>{isNotFound ? "Unable to load this passage." : message}</p>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex h-8 items-center rounded-md bg-slate-900 px-3 text-xs font-medium text-white hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900"
        >
          Try again
        </button>
        <Link
          to="/read/BSB/Genesis/1"
          className="inline-flex h-8 items-center rounded-md border border-slate-300 px-3 text-xs font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          Go to Genesis 1
        </Link>
      </div>
    </div>
  );
}
