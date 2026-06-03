# Installing soap-journal

Welcome! This is the starting line. soap-journal runs on Windows, Mac, and
Linux, and the steps are a little different on each — so the first thing to do
is pick the guide that matches the computer you'll run it on.

You don't need to be technical. Each guide assumes you've never installed
anything like this before and explains every step in plain English, with
screenshots, and tells you exactly what you should see along the way.

Whichever you pick, they all end in the same happy place: soap-journal open in
your web browser, with you logged in as the administrator, ready to read and
journal.

---

## Which one are you?

### 🪟 I have a Windows PC

You'll install **Docker Desktop**, then start soap-journal with one command. It
runs quietly in the background and you open it in your browser at
`http://localhost:8045`.

➡️ **[Windows install guide](windows.md)**

*(Prefer not to use Docker? There's an [advanced Windows guide](windows-manual.md)
that installs the pieces directly — but Docker Desktop is much simpler and is the
recommended path.)*

### 🍎 I have a Mac

You'll install **Docker Desktop**, then start soap-journal with one command and
open it in your browser at `http://localhost:8045`. Works the same on Apple
Silicon (M1/M2/M3/M4) and Intel Macs.

➡️ **[Mac install guide](macos.md)**

### 🐧 I have a dedicated Linux / Ubuntu home server

The classic self-hosted setup: a always-on machine on your home network (often
reached over SSH) that serves soap-journal to every device in the house.

➡️ **[Ubuntu Server install guide](ubuntu-server.md)**

---

## Not sure which to choose?

- **Just want to try it on the computer you use every day?** Pick **Windows** or
  **Mac** — whichever that computer is. This is the easiest way to start, and you
  can always move it to a dedicated server later. Your journal data is just a
  folder you can copy.
- **Want it running 24/7 so everyone in the house can reach it any time, even
  when your laptop is closed?** That's what the **Ubuntu Server** guide is for.

All three give you the exact same app. The only difference is the machine it
lives on.

---

## If you get stuck

Every guide links to it, but you can jump straight there:
[**Troubleshooting**](troubleshooting.md) — common problems, what causes them,
and how to fix them, organized by symptom and platform.

---

## Advanced: installing without Docker

Docker is the recommended path for everyone — the guides above use it. If you
have a specific reason to avoid Docker and you're comfortable in a terminal,
there are direct-install guides too:

- [Linux / macOS without Docker](manual.md)
- [Windows without Docker](windows-manual.md)
