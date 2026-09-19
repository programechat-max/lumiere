"""Egzersiz kürasyon kararlarının izlenebilirliği."""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "h7c9d1e3f5a6"
down_revision: Union[str, Sequence[str], None] = "g6b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if "exercise_library_items" not in sa.inspect(conn).get_table_names():
        return
    cols = {c["name"] for c in sa.inspect(conn).get_columns("exercise_library_items")}
    for name, column in (
        ("reviewed_by", sa.Column("reviewed_by", sa.String(), nullable=True)),
        ("reviewed_at", sa.Column("reviewed_at", sa.DateTime(), nullable=True)),
        ("review_note", sa.Column("review_note", sa.Text(), nullable=True)),
    ):
        if name not in cols:
            op.add_column("exercise_library_items", column)


def downgrade() -> None:
    if "exercise_library_items" not in sa.inspect(op.get_bind()).get_table_names():
        return
    for name in ("review_note", "reviewed_at", "reviewed_by"):
        try:
            op.drop_column("exercise_library_items", name)
        except Exception:
            pass
