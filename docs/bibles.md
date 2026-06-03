# Bibles

soap-journal comes with **13 public-domain Bible translations** built in, and can
load a few more that you supply yourself.

## Bundled translations

These load automatically the first time soap-journal starts — you don't have to
do anything. The side-by-side comparison view works across all of them from the
start.

| Code | Translation | License |
|------|------------|---------|
| BSB | Berean Standard Bible | Permissive |
| KJV | King James Version | Public domain |
| AKJV | American King James Version | Public domain |
| ASV | American Standard Version (1901) | Public domain |
| CPDV | Catholic Public Domain Version | Public domain |
| DBT | Darby Bible Translation (1890) | Public domain |
| DRB | Douay-Rheims Bible | Public domain |
| ERV | English Revised Version (1885) | Public domain |
| JPS | JPS Tanakh / Weymouth NT | Public domain |
| SLT | Smith's Literal Translation (1876) | Public domain |
| WBT | Webster's Bible Translation (1833) | Public domain |
| WEB | World English Bible | Public domain |
| YLT | Young's Literal Translation (1898) | Public domain |

Each translation is checked independently on every start — if one is already
loaded, only the missing ones are parsed, so first boot is the only slow start.

## Adding your own translation

Beyond the bundled 13, soap-journal includes parsers for four translations you
can add **if you have your own copy of the source PDF**: three copyrighted —
**NKJV**, **ESV**, **NLT** — and the **NET** (New English Translation). The repo
ships none of this text.

**NET is special:** it carries the NET's extensive **translator's notes** (typed
translator / study / text-critical / map) and **cross-references**, which the
reader renders inline and which scripture search can search. Loading NET is what
lights up the notes and cross-reference features.

The short version: drop the PDF into the gitignored `bibles/` folder (bind-mounted
to `/app/bibles` in the container), then build and load it:

```bash
docker compose exec soap-journal \
  python -m soap_journal.cli build-translation --code ESV /app/bibles/esv.pdf --out /tmp/esv.json
docker compose exec soap-journal \
  python -m soap_journal.cli load-translation /tmp/esv.json
```

`build-translation` runs the matching parser and validates the result against the
canonical schema in one step, writing the output only if validation passes (so a
failed build never leaves a half-baked file behind). It reports book/chapter/verse
counts and touches no database. `--out` defaults to `./<lowercase-code>.json`. If
you'd rather run the steps separately, the parser
(`python -m soap_journal.parsers.esv <pdf> --out <path>`) and
`validate-translation <path.json>` are still available.

**Full, per-translation instructions** — the exact source format each expects and
the caveats for each — are in [`bibles/README.md`](../bibles/README.md).

## A note on copyright

Only load translations you have the legal right to use. The 13 bundled
translations are public domain or permissively licensed; many modern translations
(ESV, NIV, NASB, etc.) are not. Loading a copyrighted translation onto a server
you control for personal use is between you and the publisher.
