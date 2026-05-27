import { useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { CalendarGrid } from "@/components/CalendarGrid";
import { useCalendar } from "@/hooks/useEntries";
import { ApiError } from "@/lib/apiError";

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

export function CalendarPage(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const now = useMemo(() => new Date(), []);
  const yearParam = parseInt(searchParams.get("year") ?? "", 10);
  const monthParam = parseInt(searchParams.get("month") ?? "", 10);
  const year = Number.isFinite(yearParam) ? yearParam : now.getFullYear();
  const month =
    Number.isFinite(monthParam) && monthParam >= 1 && monthParam <= 12
      ? monthParam
      : now.getMonth() + 1;

  const calendar = useCalendar(year, month);

  function setYearMonth(nextYear: number, nextMonth: number): void {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.set("year", String(nextYear));
        next.set("month", String(nextMonth));
        return next;
      },
      { replace: false },
    );
  }

  function goToPrevMonth(): void {
    if (month === 1) setYearMonth(year - 1, 12);
    else setYearMonth(year, month - 1);
  }

  function goToNextMonth(): void {
    if (month === 12) setYearMonth(year + 1, 1);
    else setYearMonth(year, month + 1);
  }

  function goToToday(): void {
    setYearMonth(now.getFullYear(), now.getMonth() + 1);
  }

  function handleDayClick(isoDate: string): void {
    navigate(`/entries?from_date=${isoDate}&to_date=${isoDate}`);
  }

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold">Calendar</h1>
        <div className="text-sm text-slate-600 dark:text-slate-300">
          {MONTH_NAMES[month - 1]} {year}
        </div>
      </header>

      <div className="flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={goToPrevMonth}
          className="inline-flex h-9 items-center rounded-md border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
        >
          ← Previous month
        </button>
        <button
          type="button"
          onClick={goToToday}
          className="inline-flex h-9 items-center rounded-md bg-slate-900 px-3 text-sm font-medium text-white shadow-sm hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
        >
          Today
        </button>
        <button
          type="button"
          onClick={goToNextMonth}
          className="inline-flex h-9 items-center rounded-md border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
        >
          Next month →
        </button>
      </div>

      {calendar.isLoading ? (
        <div
          data-testid="calendar-loading"
          className="h-72 animate-pulse rounded-md bg-slate-100 dark:bg-slate-800"
        />
      ) : calendar.isError ? (
        <div
          role="alert"
          data-testid="calendar-error"
          className="space-y-3 rounded-md border border-rose-300 bg-rose-50 px-3 py-3 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-200"
        >
          <p>
            {calendar.error instanceof ApiError
              ? calendar.error.message
              : "Couldn't load this month."}
          </p>
          <button
            type="button"
            onClick={() => {
              void calendar.refetch();
            }}
            className="inline-flex h-8 items-center rounded-md bg-slate-900 px-3 text-xs font-medium text-white hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900"
          >
            Try again
          </button>
        </div>
      ) : (
        <CalendarGrid
          year={year}
          month={month}
          daysWithEntries={calendar.data?.days ?? []}
          today={now}
          onDayClick={handleDayClick}
        />
      )}

      <div className="text-xs text-slate-500 dark:text-slate-400">
        {calendar.data
          ? `${calendar.data.total} entr${calendar.data.total === 1 ? "y" : "ies"} this month.`
          : ""}
      </div>
    </div>
  );
}
