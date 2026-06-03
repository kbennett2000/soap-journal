# Installing soap-journal on a Mac

This guide walks you through installing soap-journal on a Mac. It assumes you
have never used Docker, never installed anything like this before, and would
rather have a few small steps explained than one big one rushed.

By the end you'll have soap-journal running on your Mac and you'll be logged in as
the administrator, reading and journaling in your web browser.

The whole thing takes about 20 minutes, most of which is waiting for things to
download.

If you get stuck, see [`troubleshooting.md`](troubleshooting.md).

---

## What you will need

- **A Mac running macOS 12 (Monterey) or newer.** Both Apple Silicon (M1, M2, M3,
  M4) and Intel Macs work — the install is the same; you just download the
  matching version of Docker Desktop in Step 1.
- **About 4 GB of free disk space.** Docker Desktop and the soap-journal image
  together are a couple of gigabytes; your Bible text and journal take well under
  100 MB; the rest is headroom.
- **An internet connection during install.** soap-journal makes no internet
  connections once it's running, but the install needs to download Docker and the
  app. After that you can be fully offline.

You do **not** need to install Python, Node, a database, or anything else —
Docker bundles all of that for you.

---

## Step 1: Install Docker Desktop

Docker is what runs soap-journal. Think of it as a sealed box that already
contains everything the app needs — the web server, the database, the Bible text
— so you don't have to install any of those pieces yourself. "Docker Desktop" is
the friendly Mac version of Docker, with a window you can click around in.

### 1.1 Find out which Mac you have

Click the  **Apple menu** (top-left) → **About This Mac**. Look at the **Chip**
(or **Processor**) line:

- If it says **Apple M1 / M2 / M3 / M4** → you have **Apple Silicon**.
- If it says **Intel** → you have an **Intel** Mac.

You'll use this in the next step to download the right version.

### 1.2 Download and install Docker Desktop

Open <https://www.docker.com/products/docker-desktop/> and click the download
button for your chip — **Download for Mac – Apple Silicon** or **Download for Mac
– Intel Chip**.

You'll get a file called `Docker.dmg`. Double-click it, then **drag the Docker
icon into the Applications folder** in the window that appears.

### 1.3 Start Docker Desktop

Open **Docker** from your Applications folder (or Launchpad). The first launch
asks you to confirm you want to open it and may ask for your Mac password to
finish setting up — that's expected. Accept the service agreement if it asks. You
can skip the sign-in / "create an account" prompts — you don't need a Docker
account to run soap-journal.

**What you should see:** the Docker Desktop window, and a little whale icon in the
menu bar at the top of your screen. When the whale stops animating and sits still,
Docker is ready.

> 💡 **Leave Docker Desktop running.** soap-journal only works while Docker
> Desktop is running. You can set it to start automatically at login in Docker
> Desktop's settings (**Settings → General → Start Docker Desktop when you sign
> in**), so once it's set up you can mostly forget about it.

### 1.4 Check it works

Open the **Terminal** app (press **Cmd + Space**, type `Terminal`, press
**Enter**). A window with a text prompt appears — this is where you'll type the
next few commands. Type this and press **Enter**:

```bash
docker --version
docker compose version
```

**What you should see:** two lines, something like

```
Docker version 27.3.1, build ce12230
Docker Compose version v2.29.7
```

**If you see this error:** `command not found: docker` — Docker Desktop either
isn't installed or isn't running. Make sure the whale icon is in your menu bar and
sitting still, then try again (you may need to close and reopen Terminal).

---

## Step 2: Download soap-journal

You have two ways to get the soap-journal files. Pick whichever feels easier.

### Option A — the simple way: download the ZIP

1. Open <https://github.com/kbennett2000/soap-journal> in your browser.
2. Click the green **Code** button, then **Download ZIP**.
3. Find `soap-journal-main.zip` in your Downloads folder and double-click it to
   unzip. You'll get a folder named `soap-journal-main`.
4. Move that folder somewhere easy to find — your **Documents** folder is fine.

Then, in Terminal, move into the folder:

```bash
cd ~/Documents/soap-journal-main
```

### Option B — using Git

Macs include Git (the first time you use it, macOS may offer to install the
developer command-line tools — accept it). In Terminal:

```bash
cd ~/Documents
git clone https://github.com/kbennett2000/soap-journal.git
cd soap-journal
```

**What you should see:** after `cd`, your Terminal prompt shows the folder name.
That means you're "inside" the folder and ready for the next steps.

---

## Step 3: Create your settings file

soap-journal reads its settings from a file named `.env`. The download includes a
ready-made example called `.env.example`; you just make a copy of it named `.env`.
The defaults are fine for a normal install.

In Terminal (inside the soap-journal folder), run:

```bash
cp .env.example .env
```

**What you should see:** nothing — `cp` is silent when it works. (You now have a
`.env` file next to `.env.example`.)

> 💡 **Want to change the port?** By default soap-journal answers on port `8045`.
> If something else on your Mac already uses that port, open `.env` in TextEdit
> (`open -e .env`), change `PORT=8045` to another number like `PORT=8055`, save,
> and close. For a normal install you can skip this.

---

## Step 4: Start soap-journal

Make sure **Docker Desktop is running** (whale in the menu bar), then in Terminal
run:

```bash
docker compose up -d
```

**What this does:** tells Docker to assemble the soap-journal box and start it in
the background. The `-d` means "detached" — it runs quietly and gives you your
Terminal prompt back.

**What you should see:** the **first** time, Docker downloads the base pieces and
builds the app. This takes a few minutes and prints a lot of progress lines,
ending with something like:

```
[+] Running 1/1
 ✔ Container soap-journal  Started
```

**If you see this error:** `Cannot connect to the Docker daemon` — Docker Desktop
isn't running. Start it, wait for the whale to settle, and run the command again.

**If you see this error:** `Bind for 0.0.0.0:8045 failed: port is already
allocated` — something else on your Mac is using port 8045. Change `PORT` in
`.env` (see the tip in Step 3) to another number like `8055`, then run
`docker compose up -d` again.

### The first start loads the Bibles (give it a few minutes)

On the very first start, soap-journal loads 13 Bible translations into its
database. This takes a few minutes. To watch it happen, run:

```bash
docker compose logs -f
```

**What you should see:** lines counting through the translations, then a "startup
complete" message:

```
soap-journal  | [entrypoint] (1/13) loading BSB into the database
soap-journal  | [entrypoint] (1/13) BSB loaded
soap-journal  | ... (the rest, through 13/13) ...
soap-journal  | INFO:     Application startup complete.
soap-journal  | INFO:     Uvicorn running on http://0.0.0.0:8080
```

Those last two lines mean it's ready. **Press Ctrl + C to stop watching the
logs** — that just stops the log view; soap-journal keeps running in the
background.

---

## Step 5: Open soap-journal in your browser

Open any web browser on this Mac and go to:

```
http://localhost:8045
```

(`localhost` means "this same computer." If you changed the port in Step 3, use
that number instead of `8045`.)

### 5.1 The login page

You should see this:

![Login page with Log in and Register tabs, Username and Password fields, and a Log in button](../screenshots/install-login-page.png)

If the page doesn't load, give it another minute (the first boot may still be
loading Bibles), then refresh. Still nothing? See
[`troubleshooting.md`](troubleshooting.md).

### 5.2 Register the first user

The first person to register on a fresh install **becomes the administrator** —
they can create other accounts, reset passwords, and change settings. Make this
you.

1. Click the **Register** tab.
2. Choose a username (3–32 characters: letters, digits, underscore, hyphen).
3. Choose a password (at least 8 characters). Pick something you'll remember —
   there is no self-service password reset.

   ![Register tab with a username filled in and password dots in the password field](../screenshots/install-register-tab.png)

4. Click **Register**.

### 5.3 You're in

You'll land on your dashboard:

![Empty dashboard with a Welcome message, a Jump to a passage bar, and empty Recent entries and On this day panels](../screenshots/install-dashboard-first-time.png)

It's empty for now because you haven't written anything yet. That's the fun part,
and the [usage guide](../usage/README.md) walks you through it.

---

## Using soap-journal from your phone or other devices

`http://localhost:8045` only works on the Mac running soap-journal. To open it
from your phone, tablet, or another computer on the same home network, you need
that Mac's **local IP address**.

The quickest way, in Terminal:

```bash
ipconfig getifaddr en0
```

That prints something like `192.168.1.50`. (If it prints nothing, you're probably
on Ethernet or a different adapter — try `en1`, or look in **System Settings →
Wi-Fi → Details… → IP Address**.) On your other device's browser, go to:

```
http://192.168.1.50:8045
```

using your actual address. Bookmark it on every device you'll journal from.

---

## Everyday use

- **Starting and stopping:** soap-journal starts whenever Docker Desktop is
  running. To stop it, run `docker compose stop` in the soap-journal folder; to
  start it again, `docker compose start`.
- **Your data:** everything you write lives in the `data` folder inside the
  soap-journal folder. To back it up, stop soap-journal and copy that folder
  somewhere safe. See
  [`docs/usage/09-backups-and-updates.md`](../usage/09-backups-and-updates.md).

---

## You're done. What now?

1. **Bookmark the address** on every device you'll use to journal.
2. **Read the [usage guide](../usage/README.md)** to learn what each screen does.
3. **Set up backups** — copy the `data` folder periodically
   ([how](../usage/09-backups-and-updates.md)).
4. **Decide whether to let others register accounts.** Registration is closed
   after the first user by default; see
   [`docs/usage/08-admin-tasks.md`](../usage/08-admin-tasks.md) to open it up or
   create accounts for family members yourself.
