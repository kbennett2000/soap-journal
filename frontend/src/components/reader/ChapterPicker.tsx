interface ChapterPickerProps {
  chapterCount: number;
  currentChapter: number;
  onChange: (chapter: number) => void;
}

export function ChapterPicker({
  chapterCount,
  currentChapter,
  onChange,
}: ChapterPickerProps): JSX.Element {
  const safeCount = Math.max(chapterCount, 1);
  return (
    <select
      aria-label="Chapter"
      value={currentChapter}
      onChange={(e) => onChange(Number(e.target.value))}
      className="h-9 rounded-md border border-slate-300 bg-white px-2 text-sm text-slate-700 shadow-sm focus:outline-none focus:ring-1 focus:ring-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
    >
      {Array.from({ length: safeCount }, (_, i) => i + 1).map((n) => (
        <option key={n} value={n}>
          {n}
        </option>
      ))}
    </select>
  );
}
