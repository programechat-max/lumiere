"""Egzersiz kanıt kalitesi metadata'sı."""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "e4f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d7e1f5a3c2b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    cols = {c["name"] for c in sa.inspect(conn).get_columns("exercise_library_items")}
    if "evidence_level" not in cols:
        op.add_column("exercise_library_items", sa.Column("evidence_level", sa.String(), nullable=True))
    if "evidence_source" not in cols:
        op.add_column("exercise_library_items", sa.Column("evidence_source", sa.String(), nullable=True))
    try:
        op.create_index("ix_exercise_library_items_evidence_level", "exercise_library_items", ["evidence_level"])
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_index("ix_exercise_library_items_evidence_level", table_name="exercise_library_items")
    except Exception:
        pass
    for name in ("evidence_source", "evidence_level"):
        try:
            op.drop_column("exercise_library_items", name)
        except Exception:
            pass
