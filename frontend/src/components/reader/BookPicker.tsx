import type { BookSummary } from "@/types/api";

interface BookPickerProps {
  books: BookSummary[];
  currentBookName: string;
  onChange: (bookName: string) => void;
}

/**
 * Native `<select>` with optgroups separating OT and NT. Sorted by
 * canonical order_index, which the backend already returns.
 */
export function BookPicker({
  books,
  currentBookName,
  onChange,
}: BookPickerProps): JSX.Element {
  const ot = books.filter((b) => b.testament === "OT");
  const nt = books.filter((b) => b.testament === "NT");

  return (
    <select
      aria-label="Book"
      value={currentBookName}
      onChange={(e) => onChange(e.target.value)}
      className="h-9 rounded-md border border-slate-300 bg-white px-2 text-sm text-slate-700 shadow-sm focus:outline-none focus:ring-1 focus:ring-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
    >
      <optgroup label="Old Testament">
        {ot.map((b) => (
          <option key={b.name} value={b.name}>
            {b.name}
          </option>
        ))}
      </optgroup>
      <optgroup label="New Testament">
        {nt.map((b) => (
          <option key={b.name} value={b.name}>
            {b.name}
          </option>
        ))}
      </optgroup>
    </select>
  );
}
