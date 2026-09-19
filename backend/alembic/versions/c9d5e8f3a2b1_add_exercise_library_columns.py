"""exercise_library_items genisletme: difficulty, force_type, mechanic, goals, tags, met, body_part, description, image_*, is_bodyweight, source

Revision ID: c9d5e8f3a2b1
Revises: b8c4f7a2e1d9
Create Date: 2026-09-11

Faz 5 -> değil, Faz 6 (genis veri katmani): 0000.parquet egzersiz kutuphanesi
import'una hazirlik. Bu kolonlar egzersiz sectici (exercise_selector) ve split
planner icin gerekli filtreleme/rankleme alanlaridir. Colon ekleme idempotent:
kolon zaten varsa (create_all ile olusmus SQLite) atlar.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c9d5e8f3a2b1'
down_revision: Union[str, Sequence[str], None] = 'b8c4f7a2e1d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_COLUMNS = [
    ("difficulty", sa.String()),
    ("force_type", sa.String()),
    ("mechanic", sa.String()),
    ("goals", sa.String()),
    ("tags", sa.String()),
    ("met", sa.Float()),
    ("body_part", sa.String()),
    ("description", sa.Text()),
    ("image_start", sa.String()),
    ("image_peak", sa.String()),
    ("image_main", sa.String()),
    ("is_bodyweight", sa.Boolean()),
    ("source", sa.String()),
]

NEW_INDEXES = [
    ("ix_exercise_library_items_difficulty", ["difficulty"]),
    ("ix_exercise_library_items_body_part", ["body_part"]),
    ("ix_exercise_library_items_source", ["source"]),
]


def _existing_columns(conn, table: str) -> set:
    inspector = sa.inspect(conn)
    cols = inspector.get_columns(table)
    return {c["name"] for c in cols}


def upgrade() -> None:
    conn = op.get_bind()
    # SQLite "alter table add column" destekler; kolon zaten varsa atla
    if "exercise_library_items" not in {t for t in sa.inspect(conn).get_table_names()}:
        return
    existing = _existing_columns(conn, "exercise_library_items")
    for col_name, col_type in NEW_COLUMNS:
        if col_name in existing:
            continue
        op.add_column("exercise_library_items", sa.Column(col_name, col_type, nullable=True))
    for index_name, index_cols in NEW_INDEXES:
        try:
            op.create_index(op.f(index_name), "exercise_library_items", index_cols)
        except Exception:
            pass  # index zaten varsa sessizce atla


def downgrade() -> None:
    conn = op.get_bind()
    if "exercise_library_items" not in {t for t in sa.inspect(conn).get_table_names()}:
        return
    existing = _existing_columns(conn, "exercise_library_items")
    for col_name, _ in NEW_COLUMNS:
        if col_name in existing:
            try:
                op.drop_column("exercise_library_items", col_name)
            except Exception:
                pass
    for index_name, _ in NEW_INDEXES:
        try:
            op.drop_index(op.f(index_name), table_name="exercise_library_items")
        except Exception:
            pass