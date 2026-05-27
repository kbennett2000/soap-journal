import { useState } from "react";

import { CompactEntryCard } from "@/components/CompactEntryCard";
import { usePassageEntries } from "@/hooks/usePassageEntries";

interface PassageEntriesBadgeProps {
  /** Canonical chapter ref: e.g. `"John 3"`. */
  passageRef: string;
  translationCode: string;
}

/**
 * Reader's "you have N journal entries on this passage" badge.
 * Renders nothing when count is 0. Click the badge to expand an
 * inline panel listing the matching entries; click again to collapse.
 *
 * The parent (ReaderPage) should remount this on chapter change so the
 * panel state doesn't bleed between chapters.
 */
export function PassageEntriesBadge({
  passageRef,
  translationCode,
}: PassageEntriesBadgeProps): JSX.Element | null {
  const [open, setOpen] = useState(false);
  const query = usePassageEntries(passageRef, translationCode);

  // The query is enabled whenever the ref is non-empty; while loading
  // or errored we render nothing (the badge is informational and
  // shouldn't push a layout shift before the count is known).
  if (!query.data || query.data.count === 0) return null;
  const count = query.data.count;
  const label = `${count} ${count === 1 ? "entry" : "entries"} on this chapter`;

  return (
    <div data-testid="passage-entries-badge">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls="passage-entries-panel"
        className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-4 w-4"
          aria-hidden
        >
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
        </svg>
        <span>{label}</span>
        <span aria-hidden className="text-slate-500 dark:text-slate-400">
          {open ? "▾" : "▸"}
        </span>
      </button>
      {open && (
        <div
          id="passage-entries-panel"
          className="mt-2 space-y-2 rounded-md border border-slate-200 bg-white p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900"
        >
          {query.data.entries.map((entry) => (
            <CompactEntryCard key={entry.id} entry={entry} />
          ))}
        </div>
      )}
    </div>
  );
}
