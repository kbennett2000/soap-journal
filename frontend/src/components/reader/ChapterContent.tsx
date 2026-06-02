import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { isOmittedVerse } from "@/lib/bibleText";
import { buildVerseSegments } from "@/lib/verseSegments";
import type { FontSize, ReaderLayout } from "@/lib/storage";
import type {
  ChapterResponse,
  CrossRefResponse,
  FootnoteResponse,
  HeadingResponse,
  NoteType,
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

  // The open translator's note renders as a single panel at the article level
  // (never inside a verse <button>, so its cross-ref <Link>s aren't nested in a
  // button). Cleared when the chapter changes.
  const [openNote, setOpenNote] = useState<FootnoteResponse | null>(null);

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
          onNoteClick={setOpenNote}
        />
      ) : (
        <ParagraphLayout
          chapter={chapter}
          headingsByVerse={headingsByVerse}
          highlightRange={highlightRange}
          verseRef={verseRef}
          onVerseClick={onVerseClick}
          onNoteClick={setOpenNote}
        />
      )}
      {openNote && (
        <NoteView
          note={openNote}
          translationCode={chapter.translation_code}
          onClose={() => setOpenNote(null)}
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

// ---- translator's notes (NET) ---------------------------------------------

const NOTE_TYPE_LABELS: Record<NoteType, string> = {
  tn: "Translator's Note",
  sn: "Study Note",
  tc: "Text-Critical Note",
  map: "Map",
};

interface NoteMarkerProps {
  number: number;
  onClick: (event: React.MouseEvent) => void;
}

function NoteMarker({ number, onClick }: NoteMarkerProps): JSX.Element {
  return (
    <button
      type="button"
      data-testid="note-marker"
      aria-label={`Translator note ${number}`}
      onClick={onClick}
      className="mx-0.5 align-super text-xs font-medium text-sky-600 hover:underline dark:text-sky-400"
    >
      {number}
    </button>
  );
}

interface VerseBodyProps {
  verse: VerseResponse;
  onNoteClick: (note: FootnoteResponse) => void;
}

/**
 * Render verse text with typed-note markers interleaved at their char_offset,
 * followed by the end-of-verse FootnoteMarker for plain footnotes. For a verse
 * with no typed notes this is exactly the previous output (one text span +
 * FootnoteMarker over all footnotes), so plain translations are unchanged.
 */
function VerseBody({ verse, onNoteClick }: VerseBodyProps): JSX.Element {
  const parts = buildVerseSegments(verse.text, verse.footnotes);
  const plainFootnotes = verse.footnotes.filter((f) => f.char_offset === null);
  return (
    <>
      {parts.map((part, i) =>
        part.type === "text" ? (
          <span key={`text-${i}`}>{part.text}</span>
        ) : (
          <NoteMarker
            key={`note-${part.note.id}`}
            number={part.number}
            onClick={(event) => {
              // Don't let the marker trigger the verse's new-entry click.
              event.stopPropagation();
              onNoteClick(part.note);
            }}
          />
        ),
      )}
      <FootnoteMarker footnotes={plainFootnotes} />
    </>
  );
}

function crossRefUrl(translationCode: string, xr: CrossRefResponse): string {
  const end = xr.to_verse_end ?? xr.to_verse_start;
  return (
    `/read/${encodeURIComponent(translationCode)}` +
    `/${encodeURIComponent(xr.to_book)}/${xr.to_chapter}` +
    `?range=${xr.to_verse_start}-${end}`
  );
}

function crossRefLabel(xr: CrossRefResponse): string {
  const base = `${xr.to_book} ${xr.to_chapter}:${xr.to_verse_start}`;
  return xr.to_verse_end ? `${base}-${xr.to_verse_end}` : base;
}

interface NoteViewProps {
  note: FootnoteResponse;
  translationCode: string;
  onClose: () => void;
}

function NoteView({ note, translationCode, onClose }: NoteViewProps): JSX.Element {
  const label = note.note_type ? NOTE_TYPE_LABELS[note.note_type] : "Note";
  return (
    <aside
      role="note"
      data-testid="note-view"
      className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-3 text-sm dark:border-slate-700 dark:bg-slate-800"
    >
      <div className="mb-1 flex items-center justify-between">
        <span
          data-testid="note-type"
          className="text-xs font-semibold uppercase tracking-wide text-sky-700 dark:text-sky-300"
        >
          {label}
        </span>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close note"
          className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
        >
          ×
        </button>
      </div>
      <p className="whitespace-pre-wrap text-slate-700 dark:text-slate-200">{note.text}</p>
      {note.cross_refs.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2" data-testid="note-cross-refs">
          {note.cross_refs.map((xr, i) => (
            <Link
              key={`${xr.to_book}-${xr.to_chapter}-${xr.to_verse_start}-${i}`}
              to={crossRefUrl(translationCode, xr)}
              className="rounded border border-sky-200 bg-white px-2 py-0.5 text-xs text-sky-700 hover:bg-sky-50 dark:border-sky-800 dark:bg-slate-900 dark:text-sky-300"
            >
              {crossRefLabel(xr)}
            </Link>
          ))}
        </div>
      )}
    </aside>
  );
}

// ---- layouts --------------------------------------------------------------

interface LayoutProps {
  chapter: ChapterResponse;
  headingsByVerse: Map<number, HeadingResponse[]>;
  highlightRange?: { start: number; end: number };
  verseRef: (el: HTMLElement | null) => void;
  onVerseClick: (verse: VerseResponse) => void;
  onNoteClick: (note: FootnoteResponse) => void;
}

function VerseLayout({
  chapter,
  headingsByVerse,
  highlightRange,
  verseRef,
  onVerseClick,
  onNoteClick,
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
              <VerseBody verse={verse} onNoteClick={onNoteClick} />
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
  onNoteClick,
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
        <VerseBody verse={verse} onNoteClick={onNoteClick} />
      </button>,
    );
    buffer.push(" ");
  }
  flush();

  return <div className="space-y-2">{nodes}</div>;
}
