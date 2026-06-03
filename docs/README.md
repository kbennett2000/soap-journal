# soap-journal documentation

Two paths through these docs, depending on what you came here to do.

## I want to install soap-journal

Start at the [install hub](install/README.md) and pick the guide for your
computer — **Windows**, **Mac**, or a dedicated **Linux / Ubuntu server**.
Each one walks through every step from "I just downloaded this, what now?"
to "I'm logged in as the admin," explaining every command and showing
screenshots of every screen. soap-journal runs the same on all three; only
the setup steps differ.

If you hit a problem along the way, check
[install troubleshooting](install/troubleshooting.md).

## I have soap-journal installed and I want to learn what it does

Start with the [usage guide](usage/README.md). Nine short chapters
that cover every feature: reading, journaling, tagging, searching,
the calendar, admin tasks, and backups.

---

## What's in here

- [`install/README.md`](install/README.md) — the install hub; pick your
  platform here.
- [`install/windows.md`](install/windows.md) — install on a Windows PC with
  Docker Desktop (plus an [advanced no-Docker guide](install/windows-manual.md)).
- [`install/macos.md`](install/macos.md) — install on a Mac with Docker
  Desktop.
- [`install/ubuntu-server.md`](install/ubuntu-server.md) — the full
  walkthrough for a dedicated Ubuntu/Linux home server.
- [`install/manual.md`](install/manual.md) — advanced: installing on
  Linux/macOS without Docker.
- [`install/troubleshooting.md`](install/troubleshooting.md) —
  symptoms, diagnoses, and fixes for install-time problems (with a
  Windows & Mac section).
- [`configuration.md`](configuration.md) — the optional `.env` settings and
  what each one does.
- [`bibles.md`](bibles.md) — the 13 bundled translations and how to add your
  own.
- [`usage/`](usage/) — the end-user usage guide, in nine chapters.
- [`screenshots/`](screenshots/) — the PNG screenshots embedded in
  every doc. Captured from a real running instance by the script at
  [`scripts/capture-screenshots/`](../scripts/capture-screenshots/);
  re-run that script when the UI changes.

## Known gaps

Things this set of docs deliberately doesn't cover for v0.1, listed
here so you know not to look for them:

- **HTTPS / reverse-proxy setup guides.** v0.1 is HTTP-only on a
  trusted LAN. If you want HTTPS you're on your own; see
  [`install/troubleshooting.md`](install/troubleshooting.md#can-i-access-this-from-outside-my-network).
- **Dark-theme screenshots.** Every embedded screenshot is the light
  theme. The dark theme works, but capturing both is out of scope for
  v0.1.
- **Loading additional copyrighted translations.** 13 public-domain
  translations ship and load automatically. Adding a copyrighted one you
  own (ESV, NLT, NKJV) is documented in
  [`../bibles/README.md`](../bibles/README.md), but it's a
  command-line task, not a point-and-click one in the UI.
- **Mobile-specific gestures (swipe between chapters, pull-to-refresh,
  etc.).** None are wired up in v0.1. The mobile UI here is the responsive
  desktop UI; everything works via tap and on-screen buttons. (Want a native
  phone app instead? **[SOAP Journal for Android](https://github.com/kbennett2000/soap-journal-mobile)**
  is a separate, standalone project.)
- **A "tag manager" page.** You can add and remove tags on individual
  entries; there's no rename-or-merge UI yet. See
  [`usage/06-tags.md`](usage/06-tags.md).
- **An entry-export feature.** If you want a copy of your entries
  outside the app, back up the `data/` folder
  ([`usage/09-backups-and-updates.md`](usage/09-backups-and-updates.md)).
  A friendlier export is a v0.2-and-later topic.
- **Self-service password reset.** Admin-only, via the admin user
  list. Documented in
  [`usage/08-admin-tasks.md`](usage/08-admin-tasks.md) and
  [`install/troubleshooting.md`](install/troubleshooting.md#i-forgot-the-admin-password).
