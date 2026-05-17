"""add college source metadata

Revision ID: 202605170001
Revises: 202605150001
Create Date: 2026-05-17 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202605170001"
down_revision: str | None = "202605150001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("colleges", sa.Column("city", sa.String(length=100), nullable=True))
    op.add_column("colleges", sa.Column("public_private", sa.String(length=50), nullable=True))
    op.add_column("colleges", sa.Column("roster_vendor", sa.String(length=50), nullable=True))
    op.add_column(
        "colleges",
        sa.Column("is_sidearm", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "colleges",
        sa.Column("import_enabled", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column("colleges", sa.Column("source_notes", sa.Text(), nullable=True))

    op.create_index(op.f("ix_colleges_roster_vendor"), "colleges", ["roster_vendor"], unique=False)
    op.create_index(
        op.f("ix_colleges_import_enabled"), "colleges", ["import_enabled"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_colleges_import_enabled"), table_name="colleges")
    op.drop_index(op.f("ix_colleges_roster_vendor"), table_name="colleges")

    op.drop_column("colleges", "source_notes")
    op.drop_column("colleges", "import_enabled")
    op.drop_column("colleges", "is_sidearm")
    op.drop_column("colleges", "roster_vendor")
    op.drop_column("colleges", "public_private")
    op.drop_column("colleges", "city")
