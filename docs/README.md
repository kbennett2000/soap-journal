# soap-journal documentation

Two paths through these docs, depending on what you came here to do.

## I want to install soap-journal on my server

Start with the [install guide](install/README.md). It walks through
every step from "I have an Ubuntu Server, what now?" to "I'm logged
in as the admin," explaining every command and showing screenshots of
every screen.

If you hit a problem along the way, check
[install troubleshooting](install/troubleshooting.md).

## I have soap-journal installed and I want to learn what it does

Start with the [usage guide](usage/README.md). Nine short chapters
that cover every feature: reading, journaling, tagging, searching,
the calendar, admin tasks, and backups.

---

## What's in here

- [`install/README.md`](install/README.md) — the full Ubuntu Server
  install walkthrough.
- [`install/troubleshooting.md`](install/troubleshooting.md) —
  symptoms, diagnoses, and fixes for install-time problems.
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
  etc.).** None are wired up in v0.1. The mobile UI is the responsive
  desktop UI; everything works via tap and on-screen buttons.
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
