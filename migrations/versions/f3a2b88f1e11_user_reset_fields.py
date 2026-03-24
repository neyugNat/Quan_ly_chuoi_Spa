from alembic import op
import sqlalchemy as sa


revision = "f3a2b88f1e11"
down_revision = "c465eb0830d5"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("reset_password_token", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("reset_password_expires_at", sa.DateTime(), nullable=True))
        batch_op.create_index(batch_op.f("ix_users_reset_password_token"), ["reset_password_token"], unique=False)


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_users_reset_password_token"))
        batch_op.drop_column("reset_password_expires_at")
        batch_op.drop_column("reset_password_token")
