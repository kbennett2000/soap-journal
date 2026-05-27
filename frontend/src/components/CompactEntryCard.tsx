import { Link } from "react-router-dom";

import type { EntryResponse } from "@/types/api";

interface CompactEntryCardProps {
  entry: EntryResponse;
  showYear?: boolean;
}

/**
 * Denser variant of EntryCard for the dashboard sections and the
 * passage-entries panel. Single-line title link + a metadata row;
 * no observation preview, no tag pills.
 */
export function CompactEntryCard({
  entry,
  showYear = false,
}: CompactEntryCardProps): JSX.Element {
  const dateText = showYear ? formatYearFirst(entry.entry_date) : entry.entry_date;
  return (
    <Link
      to={`/entries/${entry.id}`}
      className="block rounded-md border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm transition-colors hover:border-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-slate-600 dark:hover:bg-slate-800"
    >
      <div className="truncate font-medium text-slate-900 dark:text-slate-100">
        {entry.display_title}
      </div>
      <div className="mt-0.5 truncate text-xs text-slate-500 dark:text-slate-400">
        {entry.scripture_ref} · {dateText}
      </div>
    </Link>
  );
}

function formatYearFirst(isoDate: string): string {
  // "2024-05-26" -> "2024 · May 26" (year first per spec's "year
  // prominent in the metadata" guidance for on-this-day).
  const parts = isoDate.split("-");
  if (parts.length !== 3) return isoDate;
  const [year, monthStr, dayStr] = parts;
  if (!year || !monthStr || !dayStr) return isoDate;
  const monthNum = Number.parseInt(monthStr, 10);
  const dayNum = Number.parseInt(dayStr, 10);
  if (!Number.isFinite(monthNum) || !Number.isFinite(dayNum)) return isoDate;
  const monthName = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ][monthNum - 1] ?? monthStr;
  return `${year} · ${monthName} ${dayNum}`;
}
