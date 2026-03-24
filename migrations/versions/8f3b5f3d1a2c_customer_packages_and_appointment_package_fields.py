# pyright: reportUnusedCallResult=false

from alembic import op
import sqlalchemy as sa


revision = "8f3b5f3d1a2c"
down_revision = "0054278f51bd"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "customer_packages",
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("package_id", sa.Integer(), nullable=False),
        sa.Column("sessions_total", sa.Integer(), nullable=False),
        sa.Column("sessions_remaining", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
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
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["package_id"], ["packages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("customer_packages", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_customer_packages_branch_id"), ["branch_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_customer_packages_customer_id"), ["customer_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_customer_packages_expires_at"), ["expires_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_customer_packages_package_id"), ["package_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_customer_packages_status"), ["status"], unique=False)

    with op.batch_alter_table("appointments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("customer_package_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("sessions_used", sa.Integer(), nullable=False, server_default=sa.text("1"))
        )
        batch_op.create_index(
            batch_op.f("ix_appointments_customer_package_id"), ["customer_package_id"], unique=False
        )
        batch_op.create_foreign_key(
            "fk_appointments_customer_package_id_customer_packages",
            "customer_packages",
            ["customer_package_id"],
            ["id"],
        )


def downgrade():
    with op.batch_alter_table("appointments", schema=None) as batch_op:
        batch_op.drop_constraint("fk_appointments_customer_package_id_customer_packages", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_appointments_customer_package_id"))
        batch_op.drop_column("sessions_used")
        batch_op.drop_column("customer_package_id")

    with op.batch_alter_table("customer_packages", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_customer_packages_status"))
        batch_op.drop_index(batch_op.f("ix_customer_packages_package_id"))
        batch_op.drop_index(batch_op.f("ix_customer_packages_expires_at"))
        batch_op.drop_index(batch_op.f("ix_customer_packages_customer_id"))
        batch_op.drop_index(batch_op.f("ix_customer_packages_branch_id"))

    op.drop_table("customer_packages")
