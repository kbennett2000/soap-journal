import { useEffect, useMemo, useState } from "react";
import { Link, Navigate, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { BookPicker } from "@/components/reader/BookPicker";
import { ChapterContent } from "@/components/reader/ChapterContent";
import { ChapterError } from "@/components/reader/ChapterError";
import { ChapterPane } from "@/components/reader/ChapterPane";
import { ChapterPicker } from "@/components/reader/ChapterPicker";
import { ChapterSkeleton } from "@/components/reader/ChapterSkeleton";
import { JumpBar } from "@/components/reader/JumpBar";
import { PassageEntriesBadge } from "@/components/PassageEntriesBadge";
import { SettingsPopover } from "@/components/reader/SettingsPopover";
import { TranslationPicker } from "@/components/reader/TranslationPicker";
import { useChapter, useTranslationDetail, useTranslations } from "@/hooks/useBible";
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
  TranslationSummary,
  VerseResponse,
} from "@/types/api";

const DEFAULT_LOCATION = {
  translationCode: "BSB",
  bookName: "Genesis",
  chapterNumber: 1,
} as const;

export function ReaderPage(): JSX.Element {
  const params = useParams<{
    translationCode?: string;
    bookName?: string;
    chapterNumber?: string;
  }>();

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

  const parsedRange = useMemo(() => parseRange(searchParams.get("range")), [searchParams]);
  const [highlightFaded, setHighlightFaded] = useState(false);

  const compareCode = searchParams.get("compare");
  const isCompareMode = compareCode !== null && compareCode.length > 0;
  const translations = translationsQuery.data?.translations ?? [];

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setHighlightFaded(false);
    if (!parsedRange) return;
    const timer = window.setTimeout(() => setHighlightFaded(true), 3000);
    return () => window.clearTimeout(timer);
  }, [parsedRange]);

  const highlightRange = parsedRange && !highlightFaded ? parsedRange : undefined;

  useEffect(() => {
    writeLastLocation({ translationCode, bookName, chapterNumber });
  }, [translationCode, bookName, chapterNumber]);

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
    const params = new URLSearchParams();
    if (range) params.set("range", `${range.start}-${range.end}`);
    const currentCompare = searchParams.get("compare");
    if (currentCompare) params.set("compare", currentCompare);
    const search = params.toString() ? `?${params.toString()}` : "";
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
    navigateTo(translationCode, pointer.book_name, pointer.chapter_number);
  }

  function handleVerseClick(verse: VerseResponse, paneCode?: string): void {
    const code = paneCode ?? translationCode;
    navigate("/entries/new", {
      state: {
        scriptureRef: `${bookName} ${chapterNumber}:${verse.number}`,
        translationCode: code,
      },
    });
  }

  function handleTranslationChange(newCode: string): void {
    if (isCompareMode && newCode === compareCode) {
      const next = new URLSearchParams(searchParams);
      next.set("compare", translationCode);
      navigate(
        `/read/${encodeURIComponent(newCode)}/${encodeURIComponent(bookName)}/${chapterNumber}?${next.toString()}`,
      );
      return;
    }
    navigateTo(newCode, bookName, chapterNumber);
  }

  function handleCompare(): void {
    const other = translations.find((t) => t.code !== translationCode);
    if (!other) return;
    const next = new URLSearchParams(searchParams);
    next.set("compare", other.code);
    setSearchParams(next, { replace: true });
  }

  function handleCompareTranslationChange(newCode: string): void {
    if (newCode === translationCode) {
      const next = new URLSearchParams(searchParams);
      next.set("compare", translationCode);
      navigate(
        `/read/${encodeURIComponent(compareCode!)}/${encodeURIComponent(bookName)}/${chapterNumber}?${next.toString()}`,
      );
      return;
    }
    const next = new URLSearchParams(searchParams);
    next.set("compare", newCode);
    setSearchParams(next, { replace: true });
  }

  function handleCloseCompare(): void {
    const next = new URLSearchParams(searchParams);
    next.delete("compare");
    setSearchParams(next, { replace: true });
  }

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
        translations={translations}
        books={books}
        currentBookName={bookName}
        currentChapter={chapterNumber}
        currentBookChapterCount={currentBook?.chapter_count ?? 1}
        fontSize={fontSize}
        layout={layout}
        translationsLoaded={translationsQuery.isSuccess}
        isCompareMode={isCompareMode}
        onBookChange={handleBookChange}
        onChapterChange={handleChapterChange}
        onResolved={handleResolved}
        onChangeFontSize={setFontSize}
        onChangeLayout={setLayout}
        onTranslationChange={handleTranslationChange}
        onCompare={handleCompare}
      />

      {isCompareMode ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <ChapterPane
            translationCode={translationCode}
            bookName={bookName}
            chapterNumber={chapterNumber}
            layout={layout}
            fontSize={fontSize}
            highlightRange={highlightRange}
            translations={translations}
            onTranslationChange={handleTranslationChange}
            onVerseClick={handleVerseClick}
            label="Primary translation"
          />
          <ChapterPane
            translationCode={compareCode!}
            bookName={bookName}
            chapterNumber={chapterNumber}
            layout={layout}
            fontSize={fontSize}
            highlightRange={highlightRange}
            translations={translations}
            onTranslationChange={handleCompareTranslationChange}
            onVerseClick={handleVerseClick}
            onClose={handleCloseCompare}
            label="Comparison translation"
          />
        </div>
      ) : (
        <>
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
            <PassageEntriesBadge
              key={`${translationCode}/${bookName}/${chapterNumber}`}
              passageRef={`${bookName} ${chapterNumber}`}
              translationCode={translationCode}
            />
          )}

          {chapterQuery.data && (
            <ChapterContent
              chapter={chapterQuery.data}
              layout={layout}
              fontSize={fontSize}
              highlightRange={highlightRange}
              onVerseClick={(v) => handleVerseClick(v)}
            />
          )}
        </>
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
  translations: TranslationSummary[];
  books: BookSummary[];
  currentBookName: string;
  currentChapter: number;
  currentBookChapterCount: number;
  fontSize: FontSize;
  layout: ReaderLayout;
  translationsLoaded: boolean;
  isCompareMode: boolean;
  onBookChange: (name: string) => void;
  onChapterChange: (chapter: number) => void;
  onResolved: (reference: ResolvedReference) => void;
  onChangeFontSize: (size: FontSize) => void;
  onChangeLayout: (layout: ReaderLayout) => void;
  onTranslationChange: (code: string) => void;
  onCompare: () => void;
}

function ControlsBar(props: ControlsBarProps): JSX.Element {
  const compareDisabled = props.translations.length < 2;
  const compareTitle = compareDisabled
    ? "Compare translations becomes available when a second translation is loaded — see the README for instructions."
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
      <TranslationPicker
        translations={props.translations}
        currentCode={props.translationCode}
        onChange={props.onTranslationChange}
      />
      <Link
        to={`/read/search?translation=${encodeURIComponent(props.translationCode)}`}
        aria-label="Search scripture"
        data-testid="scripture-search-link"
        className="inline-flex h-9 items-center gap-1 rounded-md border border-slate-300 bg-white px-3 text-xs font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
      >
        🔍 Search Scripture
      </Link>
      {!props.isCompareMode && (
        <button
          type="button"
          disabled={compareDisabled}
          title={compareTitle}
          aria-label="Compare translations"
          onClick={props.onCompare}
          className={`inline-flex h-9 items-center rounded-md border px-3 text-xs font-medium ${
            compareDisabled
              ? "border-slate-200 bg-slate-50 text-slate-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-500"
              : "border-slate-300 bg-white text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
          }`}
        >
          Compare translations
        </button>
      )}
      <SettingsPopover
        fontSize={props.fontSize}
        layout={props.layout}
        onChangeFontSize={props.onChangeFontSize}
        onChangeLayout={props.onChangeLayout}
      />
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
