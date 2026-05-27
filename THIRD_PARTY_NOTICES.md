# Third-Party Notices

soap-journal incorporates the following open-source software. All
licenses listed below are compatible with this project's MIT license.

## Backend

| Project        | License      | Project URL                            |
| -------------- | ------------ | -------------------------------------- |
| FastAPI        | MIT          | https://fastapi.tiangolo.com/          |
| Starlette      | BSD-3-Clause | https://www.starlette.io/              |
| Uvicorn        | BSD-3-Clause | https://www.uvicorn.org/               |
| Pydantic       | MIT          | https://docs.pydantic.dev/             |
| SQLAlchemy     | MIT          | https://www.sqlalchemy.org/            |
| Alembic        | MIT          | https://alembic.sqlalchemy.org/        |
| aiosqlite      | MIT          | https://aiosqlite.omnilib.dev/         |
| Passlib        | BSD-2-Clause | https://passlib.readthedocs.io/        |
| argon2-cffi    | MIT          | https://argon2-cffi.readthedocs.io/    |

## Frontend

| Project          | License | Project URL                       |
| ---------------- | ------- | --------------------------------- |
| React            | MIT     | https://react.dev/                |
| React Router     | MIT     | https://reactrouter.com/          |
| TanStack Query   | MIT     | https://tanstack.com/query        |
| Vite             | MIT     | https://vitejs.dev/               |
| Tailwind CSS     | MIT     | https://tailwindcss.com/          |
| TypeScript       | Apache-2.0 | https://www.typescriptlang.org/ |
| Zod              | MIT     | https://zod.dev/                  |

## Bible text

**Berean Standard Bible (BSB)** — dedicated to the public domain. Free
to use and redistribute. Source and full attribution text live in
[`bible-sources/bsb/NOTICE`](bible-sources/bsb/NOTICE); the canonical
home is <https://bereanbible.com/>.

---

This list covers the major direct dependencies. Each package above
brings its own transitive dependency tree; for a complete dependency
report run `pip install -r backend/requirements.txt` and
`npm install` in `frontend/` and inspect `pip list` / `npm ls`.
