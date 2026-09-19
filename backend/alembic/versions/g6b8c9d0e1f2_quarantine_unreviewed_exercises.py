"""Ham parquet egzersizlerini açıkça inceleme kuyruğuna al."""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "g6b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f5a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if "exercise_library_items" in sa.inspect(conn).get_table_names():
        op.execute(
            "UPDATE exercise_library_items SET pending_review = 1, "
            "evidence_level = 'unverified', "
            "evidence_source = 'parquet_import_unreviewed' "
            "WHERE source = 'parquet_import'"
        )


def downgrade() -> None:
    conn = op.get_bind()
    if "exercise_library_items" in sa.inspect(conn).get_table_names():
        op.execute(
            "UPDATE exercise_library_items SET pending_review = 0, "
            "evidence_source = NULL WHERE source = 'parquet_import'"
        )
