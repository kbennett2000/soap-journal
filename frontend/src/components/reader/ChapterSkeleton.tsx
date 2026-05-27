export function ChapterSkeleton(): JSX.Element {
  return (
    <div data-testid="chapter-skeleton" className="animate-pulse space-y-3">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="h-5 rounded bg-slate-200 dark:bg-slate-800" />
      ))}
    </div>
  );
}
