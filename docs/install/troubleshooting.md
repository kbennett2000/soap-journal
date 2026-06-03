# Install troubleshooting

Common problems people hit when installing soap-journal, with the exact
commands to diagnose and fix each one.

If your problem isn't here, open an issue with as much detail as you
can: <https://github.com/kbennett2000/soap-journal/issues>.

> **A note on the commands below.** The diagnostic commands in this guide
> are written for a Linux server. They work the same inside Docker on
> Windows and Mac, but a few host-side commands differ — those are called
> out in the **Windows & Mac** section just below. The Windows and Mac
> install guides ([Windows](windows.md), [Mac](macos.md)) point you here
> when something goes wrong.

---

## Windows & Mac (Docker Desktop)

These cover the issues specific to running soap-journal with Docker
Desktop on a personal computer. (The rest of this page assumes a Linux
server, but the `docker compose ...` commands are identical everywhere.)

### "docker: command not found" or "the term 'docker' is not recognized"

Docker Desktop isn't running, or your terminal was open before it
finished starting.

1. Open **Docker Desktop** (Start menu on Windows, Applications on Mac).
2. Wait for the **whale icon** (system tray on Windows, menu bar on Mac)
   to stop animating and sit still — that means the engine is ready.
3. Close your terminal and open a fresh one, then try again.

soap-journal only runs while Docker Desktop is running. By default Docker
Desktop starts when you log in; if you've turned that off, you'll need to
open it before starting soap-journal.

### "Cannot connect to the Docker daemon" / "The system cannot find the file specified"

Same cause as above — the Docker engine isn't up yet. Start Docker
Desktop, wait for the whale to settle, and re-run `docker compose up -d`.

### Other devices on my network can't reach soap-journal (Windows)

`http://localhost:8045` works on the PC itself, but your phone or another
computer can't open `http://<pc-ip>:8045`.

1. **Use the right address.** On the PC, run `ipconfig` in PowerShell and
   use the **IPv4 Address** under your active Wi-Fi/Ethernet adapter (e.g.
   `192.168.1.50`). `localhost` and `127.0.0.1` only work on the PC itself.
2. **Allow it through the Windows firewall.** The first time soap-journal
   started, Windows may have shown a **Windows Defender Firewall** prompt;
   if you dismissed it (or clicked Cancel), other devices are blocked. The
   simplest fix is to start fresh so the prompt reappears: run
   `docker compose down` then `docker compose up -d`, and click **Allow
   access** when the prompt shows. Make sure **Private networks** is
   checked.
3. **Confirm both devices are on the same network.** A phone on cellular
   data, or on a "Guest" Wi-Fi network, can't reach your PC. Put both on
   the same home Wi-Fi.

### Other devices on my network can't reach soap-journal (Mac)

1. **Use the right address.** On the Mac, run `ipconfig getifaddr en0` in
   Terminal (or check **System Settings → Wi-Fi → Details… → IP Address**)
   and use that, e.g. `192.168.1.50`. `localhost` only works on the Mac
   itself.
2. **Check the macOS firewall.** Open **System Settings → Network →
   Firewall**. If it's on, either turn it off on your trusted home network,
   or make sure incoming connections to Docker aren't blocked.
3. **Same network?** Make sure the other device is on the same home Wi-Fi,
   not cellular data or a guest network.

### Port 8045 is already in use (Windows / Mac)

You saw `Bind for 0.0.0.0:8045 failed: port is already allocated`.

The easy fix is the same on every platform: open `.env`, change
`PORT=8045` to an unused number like `PORT=8055`, save, and run
`docker compose up -d` again. Then open `http://localhost:8055`.

To find what's already using the port first:

- **Windows (PowerShell):** `Get-Process -Id (Get-NetTCPConnection -LocalPort 8045).OwningProcess`
- **Mac (Terminal):** `lsof -i :8045`

### Where do I run these commands?

In the terminal, **inside the soap-journal folder** — the one containing
`docker-compose.yml`. On Windows that's **PowerShell**; on Mac it's
**Terminal**. If `docker compose` reports it can't find a compose file,
you're in the wrong folder — `cd` into the soap-journal folder first.

---

## I can't reach the server from my browser

You followed the install guide and `docker compose ps` says the container
is `(healthy)`, but `http://<your-server-ip>:8045` doesn't load.

Check each of these in order:

### 1. Is the container actually running?

```bash
docker compose ps
```

If the STATUS column doesn't say `(healthy)`, the container isn't ready
yet. Wait 30 seconds and try again. If it still isn't healthy, look at
the logs:

```bash
docker compose logs --tail=50
```

### 2. Are you using the right IP address?

On the server, run:

```bash
hostname -I
```

Use the **first** IP it prints. Common mistakes:

- Using `127.0.0.1` or `localhost` in your browser. Those only work on
  the server itself, not from another device on your network.
- Using `0.0.0.0`. That's a "bind to everything" address, not a real
  destination. Use the actual LAN IP.
- Using your public IP (from <https://whatismyipaddress.com/>). That's
  the router's external address; it won't reach the server unless you
  intentionally set up port forwarding (don't do this without HTTPS —
  see "Can I access this from outside my network" below).

### 3. Is a firewall blocking the port?

Ubuntu Server doesn't enable the firewall by default, but some
distributions or hardened images do. Check:

```bash
sudo ufw status
```

If it says `Status: inactive`, the firewall isn't the problem.

If it says `Status: active` and port 8045 (or whatever you set `PORT`
to) isn't in the allowed list, open it:

```bash
sudo ufw allow 8045/tcp
```

Verify with `sudo ufw status` again.

### 4. Is the server reachable at all?

From another machine on your network:

```bash
ping <your-server-ip>
```

You should see replies every second. Press Ctrl + C to stop. If you
get no replies, the server isn't on the network you think it's on — fix
that first.

---

## Port 8045 is already in use

When you ran `docker compose up -d` you saw an error like:

```
Bind for 0.0.0.0:8045 failed: port is already allocated
```

That means another process on your server is already using port 8045.

### Pick a different port

Open `.env`:

```bash
nano .env
```

Change `PORT=8045` to any unused port — let's say `8055`. Save (Ctrl +
O, Enter, Ctrl + X) and restart:

```bash
docker compose up -d
```

Then open `http://<your-server-ip>:8055` in your browser.

### Or find what's using 8045

If you want to know what's using the port first:

```bash
sudo lsof -i :8045
```

The output will name the process. If it's something you don't need,
stop it (`sudo systemctl stop <service>`).

---

## docker compose up fails with "permission denied"

You ran `docker compose up -d` and saw something like:

```
permission denied while trying to connect to the Docker daemon socket
at unix:///var/run/docker.sock
```

This means your user account isn't in the `docker` group yet, so it
can't talk to the Docker daemon.

### Fix

```bash
sudo usermod -aG docker $USER
```

Then **fully log out and log back in** (close your SSH session and
reconnect, or reboot if you're using a direct keyboard). The group
change doesn't apply until your shell starts fresh.

Verify with:

```bash
groups
```

You should see `docker` in the list. Then re-run `docker compose up -d`.

---

## I forgot the admin password

There's no self-service password reset in v0.1. Your recovery options
depend on whether there are other admin accounts:

### If you have another admin account

Log in as that admin, go to **Admin → Users**, click **Reset password**
next to your account, and set a new one.

### If you're the only admin (the typical case)

Two options, from least to most destructive:

**Option A — Reset the password directly in the database.** This needs
a little command-line work but preserves all your journal entries.

```bash
docker compose exec soap-journal python -c "
import asyncio
from sqlalchemy import select
from soap_journal.core.passwords import hash_password
from soap_journal.db.session import async_session_factory
from soap_journal.db.models.user import User

USERNAME = 'YOUR_USERNAME_HERE'
NEW_PASSWORD = 'YOUR_NEW_PASSWORD_HERE'

async def reset():
    async with async_session_factory() as db:
        u = (await db.execute(select(User).where(User.username == USERNAME))).scalar_one()
        u.password_hash = hash_password(NEW_PASSWORD)
        await db.commit()
        print(f'reset password for {u.username}')

asyncio.run(reset())
"
```

Replace `YOUR_USERNAME_HERE` and `YOUR_NEW_PASSWORD_HERE` with real
values (keep the quotes). Usernames are stored lowercase, so use the
lowercase form. Run the command; you should see `reset password for ...`.

**Option B — start over.** Stop the container, delete the data folder,
and start again. **This deletes every journal entry every user has
ever written.** Only do this if you don't care about losing data.

```bash
docker compose down
rm -rf data
docker compose up -d
```

Then register again. The first user to register becomes admin.

---

## How do I view the logs?

To see recent logs:

```bash
docker compose logs --tail=100
```

To follow logs as they happen:

```bash
docker compose logs -f
```

Press **Ctrl + C** to stop following. That stops the log stream; the
container keeps running.

To see logs from a specific time forward:

```bash
docker compose logs --since=10m
```

---

## How do I stop the service?

```bash
docker compose down
```

This stops the container and removes it (the image and your data are
unaffected). To start again later:

```bash
docker compose up -d
```

To stop without removing the container (slightly faster restart):

```bash
docker compose stop
docker compose start
```

---

## How do I update to a new version?

See [`docs/usage/09-backups-and-updates.md`](../usage/09-backups-and-updates.md).
The short version:

```bash
git pull
docker compose up -d --build
```

---

## The container says "(unhealthy)" or keeps restarting

Look at the logs:

```bash
docker compose logs --tail=80
```

Common causes:

- **`chown: cannot access './data'`**: your `.env` has
  `DATA_DIR=./data` set explicitly. The container expects `/data`
  (which the volume mount maps to `./data` on your host). Remove the
  `DATA_DIR=...` line from `.env` (or comment it out by adding `#` at
  the start) and `docker compose up -d` again.
- **`Permission denied: '/data/soap_journal.db'`**: the bind-mounted
  `./data` directory is owned by a user other than UID 1000. Fix with
  `sudo chown -R 1000:1000 ./data` and restart.
- **Alembic migration errors**: a previous version's database doesn't
  match this version's schema. If you don't have data to lose, the
  fastest fix is `docker compose down && rm -rf data && docker compose
  up -d`.

---

## Can I access this from outside my network?

Short answer: **not safely without more setup.** soap-journal v0.1
ships with HTTP only and a single shared session cookie. Exposing it
to the public internet directly would let anyone on the internet read
your journal entries if they guessed (or stole) the session cookie,
because there's no TLS to encrypt the traffic.

If you really want external access:

1. Set up a reverse proxy with HTTPS (Caddy, nginx + certbot, Traefik,
   Cloudflare Tunnel) in front of the soap-journal container.
2. Make sure your admin password is strong.
3. Consider an additional layer of auth (a VPN, Cloudflare Access,
   Tailscale).

These are out of scope for the v0.1 install guide. If you're not
comfortable setting up HTTPS yourself, keep soap-journal on your LAN
only — that's the supported deployment model.

If you'd like guides for specific reverse-proxy setups, open an issue
and we'll consider adding them.
