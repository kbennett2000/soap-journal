import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { isOmittedVerse } from "@/lib/bibleText";
import {
  HIGHLIGHT_COLORS,
  HIGHLIGHT_COLOR_LABELS,
  highlightVar,
} from "@/lib/highlightColors";
import {
  resolveSelection as liveResolveSelection,
  type VerseSelection,
} from "@/lib/selection";
import { buildVerseParts, type HighlightSpan } from "@/lib/verseSegments";
import type { FontSize, ReaderLayout } from "@/lib/storage";
import type {
  Annotation,
  AnnotationCreate,
  ChapterResponse,
  CrossRefResponse,
  FootnoteResponse,
  HeadingResponse,
  HighlightColor,
  NoteType,
  VerseResponse,
} from "@/types/api";

const FONT_SIZE_CLASS: Record<FontSize, string> = {
  S: "text-sm leading-7",
  M: "text-base leading-8",
  L: "text-lg leading-9",
};

// The verse-number control is the app's primary "new entry" action, so it must
// read as a real, adequately-sized, focusable target — not an invisible
// superscript (ADR-0005 Cycle 5b). It also needs a comfortable TOUCH target:
// below lg the hit area is enlarged (~40px), reverting to the compact desktop
// size at lg (5c-4). No long-press gesture — that collides with native touch
// text-selection.
const NUMBER_BUTTON_CLASS =
  "mr-2 inline-flex min-h-[2.5rem] min-w-[2.5rem] select-none items-center justify-center rounded px-1 align-baseline text-sm font-semibold text-slate-500 transition-colors hover:bg-slate-200 hover:text-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-500 lg:min-h-0 lg:min-w-[1.75rem] dark:text-slate-400 dark:hover:bg-slate-700 dark:hover:text-slate-100";

const NUMBER_BUTTON_INLINE_CLASS =
  "mr-1 select-none rounded px-2 py-1 align-super text-xs font-semibold text-slate-500 transition-colors hover:bg-slate-200 hover:text-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-500 lg:px-0.5 lg:py-0 dark:text-slate-400 dark:hover:bg-slate-700 dark:hover:text-slate-100";

interface ChapterContentProps {
  chapter: ChapterResponse;
  layout: ReaderLayout;
  fontSize: FontSize;
  highlightRange?: { start: number; end: number };
  onVerseClick: (verse: VerseResponse) => void;
  // ---- highlight layer (opt-in; omitted disables selection/render) --------
  /** Highlights to render; filtered here to the chapter's translation_code. */
  annotations?: Annotation[];
  onCreateHighlight?: (input: AnnotationCreate) => void;
  /** Open the edit panel for the annotations covering a clicked run (5c-3). */
  onOpenAnnotations?: (annotationIds: number[]) => void;
  /**
   * Route a clicked translator note up to the host's shared panel shell (5c-4,
   * primary pane). When omitted (compare panes / isolated tests), ChapterContent
   * renders NoteView INLINE exactly as in ADR-0004 — the no-regression branch.
   */
  onOpenNote?: (note: FootnoteResponse) => void;
  /** Injectable selection reader for tests; defaults to the live one. */
  resolveSelectionFn?: () => VerseSelection | null;
}

// The popover is only ever the create swatches now (5c-3 retired the remove
// popover — existing highlights open the AnnotationPanel instead).
interface PopoverState {
  selection: VerseSelection;
  top: number;
  left: number;
}

export function ChapterContent({
  chapter,
  layout,
  fontSize,
  highlightRange,
  onVerseClick,
  annotations,
  onCreateHighlight,
  onOpenAnnotations,
  onOpenNote,
  resolveSelectionFn = liveResolveSelection,
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

  // Translator notes: when the host provides `onOpenNote` (primary pane), route
  // the clicked note up into the shared shell; otherwise (compare panes /
  // isolated tests) keep the ADR-0004 inline NoteView via local `openNote`.
  const [openNote, setOpenNote] = useState<FootnoteResponse | null>(null);
  function handleNoteClick(note: FootnoteResponse): void {
    if (onOpenNote) onOpenNote(note);
    else setOpenNote(note);
  }

  // Highlights only render in the translation they were made in (inherited from
  // ADR-0004). The list query is already per-translation, but filter defensively
  // so a stale cross-translation row can never leak in.
  const chapterAnnotations = (annotations ?? []).filter(
    (a) => a.translation_code === chapter.translation_code,
  );
  const highlightLayerEnabled =
    onCreateHighlight !== undefined || onOpenAnnotations !== undefined;

  const [popover, setPopover] = useState<PopoverState | null>(null);

  function handleMouseUp(event: React.MouseEvent): void {
    if (!highlightLayerEnabled) return;
    const selection = resolveSelectionFn();
    // `rangeToVerseSelection` returns null for a collapsed selection, so any
    // non-null value is a real drag. (Don't gate on charEnd > charStart: across
    // verses those offsets index different verses and can be in any order.)
    if (selection) {
      // Single- OR multi-verse (within one chapter) → offer to create (5c-1).
      // `rangeToVerseSelection` already refuses selections that cross a chapter
      // boundary, so any non-null selection here is in-chapter.
      if (onCreateHighlight) {
        setPopover({
          selection,
          top: selection.rect.top,
          left: selection.rect.left,
        });
      } else {
        setPopover(null);
      }
      return;
    }
    // Collapsed click on an existing highlight (run or +N badge): open the edit
    // panel for the FULL covering set (data-highlight-ids), so overlapped
    // annotations underneath the top are reachable (5c-3).
    const target = event.target as HTMLElement;
    const hit = target.closest?.("[data-highlight-id]") as HTMLElement | null;
    if (hit && onOpenAnnotations) {
      const raw =
        hit.getAttribute("data-highlight-ids") ??
        hit.getAttribute("data-highlight-id") ??
        "";
      const ids = raw
        .split(",")
        .map((s) => Number(s))
        .filter((n) => Number.isFinite(n) && n > 0);
      if (ids.length > 0) {
        onOpenAnnotations(ids);
        return;
      }
    }
    setPopover(null);
  }

  function clearLiveSelection(): void {
    if (typeof window !== "undefined") {
      window.getSelection?.()?.removeAllRanges();
    }
  }

  function handlePickColor(color: HighlightColor): void {
    if (!popover || !onCreateHighlight) return;
    const sel = popover.selection;
    onCreateHighlight({
      translation_code: chapter.translation_code,
      book: chapter.book.name,
      chapter: chapter.chapter_number,
      verse_start: sel.verseStart,
      verse_end: sel.verseEnd,
      char_start: sel.charStart,
      char_end: sel.charEnd,
      color,
    });
    setPopover(null);
    clearLiveSelection();
  }

  return (
    <article
      data-testid="chapter-content"
      data-chapter={`${chapter.translation_code}/${chapter.book.name}/${chapter.chapter_number}`}
      onMouseUp={handleMouseUp}
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
          annotations={chapterAnnotations}
          verseRef={verseRef}
          onVerseClick={onVerseClick}
          onNoteClick={handleNoteClick}
        />
      ) : (
        <ParagraphLayout
          chapter={chapter}
          headingsByVerse={headingsByVerse}
          highlightRange={highlightRange}
          annotations={chapterAnnotations}
          verseRef={verseRef}
          onVerseClick={onVerseClick}
          onNoteClick={handleNoteClick}
        />
      )}
      {openNote && (
        <NoteView
          note={openNote}
          translationCode={chapter.translation_code}
          onClose={() => setOpenNote(null)}
        />
      )}
      {popover && (
        <SelectionPopover
          popover={popover}
          onPick={handlePickColor}
          onCancel={() => setPopover(null)}
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

/**
 * Tone classes for a verse container. The container is now selectable text
 * (not a button), so it carries no click/hover affordance — that lives on the
 * verse-number control. Range-highlight (navigation flash), red-letter, and
 * omitted-verse styling remain.
 */
function verseToneClasses(verse: VerseResponse, highlighted: boolean): string {
  const omitted = isOmittedVerse(verse)
    ? "italic text-slate-400 dark:text-slate-500"
    : "";
  const red = verse.is_red_letter ? "text-rose-700 dark:text-rose-300" : "";
  const hi = highlighted ? "bg-amber-100 dark:bg-amber-900/40" : "";
  return [omitted, red, hi].filter(Boolean).join(" ");
}

/** A verse's covering highlights, projected into its char-coordinate space. */
function highlightSpansForVerse(
  annotations: Annotation[],
  verse: VerseResponse,
): HighlightSpan[] {
  return annotations
    .filter((a) => a.verse_start <= verse.number && a.verse_end >= verse.number)
    .map((a) => ({
      start: a.verse_start === verse.number ? a.char_start : 0,
      end: a.verse_end === verse.number ? a.char_end : verse.text.length,
      annotation: a,
    }));
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
  highlightSpans: HighlightSpan[];
  onNoteClick: (note: FootnoteResponse) => void;
}

/**
 * Render verse text as a sequence of `data-text-segment` spans (the offset
 * coordinate space the selection mapper and backend `char_offset` agree on),
 * with typed-note markers interleaved and highlight backgrounds applied to
 * covered runs. Markers and the verse-number control are NOT data-text-segment,
 * so they're zero-width in that space. A verse with no notes/highlights renders
 * as one plain span, so plain translations are unchanged.
 */
function VerseBody({ verse, highlightSpans, onNoteClick }: VerseBodyProps): JSX.Element {
  const parts = buildVerseParts(verse.text, verse.footnotes, highlightSpans);
  const plainFootnotes = verse.footnotes.filter((f) => f.char_offset === null);
  return (
    <>
      {parts.map((part, i) => {
        if (part.type === "marker") {
          return (
            <NoteMarker
              key={`note-${part.note.id}`}
              number={part.number}
              onClick={(event) => {
                // Don't let the marker trigger a highlight/selection action.
                event.stopPropagation();
                onNoteClick(part.note);
              }}
            />
          );
        }
        const top = part.highlights[part.highlights.length - 1];
        if (!top) {
          return (
            <span key={`text-${i}`} data-text-segment="">
              {part.text}
            </span>
          );
        }
        // Overlap (5c-2): the newest highlight's color shows on top; a `+N`
        // badge (N = highlights beyond the top) signals the stack. The run and
        // the badge carry data-highlight-id={top.id} (the fast-path/top) AND
        // data-highlight-ids (the FULL covering set, id-ascending), so a click
        // opens the panel for the whole stack — reaching the ones underneath
        // (5c-3). The badge is NOT data-text-segment (zero-width in the offset
        // space) and must NOT stopPropagation (the mouseup must reach the
        // chapter handler).
        const stacked = part.highlights.length > 1;
        const ids = part.highlights.map((a) => a.id).join(",");
        return (
          <span key={`text-${i}`}>
            <span
              data-text-segment=""
              data-highlight-id={top.id}
              data-highlight-ids={ids}
              className="cursor-pointer rounded-sm"
              style={{ backgroundColor: highlightVar(top.color) }}
            >
              {part.text}
            </span>
            {stacked && (
              <button
                type="button"
                data-highlight-id={top.id}
                data-highlight-ids={ids}
                data-testid="highlight-stack-badge"
                aria-label={`${part.highlights.length} highlights here`}
                className="mx-0.5 select-none rounded px-1 align-super font-sans text-[0.65em] font-medium text-slate-600 ring-1 ring-slate-300 dark:text-slate-300 dark:ring-slate-600"
              >
                +{part.highlights.length - 1}
              </button>
            )}
          </span>
        );
      })}
      <FootnoteMarker footnotes={plainFootnotes} />
    </>
  );
}

interface SelectionPopoverProps {
  popover: PopoverState;
  onPick: (color: HighlightColor) => void;
  onCancel: () => void;
}

function SelectionPopover({
  popover,
  onPick,
  onCancel,
}: SelectionPopoverProps): JSX.Element {
  // Escape dismisses the popover (keyboard parity with the Cancel button).
  useEffect(() => {
    function onKey(event: KeyboardEvent): void {
      if (event.key === "Escape") onCancel();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel]);
  return (
    <div
      data-testid="highlight-popover"
      role="dialog"
      aria-label="Highlight"
      style={{
        position: "fixed",
        top: Math.max(8, popover.top - 44),
        left: Math.max(8, popover.left),
      }}
      // Keep the popover's own mouse events from re-triggering the article's
      // selection handler (which would close it before a swatch click lands).
      onMouseUp={(e) => e.stopPropagation()}
      onMouseDown={(e) => e.stopPropagation()}
      className="z-20 flex items-center gap-1 rounded-md border border-slate-200 bg-white p-1 shadow-lg dark:border-slate-700 dark:bg-slate-800"
    >
      {HIGHLIGHT_COLORS.map((color) => (
        <button
          key={color}
          type="button"
          aria-label={`Highlight ${HIGHLIGHT_COLOR_LABELS[color]}`}
          onClick={() => onPick(color)}
          style={{ backgroundColor: highlightVar(color) }}
          className="h-6 w-6 rounded-full border border-slate-300 transition-transform hover:scale-110 dark:border-slate-600"
        />
      ))}
      <button
        type="button"
        aria-label="Cancel"
        onClick={onCancel}
        className="ml-1 rounded px-1.5 py-1 text-xs text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700"
      >
        ✕
      </button>
    </div>
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

export function NoteView({ note, translationCode, onClose }: NoteViewProps): JSX.Element {
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
  annotations: Annotation[];
  verseRef: (el: HTMLElement | null) => void;
  onVerseClick: (verse: VerseResponse) => void;
  onNoteClick: (note: FootnoteResponse) => void;
}

function VerseLayout({
  chapter,
  headingsByVerse,
  highlightRange,
  annotations,
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
        const spans = highlightSpansForVerse(annotations, verse);
        return (
          <div key={verse.id}>
            {headings.map((h) => (
              <Heading key={`${h.before_verse}-${h.text}`} heading={h} />
            ))}
            <div
              ref={isStart ? verseRef : undefined}
              data-verse={verse.number}
              data-testid={`verse-${verse.number}`}
              className={`rounded px-2 py-1 ${verseToneClasses(verse, highlighted)}`}
            >
              <button
                type="button"
                data-testid={`verse-${verse.number}-new-entry`}
                aria-label={`New entry on ${chapter.book.name} ${chapter.chapter_number}:${verse.number}`}
                onClick={() => onVerseClick(verse)}
                className={NUMBER_BUTTON_CLASS}
              >
                {verse.number}
              </button>
              <VerseBody verse={verse} highlightSpans={spans} onNoteClick={onNoteClick} />
            </div>
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
  annotations,
  verseRef,
  onVerseClick,
  onNoteClick,
}: LayoutProps): JSX.Element {
  // Walk the chapter in order, emitting <h2> blocks where a heading precedes a
  // verse and accumulating verses into a running <p> in between.
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
    const spans = highlightSpansForVerse(annotations, verse);
    buffer.push(
      <span
        key={verse.id}
        ref={isStart ? verseRef : undefined}
        data-verse={verse.number}
        data-testid={`verse-${verse.number}`}
        className={verseToneClasses(verse, highlighted)}
      >
        <button
          type="button"
          data-testid={`verse-${verse.number}-new-entry`}
          aria-label={`New entry on ${chapter.book.name} ${chapter.chapter_number}:${verse.number}`}
          onClick={() => onVerseClick(verse)}
          className={NUMBER_BUTTON_INLINE_CLASS}
        >
          {verse.number}
        </button>
        <VerseBody verse={verse} highlightSpans={spans} onNoteClick={onNoteClick} />
      </span>,
    );
    buffer.push(" ");
  }
  flush();

  return <div className="space-y-2">{nodes}</div>;
}
