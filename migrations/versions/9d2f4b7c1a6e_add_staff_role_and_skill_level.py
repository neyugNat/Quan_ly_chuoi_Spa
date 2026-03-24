"""add staff role and skill level

Revision ID: 9d2f4b7c1a6e
Revises: 8f3b5f3d1a2c
Create Date: 2026-03-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9d2f4b7c1a6e"
down_revision = "8f3b5f3d1a2c"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("staffs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("role", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("skill_level", sa.String(length=64), nullable=True))


def downgrade():
    with op.batch_alter_table("staffs", schema=None) as batch_op:
        batch_op.drop_column("skill_level")
        batch_op.drop_column("role")
