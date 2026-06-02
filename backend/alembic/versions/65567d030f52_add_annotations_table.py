"""add annotations table

Greenfield user-scoped highlights table. Anchored by canonical coords +
translation_code with NO foreign key to verses/translations (the loader
replace-loads translations, churning those ids) — only user_id is a real FK.
See docs/adr/0005-annotation-highlight-layer.md.

Note: autogenerate also reports the FTS5 virtual tables (verses_fts/notes_fts and
their shadow tables) as "removed" because they live on Base.metadata via a DDL
hook rather than as ORM Table objects. Those spurious drops were stripped — this
migration only adds the annotations table.

Revision ID: 65567d030f52
Revises: f8a8ac47739e
Create Date: 2026-06-02 15:52:24.836941

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '65567d030f52'
down_revision: Union[str, Sequence[str], None] = 'f8a8ac47739e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'annotations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('translation_code', sa.String(length=16), nullable=False),
        sa.Column('book', sa.String(), nullable=False),
        sa.Column('chapter', sa.Integer(), nullable=False),
        sa.Column('verse_start', sa.Integer(), nullable=False),
        sa.Column('verse_end', sa.Integer(), nullable=False),
        sa.Column('char_start', sa.Integer(), nullable=False),
        sa.Column('char_end', sa.Integer(), nullable=False),
        sa.Column('color', sa.String(), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "color IN ('yellow', 'green', 'blue', 'pink', 'orange', 'purple')",
            name='ck_annotations_color',
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_annotations_user_id'), 'annotations', ['user_id'], unique=False)
    op.create_index(
        'ix_annotations_user_lookup',
        'annotations',
        ['user_id', 'translation_code', 'book', 'chapter'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_annotations_user_lookup', table_name='annotations')
    op.drop_index(op.f('ix_annotations_user_id'), table_name='annotations')
    op.drop_table('annotations')
