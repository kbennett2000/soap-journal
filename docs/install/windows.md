# Installing soap-journal on Windows

This guide walks you through installing soap-journal on a Windows PC. It assumes
you have never used Docker, never installed anything like this before, and would
rather have a few small steps explained than one big one rushed.

By the end you'll have soap-journal running on your PC and you'll be logged in as
the administrator, reading and journaling in your web browser.

The whole thing takes about 20 minutes, most of which is waiting for things to
download.

If you get stuck, see [`troubleshooting.md`](troubleshooting.md).

> **Prefer not to use Docker?** There's an
> [advanced guide that installs the pieces directly](windows-manual.md). It's
> longer and fussier, and we only recommend it if you have a specific reason to
> avoid Docker. For almost everyone, the steps below are the easy path.

---

## What you will need

- **A PC running Windows 10 or Windows 11** (64-bit). Windows 11 is smoothest.
- **About 4 GB of free disk space.** Docker Desktop and the soap-journal image
  together are a couple of gigabytes; your Bible text and journal take well under
  100 MB; the rest is headroom.
- **Administrator access** on the PC (you'll need it to install Docker Desktop).
- **An internet connection during install.** soap-journal makes no internet
  connections once it's running, but the install needs to download Docker and the
  app. After that you can be fully offline.

That's it. You do **not** need to install Python, Node, a database, or anything
else — Docker bundles all of that for you.

---

## Step 1: Install Docker Desktop

Docker is what runs soap-journal. Think of it as a sealed box that already
contains everything the app needs — the web server, the database, the Bible text
— so you don't have to install any of those pieces yourself. "Docker Desktop" is
the friendly Windows version of Docker, with a window you can click around in.

### 1.1 Download Docker Desktop

Open <https://www.docker.com/products/docker-desktop/> in your browser and click
**Download for Windows**. You'll get a file called `Docker Desktop Installer.exe`
in your Downloads folder.

### 1.2 Run the installer

Double-click `Docker Desktop Installer.exe`.

**What this does:** installs Docker Desktop and, if it's not already on your PC,
a Windows component called **WSL 2** (a lightweight Linux engine Docker uses
under the hood). The installer handles WSL 2 for you — just leave the default
options checked.

**What you should see:** a progress window, then a prompt to **close and restart**
or **sign out**. Do it — Docker needs the restart to finish setting up.

> ⚠️ **If the installer mentions "WSL 2" and asks you to install or update it:**
> say yes / follow the link it gives you. This is normal and only happens once.
> If it sends you to a Microsoft page, download and run the small update it
> offers, then re-run the Docker Desktop installer.

### 1.3 Start Docker Desktop

After the restart, open **Docker Desktop** from the Start menu. The first launch
takes a minute while the engine starts. Accept the service agreement if it asks.
You can skip the sign-in / "create an account" prompts — you don't need a Docker
account to run soap-journal.

**What you should see:** the Docker Desktop window, and a little whale icon in your
system tray (bottom-right of the taskbar, near the clock). When the whale stops
animating and sits still, Docker is ready.

> 💡 **Leave Docker Desktop running.** soap-journal only works while Docker
> Desktop is running. By default Docker Desktop starts automatically when you log
> in to Windows, so once it's set up you can mostly forget about it.

### 1.4 Check it works

Open **PowerShell** (press the **Start** button, type `PowerShell`, press
**Enter**). A blue window with a text prompt appears. This is where you'll type
the next few commands. Type this and press **Enter**:

```powershell
docker --version
docker compose version
```

**What you should see:** two lines, something like

```
Docker version 27.3.1, build ce12230
Docker Compose version v2.29.7
```

**If you see this error:** `docker : The term 'docker' is not recognized` — Docker
Desktop either isn't installed or isn't running. Make sure the whale icon is in
your tray and sitting still, then try again. You may need to close and reopen
PowerShell.

---

## Step 2: Download soap-journal

You have two ways to get the soap-journal files. Pick whichever feels easier —
both end up in the same place.

### Option A — the simple way: download the ZIP

1. Open <https://github.com/kbennett2000/soap-journal> in your browser.
2. Click the green **Code** button, then **Download ZIP**.
3. Find `soap-journal-main.zip` in your Downloads folder, right-click it, and
   choose **Extract All…**. Extract it somewhere easy to find — your **Documents**
   folder is a fine choice.
4. You'll end up with a folder like `Documents\soap-journal-main`.

### Option B — using Git

If you already have [Git for Windows](https://git-scm.com/download/win) installed,
in PowerShell run:

```powershell
cd ~\Documents
git clone https://github.com/kbennett2000/soap-journal.git
```

Either way, **move into the folder** in PowerShell so the next commands run in the
right place. Use the name that matches what you got:

```powershell
cd ~\Documents\soap-journal-main   # if you downloaded the ZIP
# or
cd ~\Documents\soap-journal        # if you used Git
```

**What you should see:** your PowerShell prompt now shows the folder name, e.g.
`PS C:\Users\you\Documents\soap-journal-main>`. That means you're "inside" the
folder and ready for the next steps.

---

## Step 3: Create your settings file

soap-journal reads its settings from a file named `.env`. The download includes a
ready-made example called `.env.example`; you just make a copy of it named `.env`.
The defaults are fine for a normal install, so you won't need to change anything.

In PowerShell (still inside the soap-journal folder), run:

```powershell
Copy-Item .env.example .env
```

**What you should see:** nothing — `Copy-Item` is silent when it works. (You now
have a `.env` file next to `.env.example`.)

> 💡 **Want to change the port?** By default soap-journal answers on port `8045`.
> If something else on your PC already uses that port, open `.env` in Notepad
> (`notepad .env`), change `PORT=8045` to another number like `PORT=8055`, save,
> and close. For a normal install you can skip this.

---

## Step 4: Start soap-journal

This is the step that does the real work. Make sure **Docker Desktop is running**
(whale icon in the tray), then in PowerShell run:

```powershell
docker compose up -d
```

**What this does:** tells Docker to assemble the soap-journal box and start it in
the background. The `-d` means "detached" — it runs quietly and gives you your
PowerShell prompt back.

**What you should see:** the **first** time, Docker downloads the base pieces and
builds the app. This takes a few minutes and prints a lot of progress lines,
ending with something like:

```
[+] Running 1/1
 ✔ Container soap-journal  Started
```

> 🔔 **A Windows Defender Firewall pop-up may appear** the first time, asking
> whether to allow Docker to accept connections. Click **Allow access**. (If you
> only ever open soap-journal on this same PC, you can dismiss it — but allowing
> it is what lets your phone and other devices reach it later.)

**If you see this error:** `error during connect ... The system cannot find the
file specified` — Docker Desktop isn't running. Start it, wait for the whale to
settle, and run the command again.

**If you see this error:** `Bind for 0.0.0.0:8045 failed: port is already
allocated` — something else on your PC is using port 8045. Change `PORT` in `.env`
(see the tip in Step 3) to another number like `8055`, then run
`docker compose up -d` again.

### The first start loads the Bibles (give it a few minutes)

On the very first start, soap-journal loads 13 Bible translations into its
database. This takes a few minutes. To watch it happen, run:

```powershell
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

Open any web browser on this PC and go to:

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

`http://localhost:8045` only works on the PC running soap-journal. To open it from
your phone, tablet, or another computer on the same home network, you need that
PC's **local IP address**.

In PowerShell, run:

```powershell
ipconfig
```

Look for the **IPv4 Address** under your active connection (Wi-Fi or Ethernet) —
something like `192.168.1.50`. On your other device's browser, go to:

```
http://192.168.1.50:8045
```

(using your actual address). Bookmark it on every device you'll journal from.

> If your phone can't reach it, the most common cause is the Windows firewall — see
> [the firewall entry in troubleshooting](troubleshooting.md#other-devices-on-my-network-cant-reach-soap-journal-windows).

---

## Everyday use

- **Starting and stopping:** soap-journal starts automatically with Docker Desktop.
  To stop it, run `docker compose stop` in the soap-journal folder; to start it
  again, `docker compose start`.
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
