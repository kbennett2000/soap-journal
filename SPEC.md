# soap-journal — Specification

## 1. Summary

`soap-journal` is a self-hosted web app for SOAP-method Bible journaling with an integrated Bible reader. It is built for households, small groups, or individuals running a home server and is distributed under MIT on GitHub so anyone can clone, build, and run it.

### Core constraints

- Runs on Ubuntu, served over a local LAN.
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
- **Side-by-side translation comparison**: UI element is always present but disabled and grayed until a second translation is loaded.
- **Cross-reference from passage to entries**: when reading a chapter, the UI shows "you have N journal entries on this passage" with links to those entries.

### 3.3 Retrieval and Discovery

- **Keyword search** across the user's entries (title, observation, application, prayer, scripture text).
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
- View loaded translations and load new ones (point at a canonical JSON file on disk).

## 4. Bible Text and Parser Architecture

### 4.1 v1 ships with BSB

The Berean Standard Bible is bundled. No other translation is included in the v1 repo.

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

The schema must accommodate (at minimum): section headings, footnotes, and a red-letter flag per verse. Schema lives in `backend/soap_journal/parsers/schema.py` and is the single source of truth.

### 4.3 Parsers

Each translation has a **parser**: a standalone CLI module that ingests a source format (PDF, USFM, OSIS XML, plain text, etc.) and writes a canonical JSON file. Parsers are independent of the running server and the database. Example:

```
python -m soap_journal.parsers.bsb path/to/source.json --out data/translations/bsb.json
python -m soap_journal.parsers.nkjv path/to/nkjv.pdf --out data/translations/nkjv.json
```

Loading a canonical JSON file into the DB is a separate step (CLI command or admin-panel action):

```
python -m soap_journal.cli load-translation data/translations/bsb.json
```

The app **only ever reads canonical format** from the DB. Adding a translation = write a parser, run it, load the output.

### 4.4 BSB parser in v1

BSB is available in clean structured formats already, so the BSB parser is essentially a format adapter. It ships in the repo. The v1 install runs it as part of first-run setup so users have a working Bible immediately.

## 5. Data Model (sketch)

- `users` — id, username, password_hash, is_admin, created_at.
- `sessions` — id, user_id, token, expires_at.
- `settings` — key/value table for admin-toggleable flags (`open_registration`, etc.).
- `translations` — id, code, name, language, copyright_notice, loaded_at.
- `books` — id, translation_id, name, abbreviation, order_index.
- `chapters` — id, book_id, number.
- `verses` — id, chapter_id, number, text, is_red_letter.
- `headings` — id, chapter_id, before_verse, text.
- `footnotes` — id, verse_id, marker, text.
- `entries` — id, user_id, title, entry_date, scripture_ref, scripture_translation_id, observation, application, prayer, created_at, updated_at.
- `entry_scripture_verses` — junction so an entry can be linked to specific verses for cross-reference lookups (entry_id, verse_id).
- `tags` — id, user_id, name (unique per user).
- `entry_tags` — entry_id, tag_id.

## 6. Configuration

A `.env` file at the repo root, generated from `.env.example` on first run. Keys:

- `PORT` — port the server listens on. Default `8045`.
- `DATA_DIR` — absolute or relative path to the data directory. Default `./data`.
- `SECRET_KEY` — used for session signing. Generated on first run if absent.
- `OPEN_REGISTRATION` — `true` / `false`. Admin can also toggle at runtime.
- `BIND_HOST` — default `0.0.0.0` so LAN access works.

## 7. Deployment

- Single `docker compose up` brings up the app.
- The Compose file mounts `./data` as a volume and reads from `.env`.
- A non-Docker install path (manual `pip install -r requirements.txt` + `npm run build` + `uvicorn`) is documented but Docker is the recommended path.

## 8. Out of Scope for v1

(Mirrors `CLAUDE.md` — kept here for the human-facing spec.)

- Reading plans
- Bookmarks / highlights
- Export to Markdown / PDF / zip
- Built-in backups (users copy the data folder)
- Random entry / rediscover
- Self-service password reset
- User-to-user sharing
- Native mobile apps
- Audio Bible, commentary, original-language tools
- Outbound internet calls of any kind at runtime
- Translations other than BSB shipping in the repo

## 9. Future Considerations

Not commitments — just things the architecture should not preclude:

- Additional translations via new parsers (already designed in).
- Reading plans (would add a `plans` and `plan_progress` table).
- Highlights and bookmarks (would add a `highlights` table linked to verses).
- Export and import (data is already in a single folder, so a "download zip" is straightforward).
- Group / shared journals (would require a new permissions layer; intentionally not designed in for v1).
