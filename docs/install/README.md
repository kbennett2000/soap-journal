# Installing soap-journal

Welcome! This is the starting line. soap-journal runs on Windows, Mac, and
Linux — and there's a separate, standalone app for Android phones and tablets.
The steps are a little different on each, so the first thing to do is pick the
one that matches the device you'll run it on.

You don't need to be technical. Each guide assumes you've never installed
anything like this before and explains every step in plain English, with
screenshots, and tells you exactly what you should see along the way.

Whichever computer guide you pick, they all end in the same happy place:
soap-journal open in your web browser, with you logged in as the administrator,
ready to read and journal. (The Android app is a little different — it's its own
self-contained app, covered in its own project.)

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

### 📱 I have an Android phone or tablet

This one's **a separate app**, not the self-hosted server above. **SOAP Journal
for Android** is standalone — all 13 translations are built in, there's nothing
to set up, and no computer or server is needed. It lives in its own project.

➡️ **[Get SOAP Journal for Android](https://github.com/kbennett2000/soap-journal-mobile)**

---

## Not sure which to choose?

- **Just want to try it on the computer you use every day?** Pick **Windows** or
  **Mac** — whichever that computer is. This is the easiest way to start, and you
  can always move it to a dedicated server later. Your journal data is just a
  folder you can copy.
- **Want it running 24/7 so everyone in the house can reach it any time, even
  when your laptop is closed?** That's what the **Ubuntu Server** guide is for.
- **Just want it on your Android phone, all self-contained with nothing running
  on a computer?** Use the **[Android app](https://github.com/kbennett2000/soap-journal-mobile)**.

The three computer guides (Windows, Mac, Linux) give you the exact same
self-hosted app — the only difference is the machine it lives on, and they all
end with soap-journal open in your web browser. The **Android app** is a
separate, self-contained build that runs natively on your phone instead.

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
