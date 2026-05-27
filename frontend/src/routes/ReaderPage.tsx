import { useEffect, useMemo, useState } from "react";
import { Link, Navigate, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { BookPicker } from "@/components/reader/BookPicker";
import { ChapterPicker } from "@/components/reader/ChapterPicker";
import { ChapterContent } from "@/components/reader/ChapterContent";
import { JumpBar } from "@/components/reader/JumpBar";
import { SettingsPopover } from "@/components/reader/SettingsPopover";
import { useChapter, useTranslationDetail, useTranslations } from "@/hooks/useBible";
import { ApiError } from "@/lib/apiError";
import {
  readFontSize,
  readLastLocation,
  readLayout,
  writeFontSize,
  writeLastLocation,
  writeLayout,
  type FontSize,
  type ReaderLayout,
} from "@/lib/storage";
import type {
  BookSummary,
  ChapterPointer,
  ResolvedReference,
  VerseResponse,
} from "@/types/api";

const DEFAULT_LOCATION = {
  translationCode: "BSB",
  bookName: "Genesis",
  chapterNumber: 1,
} as const;

/**
 * URL is the source of truth for "what am I reading."
 * Bare /read redirects to last-read (or DEFAULT_LOCATION) so the user
 * lands somewhere meaningful. ?range=16-20 highlights + scrolls.
 */
export function ReaderPage(): JSX.Element {
  const params = useParams<{
    translationCode?: string;
    bookName?: string;
    chapterNumber?: string;
  }>();

  // Bare /read: redirect to last-known location or DEFAULT_LOCATION.
  if (!params.translationCode || !params.bookName || !params.chapterNumber) {
    const target = readLastLocation() ?? DEFAULT_LOCATION;
    return (
      <Navigate
        to={`/read/${encodeURIComponent(target.translationCode)}/${encodeURIComponent(
          target.bookName,
        )}/${target.chapterNumber}`}
        replace
      />
    );
  }

  const chapterNumber = Number(params.chapterNumber);
  if (!Number.isFinite(chapterNumber) || chapterNumber < 1) {
    return <Navigate to="/read" replace />;
  }

  return (
    <ReaderInner
      translationCode={params.translationCode}
      bookName={params.bookName}
      chapterNumber={chapterNumber}
    />
  );
}

interface ReaderInnerProps {
  translationCode: string;
  bookName: string;
  chapterNumber: number;
}

function ReaderInner({
  translationCode,
  bookName,
  chapterNumber,
}: ReaderInnerProps): JSX.Element {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const translationsQuery = useTranslations();
  const translationDetailQuery = useTranslationDetail(translationCode);
  const chapterQuery = useChapter(translationCode, bookName, chapterNumber);

  const [fontSize, setFontSize] = useState<FontSize>(() => readFontSize());
  const [layout, setLayout] = useState<ReaderLayout>(() => readLayout());

  // Parse ?range=16-20 as a memo from the URL. Anything malformed is
  // ignored. Memoized so the fade-timer effect below has a stable
  // dependency.
  const parsedRange = useMemo(() => parseRange(searchParams.get("range")), [searchParams]);
  const [highlightFaded, setHighlightFaded] = useState(false);

  useEffect(() => {
    // Intentional: a new range starts un-faded; the timer fades it back
    // to undefined after 3s. The lint rule discourages setState inside
    // an effect to prevent accidental cascading renders, but here the
    // cascade IS the behavior we want — reset on URL change.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setHighlightFaded(false);
    if (!parsedRange) return;
    const timer = window.setTimeout(() => setHighlightFaded(true), 3000);
    return () => window.clearTimeout(timer);
  }, [parsedRange]);

  const highlightRange = parsedRange && !highlightFaded ? parsedRange : undefined;

  // Persist last-read location so bare /read can resume the user.
  useEffect(() => {
    writeLastLocation({ translationCode, bookName, chapterNumber });
  }, [translationCode, bookName, chapterNumber]);

  // Settings persistence.
  useEffect(() => {
    writeFontSize(fontSize);
  }, [fontSize]);
  useEffect(() => {
    writeLayout(layout);
  }, [layout]);

  const books: BookSummary[] = translationDetailQuery.data?.books ?? [];
  const currentBook = useMemo(
    () => translationDetailQuery.data?.books.find((b) => b.name === bookName),
    [translationDetailQuery.data, bookName],
  );

  function navigateTo(
    code: string,
    book: string,
    chapter: number,
    range?: { start: number; end: number },
  ): void {
    const search = range ? `?range=${range.start}-${range.end}` : "";
    navigate(
      `/read/${encodeURIComponent(code)}/${encodeURIComponent(book)}/${chapter}${search}`,
    );
  }

  function handleBookChange(nextBookName: string): void {
    navigateTo(translationCode, nextBookName, 1);
  }

  function handleChapterChange(nextChapter: number): void {
    navigateTo(translationCode, bookName, nextChapter);
  }

  function handleResolved(reference: ResolvedReference): void {
    navigateTo(reference.translation_code, reference.book.name, reference.chapter_number, {
      start: reference.start_verse,
      end: reference.end_verse,
    });
  }

  function handlePointer(pointer: ChapterPointer | null): void {
    if (!pointer) return;
    setSearchParams({}, { replace: true });
    navigateTo(translationCode, pointer.book_name, pointer.chapter_number);
  }

  function handleVerseClick(verse: VerseResponse): void {
    // Hop to the new-entry form with the verse pre-filled. The form's
    // ScripturePreview auto-pulls the text from the same ref.
    navigate("/entries/new", {
      state: {
        scriptureRef: `${bookName} ${chapterNumber}:${verse.number}`,
        translationCode,
      },
    });
  }

  // Keyboard navigation: left/right arrows for prev/next chapter. Skip
  // when focus is inside a form field so the jump bar and settings stay
  // usable.
  useEffect(() => {
    function onKey(event: KeyboardEvent): void {
      const target = event.target as HTMLElement | null;
      const tag = target?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (event.key === "ArrowLeft" && chapterQuery.data?.previous) {
        handlePointer(chapterQuery.data.previous);
      } else if (event.key === "ArrowRight" && chapterQuery.data?.next) {
        handlePointer(chapterQuery.data.next);
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chapterQuery.data?.previous, chapterQuery.data?.next]);

  return (
    <div className="space-y-4">
      <ControlsBar
        translationCode={translationCode}
        books={books}
        currentBookName={bookName}
        currentChapter={chapterNumber}
        currentBookChapterCount={currentBook?.chapter_count ?? 1}
        fontSize={fontSize}
        layout={layout}
        translationsLoaded={translationsQuery.isSuccess}
        translationsCount={translationsQuery.data?.translations.length ?? 0}
        onBookChange={handleBookChange}
        onChapterChange={handleChapterChange}
        onResolved={handleResolved}
        onChangeFontSize={setFontSize}
        onChangeLayout={setLayout}
      />

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

      {chapterQuery.data && (
        <ChapterNav
          previous={chapterQuery.data.previous}
          next={chapterQuery.data.next}
          onNavigate={handlePointer}
        />
      )}

    </div>
  );
}

// ---- subcomponents --------------------------------------------------------

interface ControlsBarProps {
  translationCode: string;
  books: BookSummary[];
  currentBookName: string;
  currentChapter: number;
  currentBookChapterCount: number;
  fontSize: FontSize;
  layout: ReaderLayout;
  translationsLoaded: boolean;
  translationsCount: number;
  onBookChange: (name: string) => void;
  onChapterChange: (chapter: number) => void;
  onResolved: (reference: ResolvedReference) => void;
  onChangeFontSize: (size: FontSize) => void;
  onChangeLayout: (layout: ReaderLayout) => void;
}

function ControlsBar(props: ControlsBarProps): JSX.Element {
  const compareDisabled = props.translationsCount < 2;
  const compareTitle = compareDisabled
    ? "Compare translations becomes active when a second translation is loaded."
    : "Compare translations";
  return (
    <div className="flex flex-wrap items-start gap-2 rounded-md border border-slate-200 bg-white p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <BookPicker
        books={props.books}
        currentBookName={props.currentBookName}
        onChange={props.onBookChange}
      />
      <ChapterPicker
        chapterCount={props.currentBookChapterCount}
        currentChapter={props.currentChapter}
        onChange={props.onChapterChange}
      />
      <div className="min-w-[16rem] flex-1">
        <JumpBar
          translationCode={props.translationCode}
          onResolved={props.onResolved}
        />
      </div>
      <span className="inline-flex h-9 items-center rounded-md border border-slate-200 bg-slate-50 px-2 text-xs font-semibold text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
        {props.translationCode}
      </span>
      <button
        type="button"
        disabled
        title={compareTitle}
        aria-label="Compare translations"
        className="inline-flex h-9 items-center rounded-md border border-slate-200 bg-slate-50 px-3 text-xs font-medium text-slate-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-500"
      >
        Compare translations
      </button>
      <SettingsPopover
        fontSize={props.fontSize}
        layout={props.layout}
        onChangeFontSize={props.onChangeFontSize}
        onChangeLayout={props.onChangeLayout}
      />
    </div>
  );
}

function ChapterSkeleton(): JSX.Element {
  return (
    <div data-testid="chapter-skeleton" className="animate-pulse space-y-3">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="h-5 rounded bg-slate-200 dark:bg-slate-800" />
      ))}
    </div>
  );
}

interface ChapterErrorProps {
  error: unknown;
  onRetry: () => void;
}

function ChapterError({ error, onRetry }: ChapterErrorProps): JSX.Element {
  const message =
    error instanceof ApiError ? error.message : "Unable to load this passage.";
  const isNotFound = error instanceof ApiError && error.status === 404;
  return (
    <div
      role="alert"
      className="space-y-3 rounded-md border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-200"
    >
      <p>{isNotFound ? "Unable to load this passage." : message}</p>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex h-8 items-center rounded-md bg-slate-900 px-3 text-xs font-medium text-white hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900"
        >
          Try again
        </button>
        <Link
          to="/read/BSB/Genesis/1"
          className="inline-flex h-8 items-center rounded-md border border-slate-300 px-3 text-xs font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          Go to Genesis 1
        </Link>
      </div>
    </div>
  );
}

interface ChapterNavProps {
  previous: ChapterPointer | null;
  next: ChapterPointer | null;
  onNavigate: (pointer: ChapterPointer) => void;
}

function ChapterNav({ previous, next, onNavigate }: ChapterNavProps): JSX.Element {
  return (
    <nav className="flex items-center justify-between border-t border-slate-200 pt-4 dark:border-slate-700">
      <button
        type="button"
        onClick={() => previous && onNavigate(previous)}
        disabled={!previous}
        className="inline-flex h-9 items-center rounded-md border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
      >
        ← Previous{previous ? `: ${previous.book_name} ${previous.chapter_number}` : ""}
      </button>
      <button
        type="button"
        onClick={() => next && onNavigate(next)}
        disabled={!next}
        className="inline-flex h-9 items-center rounded-md border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
      >
        Next{next ? `: ${next.book_name} ${next.chapter_number}` : ""} →
      </button>
    </nav>
  );
}

// ---- helpers --------------------------------------------------------------

function parseRange(raw: string | null): { start: number; end: number } | undefined {
  if (!raw) return undefined;
  const match = /^(\d+)(?:-(\d+))?$/.exec(raw);
  if (!match) return undefined;
  const start = Number(match[1]);
  const end = match[2] ? Number(match[2]) : start;
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) {
    return undefined;
  }
  return { start, end };
}
