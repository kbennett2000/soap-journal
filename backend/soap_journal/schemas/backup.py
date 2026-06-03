"""Pydantic models for the journal backup export file (FORMAT version 1).

The interop source of truth is the mobile app's Zod schema at
``soap-journal-mobile/src/lib/schema/backup.ts``. The phone's restore validates
every object with ``.strict()`` and REJECTS any file containing an unknown key,
so these models mirror that contract 1:1 — only the contract keys, nothing else
(no ``id``, ``user_id``, ``display_title``, ...). ``extra="forbid"`` mirrors Zod
``.strict()`` as a guard; the load-bearing interop guarantee is proven by the
key-set test in ``api/backup_test.py``.

Timestamp/date fields are typed as ``str`` (not ``datetime``/``date``): the
contract carries them as JSON strings (``z.string()``), and the builder in
``core/backup.py`` owns the exact formatting (``YYYY-MM-DD`` for dates,
ISO-8601 UTC with a trailing ``Z`` for instants). Typing them as ``str`` keeps
Pydantic from re-serializing and guarantees the trailing ``Z``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class BackupVerse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    book_order_index: int  # 1..66, from books.order_index
    chapter: int  # >= 1, from chapters.number
    verse: int  # >= 1, from verses.number


class BackupEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None
    entry_date: str  # "YYYY-MM-DD"
    scripture_ref: str
    scripture_translation_code: str  # the entry's translation .code (renamed on export)
    scripture_text: str
    observation: str
    application: str
    prayer: str
    created_at: str  # ISO-8601 UTC, trailing Z
    updated_at: str  # ISO-8601 UTC, trailing Z
    verses: list[BackupVerse]
    tags: list[str]  # tag names, original casing, ordered by lower(name)


class BackupDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["soap-journal-backup"] = "soap-journal-backup"
    version: Literal[1] = 1
    exported_at: str  # ISO-8601 UTC, trailing Z
    entries: list[BackupEntry]
