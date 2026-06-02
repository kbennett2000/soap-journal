"""KJV parser CLI.

Converts a public-domain King James Version PDF into canonical Bible JSON.

Source format
-------------
- 1517-page PDF with embedded Tahoma / Times fonts, Unicode mappings.
- Pages 1–2 are TOC / title.  Real scripture starts at "Genesis 1".
- Chapter markers are dedicated lines: ``Genesis 1``, ``1 Samuel 31``,
  ``Song of Solomon 8``, ``Psalm 150``.
- Verse numbers sit at the end of lines (or on their own line) followed
  by U+202F (narrow no-break space) at the start of the next line.
  After preprocessing, verses appear inline: ``1 In the beginning … 2 And``.
- Section headings (``The Creation``, ``The First Day``) are interleaved
  between chapter headers and verse text.
- Parenthetical cross-reference lines like ``(John 1:1–5; Hebrews 11:1–3)``
  appear under headings; skipped.
- ``KJV  [Online]`` footer appears between books; skipped.
- ``Saying N`` sub-section markers in Proverbs (30 of them) look like
  chapter headers but ``Saying`` is not a canonical book name; filtered
  by checking ``get_book_by_name()``.
- Bracketed italics ``[was]``, ``[is]`` preserved verbatim.
- Form-feed characters mark page breaks; treated as line separators.
- 66 books, 1,189 chapters, 31,102 verses.
- No red-letter formatting or footnotes.

Usage
-----
    python -m soap_journal.parsers.kjv <source.pdf> --out <output.json>

**Public domain**: The KJV text is in the public domain.  The parser source
code and the generated JSON may be freely committed and distributed.
"""

from __future__ import annotations

from soap_journal.parsers._pdfmaker_translations import get_config
from soap_journal.parsers.pdfmaker_format import (
    BooksData,
    HeadingsData,
    PdfMakerParseError,
    make_cli_main,
    parse_pdfmaker_source,
)
from soap_journal.parsers.pdfmaker_format import (
    build_canonical_translation as _build_impl,
)
from soap_journal.parsers.pdfmaker_format import (
    is_likely_heading as _is_likely_heading,  # noqa: F401 — re-exported for tests
)
from soap_journal.parsers.pdfmaker_format import (
    parse_lines as _parse_lines_impl,
)
from soap_journal.parsers.pdfmaker_format import (
    read_pdf as _read_pdf,  # noqa: F401 — re-exported for tests
)
from soap_journal.parsers.pdfmaker_format import (
    split_verses as _split_verses,  # noqa: F401 — re-exported for tests
)
from soap_journal.parsers.pdfmaker_format import (
    write_canonical_json as _write_canonical_json,  # noqa: F401 — re-exported for tests
)
from soap_journal.parsers.schema import CanonicalTranslation

_CONFIG = get_config("KJV")

KJV_CODE = _CONFIG.code
KJV_NAME = _CONFIG.name
KJV_LANGUAGE = _CONFIG.language
KJV_COPYRIGHT = _CONFIG.copyright

KjvParseError = PdfMakerParseError


def parse_lines(text: str) -> tuple[BooksData, HeadingsData, list[str]]:
    """Parse preprocessed KJV text (backward-compatible wrapper)."""
    return _parse_lines_impl(text, _CONFIG.footer_marker)


def build_canonical_translation(
    books_data: BooksData, headings_data: HeadingsData
) -> CanonicalTranslation:
    """Build KJV canonical translation (backward-compatible wrapper)."""
    return _build_impl(books_data, headings_data, _CONFIG)


def parse_kjv_source(text: str) -> tuple[CanonicalTranslation, list[str]]:
    """Parse KJV text into a fully-validated CanonicalTranslation."""
    return parse_pdfmaker_source(text, _CONFIG)


main = make_cli_main(_CONFIG)

if __name__ == "__main__":  # pragma: no cover - thin shell
    raise SystemExit(main())
