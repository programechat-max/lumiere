"""Add explicit scope for exercise evidence references."""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "i8d0e2f4a6b7"
down_revision: Union[str, Sequence[str], None] = "h7c9d1e3f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if "exercise_library_items" not in sa.inspect(conn).get_table_names():
        return
    cols = {c["name"] for c in sa.inspect(conn).get_columns("exercise_library_items")}
    if "evidence_scope" not in cols:
        op.add_column(
            "exercise_library_items",
            sa.Column("evidence_scope", sa.String(), nullable=True, server_default="unverified"),
        )


def downgrade() -> None:
    if "exercise_library_items" in sa.inspect(op.get_bind()).get_table_names():
        try:
            op.drop_column("exercise_library_items", "evidence_scope")
        except Exception:
            pass
