"""add index on entry_scripture_verses(entry_id)

Revision ID: 9196d8cd4c53
Revises: 23850223500e
Create Date: 2026-05-27 02:00:00.000000

The table already has a composite primary key on (entry_id, verse_id),
which on most engines is enough for entry_id lookups. The explicit index
makes the intent visible — retrieval-by-entry_id is now a hot path
because of the new filter joins through entry_scripture_verses — and
keeps lookup performance honest if the PK index implementation ever
shifts.

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "9196d8cd4c53"
down_revision: Union[str, Sequence[str], None] = "23850223500e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        op.f("ix_entry_scripture_verses_entry_id"),
        "entry_scripture_verses",
        ["entry_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_entry_scripture_verses_entry_id"),
        table_name="entry_scripture_verses",
    )
