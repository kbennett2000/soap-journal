# Configuration

soap-journal reads all of its settings from a file named `.env` in the project
folder. You create it by copying the included example:

```bash
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env
```

**For a normal install you don't need to change anything** — the defaults work
out of the box. The install guide for your platform
([Windows](install/windows.md), [Mac](install/macos.md),
[Linux server](install/ubuntu-server.md)) walks you through this. The settings
below are here for when you want to change something specific.

## Settings

| Variable     | Default     | What it does                                                       |
| ------------ | ----------- | ------------------------------------------------------------------ |
| `PORT`       | `8045`      | The port you open in your browser (`http://localhost:8045`). Change it if something else already uses `8045`. |
| `SECRET_KEY` | (generated) | Signs your login cookie. Leave blank — soap-journal generates one on first start and remembers it. |
| `DATA_DIR`   | `/data`     | *(Advanced)* Where the database and Bible text live inside the container. Leave it alone; to move your data, change the volume mount in `docker-compose.yml` instead. |
| `BIND_HOST`  | `0.0.0.0`   | *(Advanced)* The address the server listens on inside the container. `0.0.0.0` is required for other devices on your network to reach it. You rarely need to change this. |

## About `SECRET_KEY`

Leave `SECRET_KEY` blank in `.env`. On first start, soap-journal generates a
random key and writes it to a file named `.secret_key` inside your data folder,
then reuses it on every later start. Keep that file private and include it in
your backups (it's part of the `data` folder, so a normal folder backup already
covers it). If the key changes, everyone is simply logged out and signs in
again — no data is lost.

## Who can register an account

Self-registration is **closed by default** on a fresh install. The very first
person to register becomes the **administrator**; after that, nobody else can
create an account until the admin turns open registration on.

This is a runtime setting, not an `.env` value — the admin changes it from the
admin screen (see [Admin tasks](usage/08-admin-tasks.md)), which calls
`PUT /api/v1/admin/settings` under the hood. The admin can also create accounts
for other people directly.

## Changing a setting

1. Open `.env` in any text editor.
2. Change the value (for example, `PORT=8055`).
3. Save, then restart soap-journal:

   ```bash
   docker compose up -d
   ```

See also: [Backups & updates](usage/09-backups-and-updates.md) and
[Troubleshooting](install/troubleshooting.md).
