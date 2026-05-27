import type { AppliedFilters } from "@/types/api";

export type FilterKey = "q" | "book" | "tag" | "from_date" | "to_date";

interface AppliedFilterChipsProps {
  applied: AppliedFilters;
  onRemove: (key: FilterKey) => void;
}

const LABEL: Record<FilterKey, string> = {
  q: "search",
  book: "book",
  tag: "tag",
  from_date: "from",
  to_date: "to",
};

/**
 * Reflects the server's `applied_filters` echo as a row of removable
 * chips. Each chip has an ×; clicking it tells the parent to drop just
 * that filter via `onRemove(key)`. Renders nothing when no filters are
 * applied.
 */
export function AppliedFilterChips({
  applied,
  onRemove,
}: AppliedFilterChipsProps): JSX.Element | null {
  const items: { key: FilterKey; value: string }[] = [];
  if (applied.q) items.push({ key: "q", value: applied.q });
  if (applied.book) items.push({ key: "book", value: applied.book });
  if (applied.tag) items.push({ key: "tag", value: applied.tag });
  if (applied.from_date) items.push({ key: "from_date", value: applied.from_date });
  if (applied.to_date) items.push({ key: "to_date", value: applied.to_date });

  if (items.length === 0) return null;

  return (
    <div
      data-testid="applied-filter-chips"
      className="flex flex-wrap items-center gap-1"
    >
      <span className="mr-1 text-xs text-slate-500 dark:text-slate-400">
        Filtered by:
      </span>
      {items.map((item) => (
        <span
          key={item.key}
          className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-200"
        >
          <span className="font-medium">{LABEL[item.key]}:</span>
          <span>{item.value}</span>
          <button
            type="button"
            aria-label={`Remove ${LABEL[item.key]} filter`}
            onClick={() => onRemove(item.key)}
            className="rounded text-slate-500 hover:bg-slate-200 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-700 dark:hover:text-slate-100"
          >
            ×
          </button>
        </span>
      ))}
    </div>
  );
}
