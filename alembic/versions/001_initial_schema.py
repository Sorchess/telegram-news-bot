"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(50), unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), unique=True, nullable=False),
        sa.Column("first_name", sa.String(255)),
        sa.Column("username", sa.String(255)),
        sa.Column("default_source_slug", sa.String(50)),
        sa.Column("headlines_count", sa.Integer(), server_default="5", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "headlines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.String(1000), unique=True, nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_headlines_source_published", "headlines", ["source_id", "published_at"]
    )
    op.create_index("ix_headlines_url", "headlines", ["url"], unique=True)

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_subscriptions_user_source",
        "subscriptions",
        ["user_id", "source_id"],
        unique=True,
    )

    op.create_table(
        "delivery_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "headline_id",
            sa.Integer(),
            sa.ForeignKey("headlines.id"),
            nullable=False,
        ),
        sa.Column(
            "delivered_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_delivery_user_headline",
        "delivery_log",
        ["user_id", "headline_id"],
        unique=True,
    )

    op.create_table(
        "user_actions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("detail", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("user_actions")
    op.drop_table("delivery_log")
    op.drop_table("subscriptions")
    op.drop_table("headlines")
    op.drop_table("users")
    op.drop_table("sources")
