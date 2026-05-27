# 9. Backups and updates

This is the last chapter. It is also the most important. **Your
journal is irreplaceable. Back it up.**

soap-journal makes backups trivial because everything important lives
in one folder on your host. There's no database server, no scattered
config, no external services. Copy the folder, you've copied your
journal.

## What lives in `./data`

The `data/` folder in the project root (which Docker bind-mounts to
`/data` inside the container) holds:

- `soap_journal.db` — the SQLite database. Every user account, every
  entry, every tag, every loaded Bible translation lives here.
- `.secret_key` — a 64-character random string the server uses to sign
  login cookies. If this changes, everyone gets logged out. Treat it
  like a password — don't commit it to git, don't share it.

Future versions may add other files (image uploads, attachments) here.
Whatever lives in `./data` is what you need to back up.

**Nothing else matters for backup.** Your `.env` is just configuration
(re-create it from `.env.example` if you lose it). The container image
can be rebuilt at any time with `docker compose build`. The source
code is on GitHub.

## Manual backup

The simplest backup is a copy.

### Stop the container first

It is **safest** to stop soap-journal before copying its database,
because SQLite writes to the file in chunks and you don't want to copy
mid-write:

```bash
docker compose down
```

### Copy the folder

```bash
cp -r data data-backup-2026-05-27
```

Date-stamp the backup name so you can tell them apart.

For an off-host backup (e.g. to a USB drive mounted at
`/mnt/backup`):

```bash
cp -r data /mnt/backup/soap-journal-2026-05-27
```

For a compressed archive:

```bash
tar -czvf soap-journal-2026-05-27.tar.gz data
```

For an off-machine backup over the network (`rsync` over SSH):

```bash
rsync -av data/ you@backup-host:/path/to/backups/soap-journal-2026-05-27/
```

### Start the container again

```bash
docker compose up -d
```

You're back up.

## Automating backups

A cron job is the easiest way to make backups happen automatically.

`crontab -e` then add:

```cron
# Every night at 3am, archive the data folder
0 3 * * * cd /home/YOU/soap-journal && \
  docker compose stop && \
  tar -czf /mnt/backup/soap-journal-$(date +\%Y-\%m-\%d).tar.gz data && \
  docker compose start
```

Adjust the paths to match your setup. The container is down for the
few seconds the `tar` takes; that's the cost of a consistent backup.

> **Hot backups (without stopping the container) are possible** using
> SQLite's `.backup` command or by running `sqlite3 data/soap_journal.db
> '.dump'`. Those approaches need more care than this guide goes into.
> For a household-scale instance, the cron job above is more than
> enough.

### Pruning old backups

The cron job above never deletes old archives. After a few months
your backup destination will be full. Add a second cron entry to
prune:

```cron
# Weekly, delete backups older than 30 days
0 4 * * 0 find /mnt/backup -name 'soap-journal-*.tar.gz' -mtime +30 -delete
```

Adjust the path and retention period.

## Restoring a backup

If something goes wrong and you need to restore:

```bash
# 1. Stop the container.
docker compose down

# 2. Move the (probably broken) current data out of the way, just in
#    case you change your mind. NEVER delete the existing folder
#    before restoring.
mv data data.broken-2026-05-27

# 3. Restore from the backup.
cp -r /mnt/backup/soap-journal-2026-05-26 data
# or, from a tarball:
# tar -xzvf /mnt/backup/soap-journal-2026-05-26.tar.gz

# 4. Make sure the file ownership matches what the container expects
#    (UID 1000, which is usually your own user).
sudo chown -R 1000:1000 data

# 5. Start the container again.
docker compose up -d
```

The container reads the restored database on boot. Every user is back
where they were when the backup was taken.

## Updating soap-journal to a new version

New versions of soap-journal show up on the project's
[GitHub releases page](https://github.com/kbennett2000/soap-journal/releases)
and in `CHANGELOG.md`.

**Take a backup before updating.** Always. No matter how minor the
release notes claim the update is.

```bash
# 1. Back up first.
docker compose stop
cp -r data data-before-update
docker compose start

# 2. Pull the latest code.
git pull

# 3. Rebuild and restart.
docker compose up -d --build
```

The first time you run `--build` it will be slow (a few minutes) as
Docker builds the new image. Subsequent restarts skip the build.

### What survives an update

Everything in `./data`. The database is migrated automatically on
boot (the entrypoint runs `alembic upgrade head`), so when soap-journal
changes its schema between versions, your existing data is upgraded
in place without you doing anything.

### What does not survive an update

Anything you put **inside** the container manually (e.g. `docker
exec`'d files into `/tmp` or `/app`). Don't do that. The container is
replaced on every rebuild.

`.env` survives because it lives on the host, not in the container.

### Downgrading

If you update and something breaks, the fastest recovery is to restore
the pre-update backup and roll back the code:

```bash
docker compose down
rm -rf data
cp -r data-before-update data
git checkout v0.1.0   # or whatever version you were on before
docker compose up -d --build
```

Forward database migrations are reversible in principle (Alembic
generates down-migrations) but the project hasn't promised
backwards-compatible downgrades. Treat downgrades as "restore from
backup" rather than "run a migration backwards."

## Where to put backups

Some rules of thumb:

- **Same machine ≠ a backup.** If the disk dies, the backup dies
  with it. Copy to a USB drive, a NAS, or another machine.
- **Same room ≠ a backup either.** A fire, a flood, a theft takes
  everything in the room. Periodically rotate a backup to somewhere
  else (a friend's house, a safety deposit box, your office).
- **The cloud is fine as long as you control the keys.** Encrypted
  archives uploaded to S3, Backblaze B2, or rclone-to-anything are
  reasonable. soap-journal is offline-first; uploading a backup is
  *your* choice, not the app's.
- **Test the restore.** Once a year, on a spare machine or a fresh
  Docker setup, actually restore a backup and confirm it works.
  Untested backups don't count.

---

Previous: [Admin tasks](08-admin-tasks.md) · [Back to the index](README.md)
