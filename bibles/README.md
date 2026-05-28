# Bible Source Files

Place copyrighted Bible source files (PDFs, text exports, etc.) in this
directory. **These files are gitignored and must not be committed** — they
contain copyrighted text that cannot be redistributed.

The `bible-sources/` directory (at the repo root) is different: it holds
source files for translations that are permissively licensed and *can* be
committed (e.g., the Berean Standard Bible).

## Available Parsers

### KJV (King James Version)

The KJV is bundled with the application at `bible-sources/kjv/` and loaded
automatically on first boot — no manual steps needed. If you prefer to
parse and load it yourself:

```bash
cd backend
python -m soap_journal.parsers.kjv ../bible-sources/kjv/kjv.pdf --out ../data/translations/kjv.json
python -m soap_journal.cli load-translation ../data/translations/kjv.json
```

The KJV text is in the public domain.

### NKJV (New King James Version)

**Source**: A specific 908-page PDF of the 1982 NKJV with one verse per
line, formatted as `<Abbr> <Chapter>:<Verse> <Text>`.

1. Place the PDF at `bibles/nkjv.pdf` (or any path you prefer).

2. Run the parser to produce canonical JSON:

   ```bash
   cd backend
   python -m soap_journal.parsers.nkjv ../bibles/nkjv.pdf --out ../data/translations/nkjv.json
   ```

3. Load the JSON into the database:

   ```bash
   python -m soap_journal.cli load-translation ../data/translations/nkjv.json
   ```

4. Restart the server (or refresh the browser). The NKJV translation
   will appear in the reader, and the side-by-side comparison view
   becomes active.

**Copyright**: Scripture taken from the New King James Version(R).
Copyright (c) 1982 by Thomas Nelson. Used by permission. All rights
reserved. Loading a copyrighted translation onto a server you control
for personal use is between you and the publisher.

### ESV (English Standard Version)

**Source**: An 8,386-page chunked e-reader PDF of the ESV with chapter
headers formatted as `<bookN>.<chN>. Chapter <chN>`.

1. Place the PDF at `bibles/esv.pdf` (or any path you prefer).

2. Run the parser to produce canonical JSON:

   ```bash
   cd backend
   python -m soap_journal.parsers.esv ../bibles/esv.pdf --out ../data/translations/esv.json
   ```

3. Load the JSON into the database:

   ```bash
   python -m soap_journal.cli load-translation ../data/translations/esv.json
   ```

4. Restart the server (or refresh the browser). The ESV translation
   will appear in the reader.

**Footnotes**: The ESV parser extracts inline footnotes where possible.
Due to how the PDF concatenates footnote text with verse text (no
delimiter), some verses may contain residual footnote content. This
affects roughly 0.4% of verses.

**Copyright**: Scripture quotations are from the ESV(R) Bible (The Holy
Bible, English Standard Version(R)), copyright (c) 2001 by Crossway,
a publishing ministry of Good News Publishers. Used by permission.
All rights reserved.

### NLT (New Living Translation)

**Source**: A 1,798-page two-column PDF of the NLT. The parser uses
`pdftotext -raw` (from poppler-utils) instead of pypdf because the
two-column layout requires column-first reading order.

**Prerequisite**: Install poppler-utils (`apt install poppler-utils` on
Debian/Ubuntu, `brew install poppler` on macOS, or download from
the poppler website for Windows).

1. Place the PDF at `bibles/nlt.pdf` (or any path you prefer).

2. Run the parser to produce canonical JSON:

   ```bash
   cd backend
   python -m soap_journal.parsers.nlt ../bibles/nlt.pdf --out ../data/translations/nlt.json
   ```

3. Load the JSON into the database:

   ```bash
   python -m soap_journal.cli load-translation ../data/translations/nlt.json
   ```

4. Restart the server (or refresh the browser). The NLT translation
   will appear in the reader.

**Footnotes**: The NLT print edition has extensive footnotes, but this
particular PDF rendering does not preserve them. Footnote data is not
available in the parsed output.

**Verse numbering**: The NLT omits certain disputed verses (e.g.
Acts 8:37, John 5:4, Mark 9:44). Verses are renumbered sequentially
within each chapter to satisfy the canonical schema's 1..N invariant.

**Copyright**: Holy Bible, New Living Translation, copyright (c) 1996,
2004, 2015 by Tyndale House Foundation. Used by permission of Tyndale
House Publishers, Carol Stream, Illinois 60188. All rights reserved.

## Adding Other Translations

The general pattern is the same for any translation:

1. Obtain a machine-readable source (PDF, USFM, OSIS XML, plain text).
2. Write a parser at `backend/soap_journal/parsers/<code>.py` that
   converts the source into the canonical JSON schema
   (`backend/soap_journal/parsers/schema.py`). See the BSB and NKJV
   parsers as reference implementations.
3. Run the parser, then load with `load-translation`.

See `CONTRIBUTING.md` for details on the parser architecture.
