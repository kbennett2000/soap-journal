# Advanced — installing soap-journal on Windows *without* Docker

> ⚠️ **Most people should not use this guide.** The
> [normal Windows guide](windows.md) installs soap-journal with Docker Desktop in
> a handful of steps and is far easier to keep running and update. This page is
> for advanced users who have a specific reason to avoid Docker and are
> comfortable with the PowerShell terminal. It has more moving parts and more ways
> to get stuck.

Without Docker, you install and run each piece yourself: Python (the backend),
Node (to build the frontend), and the soap-journal code. There's no container
managing it for you, so starting it is a command you run, and it keeps running
only as long as that terminal window is open.

All commands below are **PowerShell**. Open it from the Start menu (type
`PowerShell`, press Enter) and run everything from the soap-journal folder.

---

## What you will need

- **Python 3.12 or newer** — <https://www.python.org/downloads/windows/>. During
  install, **check "Add python.exe to PATH"** on the first screen.
- **Node.js 20 LTS or newer** — <https://nodejs.org/> (the "LTS" download).
- **The soap-journal code** — download the ZIP or `git clone` it, as in
  [Step 2 of the Windows guide](windows.md#step-2-download-soap-journal), and `cd`
  into the folder.
- *(Only if you plan to load the user-supplied NLT or NET translations later)*
  **poppler for Windows**, which provides `pdftotext`. The 13 bundled
  public-domain translations do **not** need it — skip it unless you specifically
  want NLT/NET.

Verify Python and Node are visible to PowerShell:

```powershell
py --version      # should print Python 3.12.x or newer
node --version    # should print v20.x or newer
```

If `py` isn't recognized, reinstall Python with "Add to PATH" checked, then open a
fresh PowerShell window.

---

## Step 1: Set up the backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**If activation is blocked** with a message about "running scripts is disabled on
this system," allow it for your user account once and try again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Your prompt should now start with `(.venv)`. Install the dependencies and create
the database:

```powershell
pip install -r requirements.txt
alembic upgrade head
```

> 💡 The password-hashing library (`argon2-cffi`) ships ready-built wheels for
> modern Python on Windows, so `pip install` should *not* need a C compiler. If it
> tries to compile and fails, you're likely on an older Python — install 3.12+.

---

## Step 2: Load the bundled Bibles

The Docker path loads all 13 translations automatically; here you parse and load
each one yourself. soap-journal needs a temporary folder for the intermediate
files — PowerShell exposes it as `$env:TEMP`.

Start with BSB (a tab-separated text file):

```powershell
python -m soap_journal.parsers.bsb ..\bible-sources\bsb\bsb.txt --out "$env:TEMP\bsb.json"
python -m soap_journal.cli load-translation "$env:TEMP\bsb.json"
```

Then the 12 PDF-based public-domain translations (or any subset you want):

```powershell
foreach ($code in "kjv","akjv","asv","cpdv","dbt","drb","erv","jps","slt","wbt","web","ylt") {
    python -m soap_journal.parsers.$code "..\bible-sources\$code\$code.pdf" --out "$env:TEMP\$code.json"
    python -m soap_journal.cli load-translation "$env:TEMP\$code.json"
}
```

This takes a few minutes. Each translation prints its book/chapter/verse counts as
it loads.

---

## Step 3: Build the frontend

In a **new** PowerShell window (leave the backend one alone), from the
soap-journal folder:

```powershell
cd frontend
npm ci
npm run build
```

This produces the `frontend\dist` folder that the backend will serve.

---

## Step 4: Run soap-journal

Back in your **backend** PowerShell window (the one with `(.venv)` in the prompt),
point the backend at the built frontend and a local data folder, then start the
server. In PowerShell you set environment variables as separate statements before
the command:

```powershell
$env:FRONTEND_DIST_DIR = "..\frontend\dist"
$env:DATA_DIR = ".\data"
uvicorn soap_journal.main:create_app --factory --host 0.0.0.0 --port 8045
```

**What you should see:** a few startup lines ending with
`Application startup complete` and `Uvicorn running on http://0.0.0.0:8045`.

Leave this window open — closing it stops soap-journal. Open
`http://localhost:8045` in your browser and register the first user, exactly as in
[Step 5 of the Windows guide](windows.md#step-5-open-soap-journal-in-your-browser).

> To change the port, change `--port 8045` to another number. To reach the app
> from other devices, find your PC's IP with `ipconfig` — see
> [the Windows guide](windows.md#using-soap-journal-from-your-phone-or-other-devices).

---

## Why Docker is still recommended

With this manual setup you're responsible for starting the server after every
reboot, keeping Python and Node up to date, and re-running the build after an
update (`git pull`, then repeat Steps 3–4). Docker Desktop handles all of that for
you and restarts soap-journal automatically. If the manual route gives you
trouble, the [Docker guide](windows.md) is the smoother path.
