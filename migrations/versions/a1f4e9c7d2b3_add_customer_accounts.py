"""add customer_accounts

Revision ID: a1f4e9c7d2b3
Revises: 9d2f4b7c1a6e, f3a2b88f1e11
Create Date: 2026-03-31 19:10:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1f4e9c7d2b3"
down_revision = ("9d2f4b7c1a6e", "f3a2b88f1e11")
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "customer_accounts",
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("reset_password_token", sa.String(length=255), nullable=True),
        sa.Column("reset_password_expires_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("customer_accounts", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_customer_accounts_customer_id"),
            ["customer_id"],
            unique=True,
        )
        batch_op.create_index(
            batch_op.f("ix_customer_accounts_email"),
            ["email"],
            unique=True,
        )
        batch_op.create_index(
            batch_op.f("ix_customer_accounts_reset_password_token"),
            ["reset_password_token"],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table("customer_accounts", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_customer_accounts_reset_password_token"))
        batch_op.drop_index(batch_op.f("ix_customer_accounts_email"))
        batch_op.drop_index(batch_op.f("ix_customer_accounts_customer_id"))

    op.drop_table("customer_accounts")
