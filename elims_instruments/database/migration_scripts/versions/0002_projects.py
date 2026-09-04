"""Add characterization projects."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the projects table."""
    op.create_table(
        "projects",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_projects_name"), "projects", ["name"], unique=True)
    op.create_table(
        "project_supported_duts",
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("dut_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["dut_id"], ["duts.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("project_id", "dut_id"),
    )
    op.create_table(
        "project_supported_boards",
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("board_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["board_id"], ["boards.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("project_id", "board_id"),
    )


def downgrade() -> None:
    """Remove the projects table."""
    op.drop_table("project_supported_boards")
    op.drop_table("project_supported_duts")
    op.drop_index(op.f("ix_projects_name"), table_name="projects")
    op.drop_table("projects")
