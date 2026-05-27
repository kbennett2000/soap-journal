import { useEffect, useRef, useState } from "react";

import { isOmittedVerse } from "@/lib/bibleText";
import type { FontSize, ReaderLayout } from "@/lib/storage";
import type {
  ChapterResponse,
  FootnoteResponse,
  HeadingResponse,
  VerseResponse,
} from "@/types/api";

const FONT_SIZE_CLASS: Record<FontSize, string> = {
  S: "text-sm leading-7",
  M: "text-base leading-8",
  L: "text-lg leading-9",
};

interface ChapterContentProps {
  chapter: ChapterResponse;
  layout: ReaderLayout;
  fontSize: FontSize;
  highlightRange?: { start: number; end: number };
  onVerseClick: (verse: VerseResponse) => void;
}

export function ChapterContent({
  chapter,
  layout,
  fontSize,
  highlightRange,
  onVerseClick,
}: ChapterContentProps): JSX.Element {
  // Group headings by the verse number they precede so renderers can
  // emit them inline at the right spot.
  const headingsByVerse = new Map<number, HeadingResponse[]>();
  for (const h of chapter.headings) {
    const list = headingsByVerse.get(h.before_verse) ?? [];
    list.push(h);
    headingsByVerse.set(h.before_verse, list);
  }

  const sizeClass = FONT_SIZE_CLASS[fontSize];
  const verseRef = useScrollToFirstHighlight(highlightRange?.start);

  return (
    <article
      data-testid="chapter-content"
      className={`prose prose-slate max-w-none dark:prose-invert ${sizeClass}`}
    >
      <h1 className="!mb-2 !mt-0 text-2xl font-semibold">
        {chapter.book.name} {chapter.chapter_number}
      </h1>
      {layout === "verse" ? (
        <VerseLayout
          chapter={chapter}
          headingsByVerse={headingsByVerse}
          highlightRange={highlightRange}
          verseRef={verseRef}
          onVerseClick={onVerseClick}
        />
      ) : (
        <ParagraphLayout
          chapter={chapter}
          headingsByVerse={headingsByVerse}
          highlightRange={highlightRange}
          verseRef={verseRef}
          onVerseClick={onVerseClick}
        />
      )}
    </article>
  );
}

// ---- helpers --------------------------------------------------------------

function useScrollToFirstHighlight(
  startVerse: number | undefined,
): (el: HTMLElement | null) => void {
  const ref = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (startVerse === undefined) return;
    if (ref.current) {
      ref.current.scrollIntoView({ block: "start", behavior: "smooth" });
    }
  }, [startVerse]);
  return (el) => {
    ref.current = el;
  };
}

function inHighlight(
  verseNumber: number,
  range: { start: number; end: number } | undefined,
): boolean {
  if (!range) return false;
  return verseNumber >= range.start && verseNumber <= range.end;
}

function verseClassNames(verse: VerseResponse, highlighted: boolean): string {
  const base = "rounded text-left transition-colors";
  const click = "cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800";
  const omitted = isOmittedVerse(verse)
    ? "italic text-slate-400 dark:text-slate-500"
    : "";
  const red = verse.is_red_letter ? "text-rose-700 dark:text-rose-300" : "";
  const hi = highlighted
    ? "bg-amber-100 dark:bg-amber-900/40"
    : "";
  return [base, click, omitted, red, hi].filter(Boolean).join(" ");
}

interface HeadingProps {
  heading: HeadingResponse;
}

function Heading({ heading }: HeadingProps): JSX.Element {
  return (
    <h2 className="!mb-2 !mt-6 text-lg font-semibold text-slate-700 dark:text-slate-200">
      {heading.text}
    </h2>
  );
}

interface FootnoteMarkerProps {
  footnotes: FootnoteResponse[];
}

function FootnoteMarker({ footnotes }: FootnoteMarkerProps): JSX.Element | null {
  const [open, setOpen] = useState(false);
  if (footnotes.length === 0) return null;
  return (
    <span className="relative inline-block align-super text-xs">
      <button
        type="button"
        aria-label="Footnote"
        onClick={(e) => {
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        className="text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
      >
        ⁿ
      </button>
      {open && (
        <span
          role="note"
          className="absolute left-1/2 z-10 mt-1 w-64 -translate-x-1/2 rounded border border-slate-200 bg-white p-2 text-xs text-slate-700 shadow-lg dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
        >
          {footnotes.map((f) => (
            <div key={f.id}>{f.text}</div>
          ))}
        </span>
      )}
    </span>
  );
}

// ---- layouts --------------------------------------------------------------

interface LayoutProps {
  chapter: ChapterResponse;
  headingsByVerse: Map<number, HeadingResponse[]>;
  highlightRange?: { start: number; end: number };
  verseRef: (el: HTMLElement | null) => void;
  onVerseClick: (verse: VerseResponse) => void;
}

function VerseLayout({
  chapter,
  headingsByVerse,
  highlightRange,
  verseRef,
  onVerseClick,
}: LayoutProps): JSX.Element {
  return (
    <div className="space-y-1">
      {chapter.verses.map((verse) => {
        const headings = headingsByVerse.get(verse.number) ?? [];
        const highlighted = inHighlight(verse.number, highlightRange);
        const isStart = highlightRange?.start === verse.number;
        return (
          <div key={verse.id}>
            {headings.map((h) => (
              <Heading key={`${h.before_verse}-${h.text}`} heading={h} />
            ))}
            <button
              type="button"
              ref={isStart ? verseRef : undefined}
              onClick={() => onVerseClick(verse)}
              data-testid={`verse-${verse.number}`}
              className={`block w-full px-2 py-1 ${verseClassNames(verse, highlighted)}`}
            >
              <span className="mr-2 inline-block min-w-[1.5rem] text-right font-semibold text-slate-400 dark:text-slate-500">
                {verse.number}
              </span>
              <span>{verse.text}</span>
              <FootnoteMarker footnotes={verse.footnotes} />
            </button>
          </div>
        );
      })}
    </div>
  );
}

function ParagraphLayout({
  chapter,
  headingsByVerse,
  highlightRange,
  verseRef,
  onVerseClick,
}: LayoutProps): JSX.Element {
  // Walk the chapter in order, emitting <h2> blocks where a heading
  // precedes a verse and accumulating verses into a running <p> in
  // between. Headings break the current paragraph so the page reads as
  // alternating prose paragraphs and section breaks.
  const nodes: React.ReactNode[] = [];
  let buffer: React.ReactNode[] = [];

  const flush = (): void => {
    if (buffer.length === 0) return;
    nodes.push(
      <p key={`p${nodes.length}`} className="leading-9">
        {buffer}
      </p>,
    );
    buffer = [];
  };

  for (const verse of chapter.verses) {
    const headings = headingsByVerse.get(verse.number) ?? [];
    if (headings.length) {
      flush();
      for (const h of headings) {
        nodes.push(<Heading key={`h${nodes.length}-${verse.number}`} heading={h} />);
      }
    }
    const highlighted = inHighlight(verse.number, highlightRange);
    const isStart = highlightRange?.start === verse.number;
    buffer.push(
      <button
        key={verse.id}
        type="button"
        ref={isStart ? verseRef : undefined}
        onClick={() => onVerseClick(verse)}
        data-testid={`verse-${verse.number}`}
        className={`inline ${verseClassNames(verse, highlighted)} px-1`}
      >
        <sup className="mr-1 font-semibold text-slate-400 dark:text-slate-500">
          {verse.number}
        </sup>
        <span>{verse.text}</span>
        <FootnoteMarker footnotes={verse.footnotes} />
      </button>,
    );
    buffer.push(" ");
  }
  flush();

  return <div className="space-y-2">{nodes}</div>;
}
