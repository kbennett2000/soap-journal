"""PDF parser internals for the NET Bible Translator's Edition.

Ported largely verbatim from the private `kbennett2000/net-bible-study` repo
(`backend/ingest/parser.py`). The empirically-tuned font-height constants, the
column/gutter split, the per-page marker->note ordinal matching, the cross-page
overflow logic, and the two book-boundary detections are kept intact — they were
derived against this exact PDF edition and should not be re-derived casually.
The adapter to the canonical schema and the CLI live in `net.py`.

The one intentional change from the original is `run_pdftotext_bbox`, which now
mirrors `nlt.py`'s subprocess idiom (timeout, OSError on failure, and a
propagating FileNotFoundError that the CLI turns into an install hint) instead
of a bare `check=True` call.

Pipeline:
    1. Invoke `pdftotext -bbox-layout` on the source PDF for a page range.
    2. Parse the XHTML output into per-page lists of <word> records with bbox.
    3. Classify each word by font height into a stable bucket
       (verse body, section heading, verse marker, note body, type code,
       superscript marker, foreign-script, book title).
    4. Assign each word to a column by x-coordinate (gutter ≈ page-width/2).
    5. Walk each column top-to-bottom, separately for the verse stream and
       the note stream (which are interleaved by y but split by height).
    6. Build verses, section headings, notes, and inline footnote markers.
    7. Reconnect markers to verses and note bodies by ordinal position on
       the page (the Nth in-text marker maps to the Nth note body).

Cross-page state:
- A verse can span pages — the current_verse buffer carries over.
- A note body can overflow to the top of the next column/page; we detect
  these as note-body-height words appearing before the first "marker + type
  code" pair in a column's note region, and append them to the previous
  page's last note.
"""

from __future__ import annotations

import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal

NoteType = Literal["tn", "sn", "tc", "map"]
NOTE_TYPES: set[str] = {"tn", "sn", "tc", "map"}

VERSE_MARKER_RE = re.compile(r"^(\d+):(\d+)$")
LOST_MARKER_SENTINEL = "*"  # pdftotext renders unmapped superscript glyphs as \x04

# Cross-reference book abbreviations used by the NET Translator's Edition.
_BOOK_ABBREVS: tuple[str, ...] = (
    "Gen",
    "Exod",
    "Lev",
    "Num",
    "Deut",
    "Josh",
    "Judg",
    "Ruth",
    "1 Sam",
    "2 Sam",
    "1 Kgs",
    "2 Kgs",
    "1 Chr",
    "2 Chr",
    "Ezra",
    "Neh",
    "Esth",
    "Job",
    "Ps",
    "Prov",
    "Eccl",
    "Song",
    "Isa",
    "Jer",
    "Lam",
    "Ezek",
    "Dan",
    "Hos",
    "Joel",
    "Amos",
    "Obad",
    "Jonah",
    "Mic",
    "Nah",
    "Hab",
    "Zeph",
    "Hag",
    "Zech",
    "Mal",
    "Matt",
    "Mark",
    "Luke",
    "John",
    "Acts",
    "Rom",
    "1 Cor",
    "2 Cor",
    "Gal",
    "Eph",
    "Phil",
    "Col",
    "1 Thess",
    "2 Thess",
    "1 Tim",
    "2 Tim",
    "Titus",
    "Phlm",
    "Heb",
    "Jas",
    "1 Pet",
    "2 Pet",
    "1 John",
    "2 John",
    "3 John",
    "Jude",
    "Rev",
)
CROSS_REF_RE = re.compile(
    r"\b(?P<book>"
    + "|".join(re.escape(a) for a in _BOOK_ABBREVS)
    + r")\.?\s+(?P<chapter>\d+):(?P<verse>\d+)(?:-(?P<verse_end>\d+))?\b"
)


def extract_cross_refs(body: str) -> list[CrossRefData]:
    """Pull `Book Chapter:Verse[-Verse]` patterns from a note body."""
    seen: set[tuple[str, int, int, int | None]] = set()
    refs: list[CrossRefData] = []
    for m in CROSS_REF_RE.finditer(body):
        book = m.group("book")
        ch = int(m.group("chapter"))
        v = int(m.group("verse"))
        v_end_raw = m.group("verse_end")
        v_end = int(v_end_raw) if v_end_raw else None
        key = (book, ch, v, v_end)
        if key in seen:
            continue
        seen.add(key)
        refs.append(CrossRefData(book, ch, v, v_end))
    return refs


# Font-height buckets, derived empirically from the NET Translator's Edition.
H_MARKER_MAX = 7.5  # superscript footnote markers
H_TYPECODE_MAX = 9.0  # 'tn' / 'sn' / 'tc' / 'map' words
H_NOTE_BODY_MAX = 10.0  # regular note body text (~9.6)
H_BOOK_TITLE_MIN = 30.0  # 'Genesis' style book heading
H_SECTION_HEADING_RANGE = (11.5, 12.3)  # heading sits just under typical verse body


class WordCategory(Enum):
    BOOK_TITLE = "book_title"
    SECTION_HEADING = "section_heading"
    VERSE_MARKER = "verse_marker"
    VERSE_BODY = "verse_body"
    SMALL_CAPS = "small_caps"  # small-caps suffix of an all-caps word (e.g. "ord" of "Lord")
    NOTE_BODY = "note_body"
    TYPE_CODE = "type_code"
    MARKER_SUPER = "marker_super"
    FOREIGN_SCRIPT = "foreign_script"  # Hebrew/Greek in notes, height ~8.8
    UNKNOWN = "unknown"


@dataclass
class Word:
    x: float
    y: float
    h: float
    text: str
    column: int  # 0 = left, 1 = right
    category: WordCategory


@dataclass
class Page:
    number: int  # 1-based PDF page (not Bible chapter)
    width: float
    height: float
    words: list[Word]


@dataclass
class VerseRow:
    number: int
    text: str


@dataclass
class CrossRefData:
    to_book_short: str
    to_chapter: int
    to_verse_start: int
    to_verse_end: int | None = None


@dataclass
class NoteRow:
    verse_number: int
    chapter: int
    marker: int  # ordinal on the page; 1-indexed
    word_offset: int  # char offset into verse text
    type: NoteType
    body: str
    ordinal: int  # ordinal within the verse, 0-indexed
    cross_refs: list[CrossRefData] = field(default_factory=list)


@dataclass
class ChapterData:
    book_short: str
    book_full: str
    book_position: int
    testament: Literal["OT", "NT"]
    chapter: int
    verses: list[VerseRow] = field(default_factory=list)
    headings: list[tuple[int, str]] = field(default_factory=list)
    notes: list[NoteRow] = field(default_factory=list)


# ---------- bbox-layout extraction ----------


def run_pdftotext_bbox(pdf_path: Path, first_page: int, last_page: int) -> str:
    """Invoke `pdftotext -bbox-layout` for a page range, returning XHTML.

    Mirrors `nlt.py`'s subprocess idiom: a missing `pdftotext` binary raises
    `FileNotFoundError` (the CLI maps it to an install hint), while a timeout or
    a non-zero exit raises `OSError`.
    """
    try:
        result = subprocess.run(
            [
                "pdftotext",
                "-bbox-layout",
                "-f",
                str(first_page),
                "-l",
                str(last_page),
                str(pdf_path),
                "-",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )
    except subprocess.TimeoutExpired as exc:
        raise OSError("pdftotext timed out after 300 seconds") from exc
    if result.returncode != 0:
        raise OSError(f"pdftotext failed (exit {result.returncode}): {result.stderr.strip()}")
    return result.stdout


def parse_pages(xhtml: str) -> list[Page]:
    """Convert pdftotext bbox-layout XHTML into Page records with classified words."""
    cleaned = re.sub(r'\sxmlns="[^"]+"', "", xhtml, count=1)
    cleaned = cleaned.replace("\x04", LOST_MARKER_SENTINEL)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", cleaned)
    root = ET.fromstring(cleaned)

    pages: list[Page] = []
    for page_el in root.iter("page"):
        width = float(page_el.get("width", 0))
        height = float(page_el.get("height", 0))
        # First pass: build raw word records (no column yet)
        raw: list[tuple[float, float, float, str, WordCategory]] = []
        for w_el in page_el.iter("word"):
            text = (w_el.text or "").strip()
            if not text:
                continue
            x = float(w_el.get("xMin", 0))
            y = float(w_el.get("yMin", 0))
            h = float(w_el.get("yMax", 0)) - y
            if y < 36:
                continue
            raw.append((x, y, h, text, classify(text, h)))
        gutter = detect_gutter(raw, width)
        words = [
            Word(x=x, y=y, h=h, text=text, column=(0 if x < gutter else 1), category=cat)
            for (x, y, h, text, cat) in raw
        ]
        pages.append(Page(number=len(pages) + 1, width=width, height=height, words=words))
    return pages


def detect_gutter(
    raw: list[tuple[float, float, float, str, WordCategory]],
    page_width: float,
) -> float:
    """Find the column gutter — the widest x-gap in body-height word positions.

    Looking at verse-body (h ≈ 12.5) and note-body (h ≈ 9.6) words only avoids
    being thrown off by markers and superscripts at weird positions.
    """
    relevant_x = sorted(
        {
            round(x, 1)
            for (x, _y, _h, _t, cat) in raw
            if cat in (WordCategory.VERSE_BODY, WordCategory.NOTE_BODY) and 140 <= x <= 290
        }
    )
    if len(relevant_x) < 2:
        return page_width / 2
    best_gap = 0.0
    best_mid = page_width / 2
    for i in range(1, len(relevant_x)):
        gap = relevant_x[i] - relevant_x[i - 1]
        if gap > best_gap:
            best_gap = gap
            best_mid = (relevant_x[i] + relevant_x[i - 1]) / 2
    return best_mid


def classify(text: str, h: float) -> WordCategory:
    """Classify a word by its font height and (lightly) its text content."""
    if h >= H_BOOK_TITLE_MIN:
        return WordCategory.BOOK_TITLE
    if h <= H_MARKER_MAX:
        return WordCategory.MARKER_SUPER
    # Type codes — 'tn'/'sn'/'tc'/'map' — are always rendered smaller than
    # verse body but their exact height varies by book (e.g. 8.5pt in Genesis,
    # 9.4pt in Ecclesiastes). Detect by content first, then validate the size.
    if text in NOTE_TYPES and h < H_SECTION_HEADING_RANGE[0]:
        return WordCategory.TYPE_CODE
    if h <= H_TYPECODE_MAX:
        # Small-caps suffix: a short ASCII-letter fragment like 'ord' (the tail
        # of 'Lord' rendered in small caps for the divine name). Distinguish
        # from Hebrew/Greek script which contains non-ASCII characters.
        stripped = text.strip(".,;:!?'’\"-")  # noqa: RUF001
        if stripped and stripped.isascii() and stripped.isalpha() and stripped.islower():
            return WordCategory.SMALL_CAPS
        return WordCategory.FOREIGN_SCRIPT
    if h <= H_NOTE_BODY_MAX:
        return WordCategory.NOTE_BODY
    # h > 10.0 — verse territory. A '\d+:\d+' word is a verse marker; in note
    # body height (handled above) it would be a cross-reference instead.
    if VERSE_MARKER_RE.match(text):
        return WordCategory.VERSE_MARKER
    if H_SECTION_HEADING_RANGE[0] <= h <= H_SECTION_HEADING_RANGE[1]:
        return WordCategory.SECTION_HEADING
    return WordCategory.VERSE_BODY


def group_into_lines(words: list[Word], tolerance: float = 3.0) -> list[list[Word]]:
    """Cluster words into lines where word y-values differ by less than `tolerance`.

    Used to defeat the "verse marker is at y=121.9 but the first verse-text word
    is at y=121.0" case: both belong to the same printed line but a pure (y,x)
    sort gets the order wrong.
    """
    if not words:
        return []
    sorted_words = sorted(words, key=lambda w: (w.y, w.x))
    lines: list[list[Word]] = [[sorted_words[0]]]
    for w in sorted_words[1:]:
        if abs(w.y - lines[-1][0].y) < tolerance:
            lines[-1].append(w)
        else:
            lines.append([w])
    for line in lines:
        line.sort(key=lambda w: w.x)
    return lines


# ---------- per-page parsing ----------


@dataclass
class _PageNote:
    marker_text: str  # raw text of the leading marker word (e.g. "10" or "*")
    type: NoteType
    body_words: list[Word] = field(default_factory=list)
    col: int = 0


def _process_column_verses(
    column_words: list[Word],
    state: _ParserState,
) -> None:
    """Append verse text and section headings from one column to state.

    Words are grouped into lines (by y proximity), then within each line we
    re-order so that a VERSE_MARKER appears before the verse-body words on its
    line, even if its yMin is slightly larger.
    """
    relevant = [
        w
        for w in column_words
        if w.category
        in (
            WordCategory.VERSE_MARKER,
            WordCategory.VERSE_BODY,
            WordCategory.SECTION_HEADING,
            WordCategory.MARKER_SUPER,
            WordCategory.SMALL_CAPS,
        )
    ]
    lines = group_into_lines(relevant)

    # SMALL_CAPS words only count as verse content if their line also contains
    # an actual VERSE_BODY word. Otherwise they're inside a note body (e.g.
    # transliterated Greek in a translator's note) and would corrupt verse text.
    # Lines that are pure section heading or pure verse marker are preserved.
    filtered_lines: list[list[Word]] = []
    for line in lines:
        if any(w.category in (WordCategory.VERSE_BODY, WordCategory.SECTION_HEADING) for w in line):
            filtered_lines.append(line)
            continue
        markers_only = [w for w in line if w.category == WordCategory.VERSE_MARKER]
        if markers_only:
            filtered_lines.append(markers_only)
    lines = filtered_lines

    for line in lines:
        # Within a line: process in pure x-order. A verse marker mid-line
        # switches the active verse — words before the marker belong to the
        # previous verse, words after to the new one.
        x_sorted = sorted(line, key=lambda w: w.x)
        for w in x_sorted:
            if w.category == WordCategory.SECTION_HEADING:
                if state.pending_heading is None:
                    state.pending_heading = w.text
                else:
                    state.pending_heading = (state.pending_heading + " " + w.text).strip()
                continue
            if w.category == WordCategory.VERSE_MARKER:
                m = VERSE_MARKER_RE.match(w.text)
                assert m is not None
                ch = int(m.group(1))
                v = int(m.group(2))
                state.open_verse(ch, v)
                continue
            if w.category == WordCategory.MARKER_SUPER:
                state.record_inline_marker(w)
                continue
            state.append_word(w)


def _process_column_notes(
    column_words: list[Word],
    col: int,
    state: _ParserState,
) -> None:
    """Build note records from one column's note-region words."""
    relevant = [
        w
        for w in column_words
        if w.category
        in (
            WordCategory.NOTE_BODY,
            WordCategory.TYPE_CODE,
            WordCategory.MARKER_SUPER,
            WordCategory.FOREIGN_SCRIPT,
        )
    ]
    if not relevant:
        return

    lines = group_into_lines(relevant)

    # Find the column-left x by looking for the first line that starts with
    # a marker word immediately followed by a type-code word.
    col_left_x: float | None = None
    for line in lines:
        xsorted = sorted(line, key=lambda w: w.x)
        if (
            len(xsorted) >= 2
            and xsorted[0].category == WordCategory.MARKER_SUPER
            and xsorted[1].category == WordCategory.TYPE_CODE
        ):
            col_left_x = xsorted[0].x
            break

    notes: list[_PageNote] = []
    current: _PageNote | None = None

    for line in lines:
        xsorted = sorted(line, key=lambda w: w.x)
        # Detect a new-note start at the head of this line.
        if (
            len(xsorted) >= 2
            and xsorted[0].category == WordCategory.MARKER_SUPER
            and xsorted[1].category == WordCategory.TYPE_CODE
            and (col_left_x is None or abs(xsorted[0].x - col_left_x) < 12)
        ):
            current = _PageNote(
                marker_text=xsorted[0].text,
                type=xsorted[1].text,  # type: ignore[arg-type]
                col=col,
            )
            notes.append(current)
            body_words = xsorted[2:]
        else:
            body_words = xsorted

        if current is None:
            # Words appearing before the first note-start = overflow continuation
            # from previous page's last note.
            for w in body_words:
                if w.category in (
                    WordCategory.NOTE_BODY,
                    WordCategory.FOREIGN_SCRIPT,
                    WordCategory.MARKER_SUPER,
                ):
                    state.overflow_note_words.append(w)
            continue

        for w in body_words:
            if w.category == WordCategory.TYPE_CODE:
                continue
            current.body_words.append(w)

    state.page_notes.extend(notes)


# ---------- chapter assembly state ----------


@dataclass
class _InlineMarker:
    y: float
    x: float
    chapter: int
    verse: int
    char_offset: int
    column: int


@dataclass
class _ParserState:
    book: tuple[str, str, int, Literal["OT", "NT"]]
    only_chapter: int | None
    max_chapter: int | None = None
    current_chapter: int = 0
    current_verse: int | None = None
    current_column: int = 0
    book_done: bool = False  # set when we detect the next book's content has started
    verse_text_parts: dict[tuple[int, int], list[str]] = field(default_factory=dict)
    pending_heading: str | None = None
    headings: list[tuple[int, int, str]] = field(default_factory=list)
    # Per-page-and-column accumulators (cleared each column)
    page_inline_markers: list[_InlineMarker] = field(default_factory=list)
    page_notes: list[_PageNote] = field(default_factory=list)
    overflow_note_words: list[Word] = field(default_factory=list)
    # Final notes
    finished_notes: list[NoteRow] = field(default_factory=list)
    # Cross-page state: last note completed (for overflow concatenation)
    last_note: NoteRow | None = None
    # Per-verse note ordinal counter
    note_ordinal_by_verse: dict[tuple[int, int], int] = field(default_factory=dict)
    # Per-page marker numbering counter (starts at 1, resets per page)
    page_marker_counter: int = 0

    def open_verse(self, ch: int, v: int) -> None:
        if self.book_done:
            return
        # Book-boundary detection #1: chapter resets to a lower number
        # (Genesis 50 → Exodus 1).
        if self.current_chapter > 1 and ch < self.current_chapter:
            self.book_done = True
            return
        # Book-boundary detection #2: re-entering (1, 1) when we've already
        # populated it (e.g. Obadiah → Jonah, both single-chapter).
        if (ch, v) == (1, 1) and (1, 1) in self.verse_text_parts and self.verse_text_parts[(1, 1)]:
            self.book_done = True
            return
        # Out-of-bounds chapter for this book.
        if self.max_chapter is not None and ch > self.max_chapter:
            self.book_done = True
            return
        if ch != self.current_chapter:
            self.current_chapter = ch
        self.current_verse = v
        self.verse_text_parts.setdefault((ch, v), [])
        if self.pending_heading is not None:
            self.headings.append((ch, v, self.pending_heading))
            self.pending_heading = None

    def append_word(self, w: Word) -> None:
        if self.book_done or self.current_verse is None or self.current_chapter == 0:
            return
        key = (self.current_chapter, self.current_verse)
        parts = self.verse_text_parts[key]
        # SMALL_CAPS suffixes (e.g. 'ord' for 'Lord') merge into the preceding
        # word with no space (giving 'Lord' visually).
        if w.category == WordCategory.SMALL_CAPS and parts:
            parts[-1] = parts[-1] + w.text
            return
        # Collapse line-wrap hyphenation: previous word ends with '-' and this
        # word starts with a letter.
        if parts and parts[-1].endswith("-") and w.text[:1].isalpha():
            parts[-1] = parts[-1][:-1] + w.text
            return
        # Trailing punctuation that's emitted as its own token (e.g. ',' after a
        # small-caps suffix) attaches to the preceding word with no space.
        if parts and w.text in {",", ".", ";", ":", "!", "?", ")"}:
            parts[-1] = parts[-1] + w.text
            return
        parts.append(w.text)

    def record_inline_marker(self, w: Word) -> None:
        if self.book_done or self.current_verse is None or self.current_chapter == 0:
            return
        key = (self.current_chapter, self.current_verse)
        cur_text = " ".join(self.verse_text_parts[key])
        self.page_inline_markers.append(
            _InlineMarker(
                y=w.y,
                x=w.x,
                chapter=self.current_chapter,
                verse=self.current_verse,
                char_offset=len(cur_text),
                column=w.column,
            )
        )


def parse_chapter(
    pdf_path: Path,
    book_short: str,
    book_full: str,
    book_position: int,
    testament: Literal["OT", "NT"],
    chapter: int,
    page_range: tuple[int, int],
) -> ChapterData:
    """Parse one chapter from the PDF (convenience wrapper around `parse_book`)."""
    chapters = parse_book(
        pdf_path=pdf_path,
        book_short=book_short,
        book_full=book_full,
        book_position=book_position,
        testament=testament,
        page_range=page_range,
    )
    matched = next((c for c in chapters if c.chapter == chapter), None)
    if matched is None:
        raise ValueError(f"chapter {chapter} not found in page range {page_range}")
    return matched


def parse_book(
    pdf_path: Path,
    book_short: str,
    book_full: str,
    book_position: int,
    testament: Literal["OT", "NT"],
    page_range: tuple[int, int],
    max_chapter: int | None = None,
) -> list[ChapterData]:
    """Parse all chapters within a page range, returning one ChapterData per chapter.

    Args:
        page_range: 1-based (first_page, last_page) covering the book.
        max_chapter: optional ceiling — verses with chapter > max_chapter are
                     ignored (defensive against pages that bleed into the next
                     book). If omitted, the parser auto-stops when the chapter
                     number resets to 1 mid-stream.

    Returns:
        Chapters in ascending order.
    """
    xhtml = run_pdftotext_bbox(pdf_path, page_range[0], page_range[1])
    pages = parse_pages(xhtml)
    state = _ParserState(
        book=(book_short, book_full, book_position, testament),
        only_chapter=None,
        max_chapter=max_chapter,
    )

    for page in pages:
        state.page_marker_counter = 0  # resets per page
        for col in (0, 1):
            # Reset per-column accumulators
            state.page_inline_markers = []
            state.page_notes = []
            state.overflow_note_words = []
            col_words = [w for w in page.words if w.column == col]
            _process_column_verses(col_words, state)
            _process_column_notes(col_words, col, state)

            # Merge overflow words with previous note (cross-column/page tail)
            if state.overflow_note_words and state.last_note is not None:
                overflow_text = " ".join(w.text for w in state.overflow_note_words).strip()
                overflow_text = re.sub(r"(\w)-\s+(\w)", r"\1\2", overflow_text)
                if overflow_text:
                    state.last_note.body = (state.last_note.body + " " + overflow_text).strip()

            # Attach this column's notes to this column's inline markers
            _attach_column_notes(state)

    return _build_all_chapters(state)


def _attach_column_notes(state: _ParserState) -> None:
    """Match this column's notes to its inline markers, in y-x order.

    The Nth note in a column corresponds to the Nth inline marker in the same
    column. This works because verses and their notes share columns, and notes
    are emitted in the same order their markers appear inline.
    """
    markers_sorted = sorted(state.page_inline_markers, key=lambda m: (m.y, m.x))
    for i, note in enumerate(state.page_notes):
        body_text = " ".join(w.text for w in note.body_words).strip()
        body_text = re.sub(r"(\w)-\s+(\w)", r"\1\2", body_text)
        body_text = re.sub(r"\s+", " ", body_text)
        if i < len(markers_sorted):
            m = markers_sorted[i]
            verse_ch, verse_num = m.chapter, m.verse
            offset = m.char_offset
        else:
            # More notes than markers — shouldn't normally happen, but degrade
            # gracefully: attach to the last marker's verse.
            if markers_sorted:
                m = markers_sorted[-1]
                verse_ch, verse_num = m.chapter, m.verse
                offset = m.char_offset
            else:
                continue
        state.page_marker_counter += 1
        key = (verse_ch, verse_num)
        ordinal = state.note_ordinal_by_verse.get(key, 0)
        nr = NoteRow(
            verse_number=verse_num,
            chapter=verse_ch,
            marker=state.page_marker_counter,
            word_offset=offset,
            type=note.type,
            body=body_text,
            ordinal=ordinal,
            cross_refs=extract_cross_refs(body_text),
        )
        state.finished_notes.append(nr)
        state.last_note = nr
        state.note_ordinal_by_verse[key] = ordinal + 1


def _build_all_chapters(state: _ParserState) -> list[ChapterData]:
    """Collect every chapter that the parser produced into ChapterData rows."""
    book_short, book_full, book_position, testament = state.book
    chapters_seen = sorted({ch for (ch, _v) in state.verse_text_parts})
    out: list[ChapterData] = []
    for chapter in chapters_seen:
        ch_data = ChapterData(
            book_short=book_short,
            book_full=book_full,
            book_position=book_position,
            testament=testament,
            chapter=chapter,
        )
        for (ch, v), parts in sorted(state.verse_text_parts.items()):
            if ch != chapter:
                continue
            text = " ".join(parts).strip()
            text = re.sub(r"\s+", " ", text)
            ch_data.verses.append(VerseRow(number=v, text=text))
        for ch, v, txt in state.headings:
            if ch != chapter:
                continue
            ch_data.headings.append((v, txt))
        for n in state.finished_notes:
            if n.chapter != chapter:
                continue
            ch_data.notes.append(n)
        out.append(ch_data)
    return out
