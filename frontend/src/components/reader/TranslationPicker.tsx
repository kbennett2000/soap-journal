import type { TranslationSummary } from "@/types/api";

interface TranslationPickerProps {
  translations: TranslationSummary[];
  currentCode: string;
  onChange: (code: string) => void;
  ariaLabel?: string;
}

export function TranslationPicker({
  translations,
  currentCode,
  onChange,
  ariaLabel = "Translation",
}: TranslationPickerProps): JSX.Element {
  if (translations.length <= 1) {
    return (
      <span
        data-testid="translation-pill"
        className="inline-flex h-9 items-center rounded-md border border-slate-200 bg-slate-50 px-2 text-xs font-semibold text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
      >
        {currentCode}
      </span>
    );
  }

  return (
    <select
      aria-label={ariaLabel}
      value={currentCode}
      onChange={(e) => onChange(e.target.value)}
      className="h-9 rounded-md border border-slate-300 bg-white px-2 text-sm text-slate-700 shadow-sm focus:outline-none focus:ring-1 focus:ring-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
    >
      {translations.map((t) => (
        <option key={t.code} value={t.code}>
          {t.code} — {t.name}
        </option>
      ))}
    </select>
  );
}
