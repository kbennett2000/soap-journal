import type { CalendarDay } from "@/types/api";

interface CalendarGridProps {
  year: number;
  month: number; // 1-12
  daysWithEntries: CalendarDay[];
  today?: Date;
  onDayClick: (isoDate: string) => void;
}

const DAY_LABELS = ["S", "M", "T", "W", "T", "F", "S"];

/**
 * Standard 7-column month grid, Sunday-first.
 *
 * Renders days from the previous and next months as muted cells so the
 * week alignment is intact. Only days in the current month with at
 * least one entry are clickable; clicking calls `onDayClick(isoDate)`.
 */
export function CalendarGrid({
  year,
  month,
  daysWithEntries,
  today = new Date(),
  onDayClick,
}: CalendarGridProps): JSX.Element {
  const countByDate = new Map<string, number>();
  for (const day of daysWithEntries) {
    countByDate.set(day.entry_date, day.count);
  }

  const firstOfMonth = new Date(year, month - 1, 1);
  const daysInMonth = new Date(year, month, 0).getDate();
  const startWeekday = firstOfMonth.getDay(); // 0 = Sun
  const totalCells = Math.ceil((startWeekday + daysInMonth) / 7) * 7;

  const todayIso = isoDate(today);

  const cells: JSX.Element[] = [];
  for (let i = 0; i < totalCells; i += 1) {
    const dayOffset = i - startWeekday + 1;
    const cellDate = new Date(year, month - 1, dayOffset);
    const inMonth = cellDate.getMonth() === month - 1;
    const cellIso = isoDate(cellDate);
    const count = countByDate.get(cellIso) ?? 0;
    const isToday = cellIso === todayIso;

    cells.push(
      <CalendarCell
        key={cellIso}
        date={cellDate}
        isoDate={cellIso}
        inMonth={inMonth}
        count={count}
        isToday={isToday}
        onClick={count > 0 && inMonth ? () => onDayClick(cellIso) : undefined}
      />,
    );
  }

  return (
    <div data-testid="calendar-grid" className="space-y-1">
      <div className="grid grid-cols-7 gap-1 text-center text-xs font-semibold text-slate-500 dark:text-slate-400">
        {DAY_LABELS.map((label, idx) => (
          <div key={`${idx}-${label}`} aria-hidden>
            {label}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-1">{cells}</div>
    </div>
  );
}

interface CalendarCellProps {
  date: Date;
  isoDate: string;
  inMonth: boolean;
  count: number;
  isToday: boolean;
  onClick?: () => void;
}

function CalendarCell({
  date,
  isoDate,
  inMonth,
  count,
  isToday,
  onClick,
}: CalendarCellProps): JSX.Element {
  const baseClass =
    "relative flex aspect-square min-h-[2.5rem] flex-col items-center justify-center rounded-md text-sm";
  const inMonthClass = inMonth
    ? "bg-white text-slate-800 dark:bg-slate-900 dark:text-slate-100"
    : "bg-slate-50 text-slate-400 dark:bg-slate-800 dark:text-slate-600";
  const todayClass = isToday
    ? " ring-2 ring-slate-900 dark:ring-slate-100"
    : "";
  const clickableClass = onClick
    ? " cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800"
    : "";
  const className = `${baseClass} ${inMonthClass}${todayClass}${clickableClass}`;

  const dayNumber = date.getDate();
  const content = (
    <>
      <span className="leading-none">{dayNumber}</span>
      {count > 0 && (
        <span
          data-testid={`day-badge-${isoDate}`}
          className="mt-0.5 inline-flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-slate-900 px-1 text-[10px] font-semibold text-white dark:bg-slate-100 dark:text-slate-900"
        >
          {count}
        </span>
      )}
    </>
  );

  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        data-testid={`day-${isoDate}`}
        aria-label={`${isoDate}, ${count} entr${count === 1 ? "y" : "ies"}`}
        className={className}
      >
        {content}
      </button>
    );
  }
  return (
    <div data-testid={`day-${isoDate}`} className={className}>
      {content}
    </div>
  );
}

function isoDate(date: Date): string {
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}
