"""v3.2 Multi-User Auth, BYOK Credentials & AI Model Manager schema

Revision ID: 0002_v32_multiuser
Revises: 0001_initial
Create Date: 2026-11-12
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from app.database.session import Base
import app.database.models  # noqa: F401

revision: str = "0002_v32_multiuser"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_column_if_missing(inspector, table_name: str, column: sa.Column) -> None:
    cols = {c["name"] for c in inspector.get_columns(table_name)}
    if column.name not in cols:
        op.add_column(table_name, column)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. Create new v3.2 tables
    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            table.create(bind=bind, checkfirst=True)

    # 2. Evolve existing tables safely
    if "users" in existing_tables:
        _add_column_if_missing(inspector, "users", sa.Column("full_name", sa.String(128), server_default="Usuário", nullable=False))
        _add_column_if_missing(inspector, "users", sa.Column("must_change_password", sa.Boolean(), server_default=sa.false(), nullable=False))
        _add_column_if_missing(inspector, "users", sa.Column("terms_accepted", sa.Boolean(), server_default=sa.true(), nullable=False))
        _add_column_if_missing(inspector, "users", sa.Column("failed_login_attempts", sa.Integer(), server_default="0", nullable=False))
        _add_column_if_missing(inspector, "users", sa.Column("locked_until", sa.DateTime(), nullable=True))
        _add_column_if_missing(inspector, "users", sa.Column("last_login_at", sa.DateTime(), nullable=True))

    for tbl in ("projects", "workflows", "tasks", "artifacts", "approvals", "events", "chat_messages", "agent_memories"):
        if tbl in existing_tables:
            _add_column_if_missing(inspector, tbl, sa.Column("user_id", sa.String(64), nullable=True))


def downgrade() -> None:
    for tbl in (
        "ai_usage_records",
        "task_model_configs",
        "agent_model_configs",
        "user_ai_preferences",
        "ai_provider_sync_logs",
        "ai_models",
        "ai_provider_credentials",
        "security_audit_logs",
        "invite_codes",
        "password_reset_tokens",
        "user_sessions",
    ):
        op.drop_table(tbl)

