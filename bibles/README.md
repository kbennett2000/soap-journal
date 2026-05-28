# Bible Source Files

Place copyrighted Bible source files (PDFs, text exports, etc.) in this
directory. **These files are gitignored and must not be committed** — they
contain copyrighted text that cannot be redistributed.

The `bible-sources/` directory (at the repo root) is different: it holds
the 13 public-domain translations that ship with the app and load
automatically on first boot. This `bibles/` directory is for translations
**you** have the legal right to use but cannot redistribute (ESV, NLT,
NKJV, etc.).

> **Copyright:** only load translations you have the legal right to use on
> a server you control. Loading a copyrighted translation for personal use
> is between you and the publisher.

## How it works with Docker

`./bibles` is bind-mounted read-only into the running container at
`/app/bibles` (see `docker-compose.yml`). So once you drop a PDF in this
folder on the host, it's immediately visible inside the container, and you
can parse and load it with `docker compose exec` — no rebuild needed.

The general workflow for any of the parsers below:

1. Put the PDF in this folder, e.g. `./bibles/esv.pdf`.
2. If you upgraded from a version before the `bibles/` mount existed, run
   `docker compose up -d` once so the container picks up the bind-mount.
3. Parse it into canonical JSON inside the container.
4. Load that JSON into the database.
5. Refresh the browser — the translation appears in the reader and the
   side-by-side compare view.

The parse step writes JSON to `/tmp` inside the container; the load step
reads it back. Both run in the same container, so `/tmp` persists between
the two commands.

> **Windows / Git Bash note:** prefix `docker compose exec` commands with
> `MSYS_NO_PATHCONV=1` so Git Bash doesn't rewrite the `/app/...` path.

## NKJV (New King James Version)

**Source**: A 908-page PDF of the 1982 NKJV with one verse per line,
formatted as `<Abbr> <Chapter>:<Verse> <Text>`. Parsed with pypdf.

```bash
# 1. Place the PDF at ./bibles/nkjv.pdf
# 2. Parse and load inside the container:
docker compose exec soap-journal \
  python -m soap_journal.parsers.nkjv /app/bibles/nkjv.pdf --out /tmp/nkjv.json
docker compose exec soap-journal \
  python -m soap_journal.cli load-translation /tmp/nkjv.json
```

**Copyright**: Scripture taken from the New King James Version®.
Copyright © 1982 by Thomas Nelson. Used by permission. All rights
reserved.

## ESV (English Standard Version)

**Source**: An 8,386-page chunked e-reader PDF of the ESV with chapter
headers formatted as `<bookN>.<chN>. Chapter <chN>`. Parsed with pypdf.

```bash
# 1. Place the PDF at ./bibles/esv.pdf
# 2. Parse and load inside the container:
docker compose exec soap-journal \
  python -m soap_journal.parsers.esv /app/bibles/esv.pdf --out /tmp/esv.json
docker compose exec soap-journal \
  python -m soap_journal.cli load-translation /tmp/esv.json
```

**Footnotes**: The ESV parser extracts inline footnotes where possible.
Due to how the PDF concatenates footnote text with verse text (no
delimiter), some verses may contain residual footnote content. This
affects roughly 0.4% of verses.

**Copyright**: Scripture quotations are from the ESV® Bible (The Holy
Bible, English Standard Version®), copyright © 2001 by Crossway, a
publishing ministry of Good News Publishers. Used by permission. All
rights reserved.

## NLT (New Living Translation)

**Source**: A 1,798-page two-column PDF of the NLT. Unlike the other
parsers, the NLT parser uses `pdftotext` (poppler-utils) because the
two-column layout requires column-first reading order. The runtime image
ships with poppler-utils, so this works in-container with no extra setup.

```bash
# 1. Place the PDF at ./bibles/nlt.pdf
# 2. Parse and load inside the container:
docker compose exec soap-journal \
  python -m soap_journal.parsers.nlt /app/bibles/nlt.pdf --out /tmp/nlt.json
docker compose exec soap-journal \
  python -m soap_journal.cli load-translation /tmp/nlt.json
```

**Footnotes**: The NLT print edition has extensive footnotes, but this
PDF rendering does not preserve them, so none appear in the output.

**Verse numbering**: The NLT omits certain disputed verses (e.g.
Acts 8:37, John 5:4, Mark 9:44). The verse number is preserved with a
placeholder so references still land in the right place.

**Copyright**: Holy Bible, New Living Translation, copyright © 1996,
2004, 2015 by Tyndale House Foundation. Used by permission of Tyndale
House Publishers, Carol Stream, Illinois 60188. All rights reserved.

## Adding Other Translations

The general pattern for any new translation:

1. Obtain a machine-readable source (PDF, USFM, OSIS XML, plain text).
2. Write a parser at `backend/soap_journal/parsers/<code>.py` that
   converts the source into the canonical JSON schema
   (`backend/soap_journal/parsers/schema.py`). If the PDF was produced by
   Acrobat PDFMaker (the layout the public-domain bundle uses), you may
   only need a small config entry — see
   `backend/soap_journal/parsers/pdfmaker_format.py` and
   `_pdfmaker_translations.py`. Otherwise the NKJV, ESV, and NLT parsers
   are good reference implementations for other PDF shapes.
3. Run the parser, then load the JSON with `load-translation`.

See `CONTRIBUTING.md` for details on the parser architecture.
