"""add fts5 search tables

Creates the standalone FTS5 virtual tables `verses_fts` and `notes_fts` and
backfills them from the existing verses/footnotes rows, so search works
immediately on databases that already have translations loaded (the 13 bundled
translations predate these tables). The CREATE/DROP/backfill SQL is imported
from soap_journal.db.fts so the migrated DB and the create_all-built test DB get
identical table definitions. See docs/adr/0003-full-text-search.md.

Revision ID: f8a8ac47739e
Revises: 4708ebfdc41a
Create Date: 2026-06-02 14:13:42.988251

"""
from typing import Sequence, Union

from alembic import op

from soap_journal.db.fts import (
    BACKFILL_NOTES_FTS,
    BACKFILL_VERSES_FTS,
    NOTES_FTS_CREATE,
    NOTES_FTS_DROP,
    VERSES_FTS_CREATE,
    VERSES_FTS_DROP,
)

# revision identifiers, used by Alembic.
revision: str = 'f8a8ac47739e'
down_revision: Union[str, Sequence[str], None] = '4708ebfdc41a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(VERSES_FTS_CREATE)
    op.execute(NOTES_FTS_CREATE)
    # Backfill existing rows so already-loaded translations are searchable
    # without a manual reload.
    op.execute(BACKFILL_VERSES_FTS)
    op.execute(BACKFILL_NOTES_FTS)


def downgrade() -> None:
    op.execute(NOTES_FTS_DROP)
    op.execute(VERSES_FTS_DROP)
