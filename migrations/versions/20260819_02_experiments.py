"""Add accounts and experiment history.

Revision ID: 20260819_02
Revises: 20260819_01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260819_02"
down_revision = "20260819_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("login", sa.String(100), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(32), nullable=False, unique=True),
    )
    op.create_table(
        "profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("account_id", sa.String(36), nullable=False, unique=True),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("patronymic", sa.String(100)),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "account_roles",
        sa.Column("account_id", sa.String(36), primary_key=True),
        sa.Column("role_id", sa.String(36), primary_key=True),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "test_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("collection_id", sa.String(36)),
        sa.Column("collection_snapshot", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("time_mode", sa.String(32), nullable=False),
        sa.Column("time_limit_ms", sa.Integer()),
        sa.Column("random_seed", sa.String(100), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"], ondelete="SET NULL"),
    )
    op.create_table(
        "comparison_responses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("presentation_index", sa.Integer(), nullable=False),
        sa.Column("level_index", sa.Integer(), nullable=False),
        sa.Column("is_training", sa.Boolean(), nullable=False),
        sa.Column("left_item_id", sa.String(36), nullable=False),
        sa.Column("right_item_id", sa.String(36), nullable=False),
        sa.Column("left_type_id", sa.String(36), nullable=False),
        sa.Column("right_type_id", sa.String(36), nullable=False),
        sa.Column("selected_item_id", sa.String(36)),
        sa.Column("selected_type_id", sa.String(36)),
        sa.Column("reaction_time_ms", sa.Float()),
        sa.Column("exceeded_time_limit", sa.Boolean(), nullable=False),
        sa.Column("timed_out", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("shown_at", sa.DateTime(timezone=True)),
        sa.Column("answered_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["session_id"], ["test_sessions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_id", "presentation_index", name="uq_session_order"),
    )
    op.create_table(
        "analysis_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("analysis_mode", sa.String(32), nullable=False),
        sa.Column("algorithm_version", sa.String(100), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["test_sessions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_id", "analysis_mode", name="uq_session_analysis_mode"),
    )


def downgrade() -> None:
    op.drop_table("analysis_results")
    op.drop_table("comparison_responses")
    op.drop_table("test_sessions")
    op.drop_table("account_roles")
    op.drop_table("profiles")
    op.drop_table("roles")
    op.drop_table("accounts")
