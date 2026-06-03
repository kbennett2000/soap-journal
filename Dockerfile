# syntax=docker/dockerfile:1.7

# ---------------------------------------------------------------------------
# Stage 1: build the frontend bundle.
# Node 20 is the current LTS (supported through April 2026). Alpine keeps the
# build-stage image small; the artifact (frontend/dist) is what ships, not
# this stage.
# ---------------------------------------------------------------------------
FROM node:20-alpine AS frontend-build
WORKDIR /build

# Install deps from the lockfile first so this layer caches independently of
# the rest of the source tree.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build
# Output: /build/dist


# ---------------------------------------------------------------------------
# Stage 2: backend runtime.
# Python 3.12-slim is the smallest official image that still has glibc, which
# argon2-cffi's wheels need.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# gosu lets the entrypoint start as root (just long enough to fix bind-mount
# ownership on /data) and then drop to the unprivileged soap user before
# exec'ing uvicorn.
# poppler-utils provides pdftotext, which the NLT parser needs to extract
# its two-column PDF. The other parsers use pypdf (a Python dep).
RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Non-root user. UID 1000 matches the default Ubuntu host UID so the
# bind-mounted ./data directory winds up owned by the host user, which makes
# host-side backups, restores, and chmod adjustments straightforward.
RUN useradd --create-home --uid 1000 --shell /bin/bash soap

WORKDIR /app

# Python deps land in their own layer; rebuilds skip this when requirements
# don't change.
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

# Backend source. The .dockerignore strips tests and caches.
COPY backend/ ./

# Built frontend bundle from stage 1.
COPY --from=frontend-build /build/dist ./frontend-dist

# Bundled Bible sources (BSB text + 12 public-domain PDFMaker translations) —
# the entrypoint parses these on first boot.
COPY bible-sources/ ./bible-sources/

# Entrypoint. The sed strips any stray carriage returns (CRLF) so a checkout
# made on Windows — where git may rewrite line endings — still boots; the
# script's bash shebang fails cryptically if it carries CRLF. It's a no-op on a
# normal LF checkout, and a belt-and-suspenders companion to .gitattributes.
COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh \
    && chmod +x /usr/local/bin/docker-entrypoint.sh

# Data directory (the docker-compose volume mount lands on top of this).
RUN mkdir -p /data && chown soap:soap /data

ENV DATA_DIR=/data \
    FRONTEND_DIST_DIR=/app/frontend-dist \
    PORT=8080 \
    BIND_HOST=0.0.0.0

# The entrypoint starts as root so it can chown a freshly bind-mounted
# /data, then gosu's into `soap` before exec'ing uvicorn. The server itself
# never runs as root.
EXPOSE 8080

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["uvicorn", "soap_journal.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]
