import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { resolveReference } from "@/lib/bible";
import { ApiError } from "@/lib/apiError";
import type { ResolvedReference } from "@/types/api";

interface ScripturePreviewProps {
  scriptureRef: string;
  translationCode: string;
  onResolved?: (resolved: ResolvedReference) => void;
}

const DEBOUNCE_MS = 400;

/**
 * Auto-pulls Scripture text as the user types. Debounces the input
 * (~400ms) before issuing the resolve. Caches via TanStack Query so the
 * same input doesn't refetch.
 */
export function EntryFormScripturePreview({
  scriptureRef,
  translationCode,
  onResolved,
}: ScripturePreviewProps): JSX.Element | null {
  const trimmed = scriptureRef.trim();
  const [debouncedRef, setDebouncedRef] = useState(trimmed);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedRef(trimmed), DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [trimmed]);

  const query = useQuery({
    queryKey: ["bible", "resolve", debouncedRef, translationCode] as const,
    queryFn: () => resolveReference(debouncedRef, translationCode),
    enabled: debouncedRef.length > 0,
    staleTime: Infinity,
    retry: false,
  });

  // Forward successful resolution to the parent (e.g. so the form can
  // capture the canonical string for analytics later). Effect rather
  // than render-time call to keep the contract pure.
  useEffect(() => {
    if (query.data && onResolved) {
      onResolved(query.data.reference);
    }
  }, [query.data, onResolved]);

  if (!trimmed) return null;

  const isFetching = trimmed !== debouncedRef || query.isFetching;

  if (isFetching && !query.data && !query.isError) {
    return (
      <div
        data-testid="scripture-preview-loading"
        className="mt-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400"
      >
        Looking up reference…
      </div>
    );
  }

  if (query.isError) {
    const message =
      query.error instanceof ApiError ? query.error.message : "Unable to resolve reference.";
    return (
      <div
        role="alert"
        data-testid="scripture-preview-error"
        className="mt-2 rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-200"
      >
        {message}
      </div>
    );
  }

  if (query.data) {
    const text = query.data.verses
      .map((v) => `${v.number} ${v.text}`)
      .join(" ");
    return (
      <div
        data-testid="scripture-preview"
        className="mt-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
      >
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {query.data.reference.canonical_string}
        </div>
        <div className="max-h-64 overflow-y-auto whitespace-pre-wrap leading-7">
          {text || "(no verses returned)"}
        </div>
      </div>
    );
  }

  return null;
}
