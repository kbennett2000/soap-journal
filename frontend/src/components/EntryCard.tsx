import { Link } from "react-router-dom";

import type { EntryResponse } from "@/types/api";

interface EntryCardProps {
  entry: EntryResponse;
}

export function EntryCard({ entry }: EntryCardProps): JSX.Element {
  return (
    <article className="rounded-md border border-slate-200 bg-white p-4 shadow-sm transition-colors hover:border-slate-300 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-slate-600">
      <Link
        to={`/entries/${entry.id}`}
        className="text-base font-semibold text-slate-900 hover:underline dark:text-slate-100"
      >
        {entry.display_title}
      </Link>
      <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
        {entry.scripture_ref} · {entry.entry_date} · {entry.translation_code}
      </div>
      {entry.observation && (
        <p className="mt-2 line-clamp-3 text-sm text-slate-700 dark:text-slate-300">
          {entry.observation}
        </p>
      )}
      {entry.tags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
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
    </article>
  );
}
