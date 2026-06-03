# soap-journal — Specification

## 1. Summary

`soap-journal` is a self-hosted web app for SOAP-method Bible journaling with an integrated Bible reader. It is built for households, small groups, or individuals running a home server and is distributed under MIT on GitHub so anyone can clone, build, and run it.

### Core constraints

- Runs anywhere Docker does — a dedicated Ubuntu/Linux server on a LAN is the primary design target, and Docker Desktop on Windows or macOS is a supported install too.
- After installation and initial configuration, operates **100% offline** with no internet calls.
- Port is configurable via environment variable.
- Multi-user, with auth and per-user private journals.
- Designed for a parser architecture so new Bible translations can be added over time.

## 2. Users and Auth

- The first registered user becomes **admin**.
- The admin can either enable **open self-registration** or keep registration closed and create accounts manually.
- Auth is **username + password only**. No email, no SMS, no external identity providers.
- Passwords hashed with argon2 via Passlib.
- Sessions are **long-lived cookies** (stay-logged-in across browser restarts) with an explicit **Log Out** button.
- **Password reset**: admin-only. The admin can reset any user's password from an admin panel. No self-service reset in v1.
- Admin can promote/demote other users to/from admin.

## 3. Features (v1)

### 3.1 SOAP Journal

Each entry has:

- **Title** (optional; auto-generated from the passage if blank, e.g. "John 3:16-21").
- **Date** (defaults to today; editable).
- **Scripture reference** (e.g. `John 3:16-21`). Reference is parsed and the Scripture text is auto-pulled from the loaded translation so the user doesn't retype it.
- **Observation** — what the passage says.
- **Application** — how it applies to the user's life.
- **Prayer** — written prayer in response.
- **Tags** — free-form, with autocomplete based on tags the user has previously used.

### 3.2 Bible Reader

- Browse by book and chapter.
- Jump bar that accepts references like `John 3:16`, `Jn 3:16`, `Rom 8:28-30`.
- Verse-by-verse view and paragraph view toggle.
- Adjustable font size.
- Light and dark themes.
- Click any verse to start a new SOAP entry pre-filled with that reference.
- **Side-by-side translation comparison**: active by default, since multiple translations are bundled and loaded on first run. (The UI still falls back to a disabled affordance if an instance somehow has only one translation loaded.)
- **Cross-reference from passage to entries**: when reading a chapter, the UI shows "you have N journal entries on this passage" with links to those entries.
- **Translator's notes and cross-references** (notes-bearing translations, i.e. NET): inline superscript markers mark each typed note at its position in the verse — translator (`tn`), study (`sn`), text-critical (`tc`), and map (`map`). Clicking a marker opens the note (its type label + body) with tappable **cross-reference links** that navigate to the cited passage. Plain translations show no markers and read exactly as before.
- **Scripture full-text search**: a dedicated "Search Scripture" surface searches verse text and translator's notes — within one translation, or across **all** loaded translations grouped to one row per canonical verse. Distinct from journal-entry search (§3.3); the two are never merged.
- **Highlights / annotations**: select verse text to highlight it in one of six colors. A highlight can **span multiple verses** within a chapter, **overlap** other highlights (shown with a "+N" indicator), and carry an optional plain-text **note**. Change color, edit the note, or delete from an **annotation panel** — a docked side-panel on desktop, a slide-up bottom-sheet on mobile (touch selection supported). A highlight is **visible only in the translation it was made in** (its character offsets are meaningless against differently-worded text).

### 3.3 Retrieval and Discovery

- **Keyword search** across the user's entries (title, observation, application, prayer, scripture text). This is journal-entry search; **scripture full-text search** over verses + translator's notes is a separate reader feature (§3.2).
- **Filter** by book, passage, and/or tag.
- **Calendar view** of entries by month.
- **"On this day in previous years"** — surface entries from the same date in prior years.

### 3.4 Landing Page

After login, the user lands on a **dashboard** showing:

- Recent entries.
- "On this day" entries.
- A jump-to-reader bar.
- A "new entry" call to action.

### 3.5 Admin Panel

- List all users.
- Create / delete users.
- Reset any user's password.
- Promote / demote admins.
- Toggle open registration.
- View loaded translations. (Loading a new translation is an operator/CLI task — see §4 — not an admin-panel action in v1.)

## 4. Bible Text and Parser Architecture

### 4.1 Bundled translations

v1 bundles **13 public-domain translations**, all parsed and loaded automatically on first run: BSB plus 12 PDFMaker-format translations (KJV, AKJV, ASV, CPDV, DBT, DRB, ERV, JPS, SLT, WBT, WEB, YLT).

The parser architecture is designed so more translations can be added over time without shipping their text in the repo. Parsers for four user-supplied translations are included — three copyrighted (ESV, NKJV, NLT) plus **NET** (New English Translation) — but the repo ships no such text: a user supplies their own legally-obtained PDF via the gitignored `bibles/` directory and parses it locally.

**NET is distinctive.** Unlike every bundled translation, NET carries tens of thousands of **typed translator's notes** (`tn/sn/tc/map`), each anchored to a character offset in its verse, many with **cross-references** to other passages. The reader surfaces all of it (§3.2). Loading NET is what makes the notes/cross-references and notes-aware scripture search visible on an instance. Per-translation build/load steps for NET (and ESV/NKJV/NLT) are in `bibles/README.md`.

### 4.2 Canonical format

A normalized JSON schema for Bible text. Roughly:

```
{
  "code": "BSB",
  "name": "Berean Standard Bible",
  "language": "en",
  "copyright": "Public domain / permissive notice text",
  "books": [
    {
      "name": "Genesis",
      "abbreviation": "Gen",
      "chapters": [
        {
          "number": 1,
          "verses": [
            { "number": 1, "text": "In the beginning..." }
          ],
          "headings": [
            { "before_verse": 1, "text": "The Creation" }
          ]
        }
      ]
    }
  ]
}
```

The schema must accommodate (at minimum): section headings; footnotes — optionally **typed** (`tn/sn/tc/map`), anchored to a character offset within the verse, and carrying **cross-references** to other passages (used by NET; plain translations leave these fields unset); and a red-letter flag per verse. Schema lives in `backend/soap_journal/parsers/schema.py` and is the single source of truth.

### 4.3 Parsers

Each translation has a **parser**: a standalone CLI module that ingests a source format (PDF, USFM, OSIS XML, plain text, etc.) and writes a canonical JSON file. Parsers are independent of the running server and the database. Example:

```
python -m soap_journal.parsers.bsb path/to/bsb.txt --out data/translations/bsb.json
python -m soap_journal.parsers.nkjv path/to/nkjv.pdf --out data/translations/nkjv.json
```

Loading a canonical JSON file into the DB is a separate step (a CLI command):

```
python -m soap_journal.cli load-translation data/translations/bsb.json
```

The app **only ever reads canonical format** from the DB. Adding a translation = write a parser, run it, load the output.

### 4.4 Bundled parsers

Two parser kinds cover the 13 bundled translations. BSB ingests a clean tab-separated text source, so its parser is essentially a format adapter. The 12 public-domain translations share a single **PDFMaker-format** PDF parser. The first-run setup runs all 13 (each independently and idempotently) so users have a full Bible — and the side-by-side comparison view — working immediately. The same parser architecture handles user-supplied copyrighted PDFs (ESV/NKJV/NLT) via their own parser modules.

## 5. Data Model (sketch)

- `users` — id, username, password_hash, is_admin, created_at.
- `sessions` — id, user_id, token, expires_at.
- `settings` — key/value table for admin-toggleable flags (`open_registration`, etc.).
- `translations` — id, code, name, language, copyright_notice, loaded_at.
- `books` — id, translation_id, name, abbreviation, order_index.
- `chapters` — id, book_id, number.
- `verses` — id, chapter_id, number, text, is_red_letter.
- `headings` — id, chapter_id, before_verse, text.
- `footnotes` — id, verse_id, marker, text, `note_type`, `char_offset`, `ordinal` (the typed/anchored note fields are NULL for the plain translations; populated for NET).
- `cross_references` — id, footnote_id, to_book_id, to_chapter, to_verse_start, to_verse_end (a note's links to other passages; the source verse is derived from the footnote).
- `annotations` — id, user_id, translation_code, book, chapter, verse_start, verse_end, char_start, char_end, color, note, created_at, updated_at (per-user highlights). Anchored by **canonical coordinates + translation code**, deliberately **not** by `verses.id`/`translations.id` foreign keys, so a translation reload (delete+insert) can't orphan a user's highlights. Searchable verse/note text is mirrored into FTS5 tables (`verses_fts`, `notes_fts`) maintained by the loader.
- `entries` — id, user_id, title, entry_date, scripture_ref, scripture_translation_id, observation, application, prayer, created_at, updated_at.
- `entry_scripture_verses` — junction so an entry can be linked to specific verses for cross-reference lookups (entry_id, verse_id).
- `tags` — id, user_id, name (unique per user).
- `entry_tags` — entry_id, tag_id.

## 6. Configuration

A `.env` file at the repo root, generated from `.env.example` on first run. Keys:

- `PORT` — host-side port Compose maps to the container's internal `8080`; this is what you browse to, not the port the server itself binds. Default `8045`.
- `DATA_DIR` — absolute or relative path to the data directory. Default `./data`.
- `SECRET_KEY` — used for session signing. Generated on first run if absent.
- `BIND_HOST` — default `0.0.0.0` so LAN access works.

Self-registration is **not** an env var: it's a DB-seeded setting (default "closed") that the admin toggles at runtime via the admin API (`PUT /api/v1/admin/settings`) after the first user signs up.

## 7. Deployment

- Single `docker compose up` brings up the app.
- The Compose file mounts `./data` as a volume and reads from `.env`.
- Supported on Linux (Docker Engine) and on Windows/macOS (Docker Desktop, which runs the same Linux image inside its VM — the bash entrypoint, `gosu`, and `chown` all run inside the container regardless of host OS). A dedicated Linux server on a LAN remains the primary target. Per-platform install guides live in `docs/install/`.
- A non-Docker install path (manual `pip install -r requirements.txt` + `npm run build` + `uvicorn`) is documented but Docker is the recommended path.
- A `.gitattributes` forces LF line endings so the container entrypoint is never CRLF-corrupted by a Windows clone; the Dockerfile also strips stray CRs as a safety net.

## 8. Out of Scope for v1

(Mirrors `CLAUDE.md` — kept here for the human-facing spec.)

- Reading plans
- Bookmarks (navigational markers). **Verse highlights are built** — see §3.2 — and are no longer out of scope.
- Export to Markdown / PDF / zip
- Built-in backups (users copy the data folder)
- Random entry / rediscover
- Self-service password reset
- User-to-user sharing
- Native mobile apps
- Audio Bible, commentary, original-language tools
- Outbound internet calls of any kind at runtime
- Copyrighted / restricted translations shipping in the repo (parsers for ESV/NKJV/NLT **and NET** are included, but users supply their own PDFs; only the 13 public-domain translations are bundled)
- Refinements within the now-built highlight layer that remain deferred: highlights in the side-by-side **compare** view, **Markdown** formatting in highlight notes, a **drag-to-resize** mobile sheet, and a chooser to cycle through every annotation beneath a "+N" **overlap** stack (clicking a stack opens the top one).

## 9. Future Considerations

Not commitments — just things the architecture should not preclude:

- Additional translations via new parsers (already designed in).
- Reading plans (would add a `plans` and `plan_progress` table).
- Bookmarks (quick navigational markers). Verse **highlights** are now built (the `annotations` table, §5); bookmarks are a separate, still-future idea.
- Export and import (data is already in a single folder, so a "download zip" is straightforward).
- Group / shared journals (would require a new permissions layer; intentionally not designed in for v1).
