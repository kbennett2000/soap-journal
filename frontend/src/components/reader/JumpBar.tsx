import { type FormEvent, useState } from "react";

import { resolveReference } from "@/lib/bible";
import { ApiError } from "@/lib/apiError";
import type { ResolvedReference } from "@/types/api";

interface JumpBarProps {
  translationCode: string;
  onResolved: (reference: ResolvedReference) => void;
}

/**
 * Single text input + submit. The frontend doesn't try to validate
 * reference syntax — it sends the user's input as-is and surfaces the
 * server's structured error message inline on failure.
 */
export function JumpBar({ translationCode, onResolved }: JumpBarProps): JSX.Element {
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!value.trim()) return;
    setError(null);
    setSubmitting(true);
    try {
      const response = await resolveReference(value.trim(), translationCode);
      onResolved(response.reference);
      // Keep the input value — the user might want to tweak it.
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
    <form onSubmit={handleSubmit} className="flex w-full min-w-0 flex-col gap-1">
      <div className="flex w-full min-w-0 items-center gap-2">
        <input
          type="text"
          aria-label="Jump to reference"
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            if (error) setError(null);
          }}
          placeholder='e.g. "John 3:16" or "Romans 8:28-30"'
          className="h-9 min-w-0 flex-1 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-700 shadow-sm focus:outline-none focus:ring-1 focus:ring-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
        />
        <button
          type="submit"
          disabled={submitting || !value.trim()}
          className="inline-flex h-9 items-center rounded-md bg-slate-900 px-3 text-sm font-medium text-white shadow-sm transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
        >
          Go
        </button>
      </div>
      {error && (
        <p
          role="alert"
          className="text-xs text-rose-700 dark:text-rose-300"
        >
          {error}
        </p>
      )}
    </form>
  );
}
