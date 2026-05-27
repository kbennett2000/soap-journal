import { ChapterContent } from "@/components/reader/ChapterContent";
import { ChapterError } from "@/components/reader/ChapterError";
import { ChapterSkeleton } from "@/components/reader/ChapterSkeleton";
import { TranslationPicker } from "@/components/reader/TranslationPicker";
import { useChapter } from "@/hooks/useBible";
import type { FontSize, ReaderLayout } from "@/lib/storage";
import type { TranslationSummary, VerseResponse } from "@/types/api";

interface ChapterPaneProps {
  translationCode: string;
  bookName: string;
  chapterNumber: number;
  layout: ReaderLayout;
  fontSize: FontSize;
  highlightRange?: { start: number; end: number };
  translations: TranslationSummary[];
  onTranslationChange: (code: string) => void;
  onVerseClick: (verse: VerseResponse, translationCode: string) => void;
  onClose?: () => void;
  label: string;
}

export function ChapterPane({
  translationCode,
  bookName,
  chapterNumber,
  layout,
  fontSize,
  highlightRange,
  translations,
  onTranslationChange,
  onVerseClick,
  onClose,
  label,
}: ChapterPaneProps): JSX.Element {
  const chapterQuery = useChapter(translationCode, bookName, chapterNumber);

  function handleVerseClick(verse: VerseResponse): void {
    onVerseClick(verse, translationCode);
  }

  return (
    <section aria-label={label} className="min-w-0 flex-1">
      <div className="mb-2 flex items-center gap-2">
        <TranslationPicker
          translations={translations}
          currentCode={translationCode}
          onChange={onTranslationChange}
          ariaLabel={label}
        />
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Close comparison"
            className="inline-flex h-9 items-center rounded-md border border-slate-300 bg-white px-2 text-sm text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            ✕
          </button>
        )}
      </div>

      {chapterQuery.isLoading && <ChapterSkeleton />}

      {chapterQuery.isError && (
        <ChapterError
          error={chapterQuery.error}
          onRetry={() => {
            void chapterQuery.refetch();
          }}
        />
      )}

      {chapterQuery.data && (
        <ChapterContent
          chapter={chapterQuery.data}
          layout={layout}
          fontSize={fontSize}
          highlightRange={highlightRange}
          onVerseClick={handleVerseClick}
        />
      )}
    </section>
  );
}
