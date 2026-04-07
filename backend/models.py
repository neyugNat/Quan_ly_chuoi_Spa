from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import UniqueConstraint, inspect, text

from werkzeug.security import check_password_hash, generate_password_hash

from backend.extensions import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class Branch(db.Model, TimestampMixin):
    __tablename__ = "branches"

    id = db.Column(db.Integer, primary_key=True)
    branch_code = db.Column(db.String(16), nullable=True, unique=True, index=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    address = db.Column(db.String(500), nullable=True)
    phone = db.Column(db.String(32), nullable=True, unique=True)
    manager_name = db.Column(db.String(255), nullable=True)
    manager_staff_id = db.Column(db.Integer, db.ForeignKey("staffs.id"), nullable=True, index=True)
    status = db.Column(db.String(32), nullable=False, default="active")

    manager_staff = db.relationship("Staff", foreign_keys=[manager_staff_id], lazy="joined")


class User(db.Model, TimestampMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(32), nullable=False, default="branch_manager")
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=True, index=True)
    staff_id = db.Column(db.Integer, db.ForeignKey("staffs.id"), nullable=True, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    branch = db.relationship("Branch", lazy="joined")
    staff = db.relationship("Staff", lazy="joined")

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def verify_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_super_admin(self) -> bool:
        return self.role == "super_admin"


class Staff(db.Model, TimestampMixin):
    __tablename__ = "staffs"

    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False, index=True)
    full_name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(32), nullable=True, unique=True, index=True)
    title = db.Column(db.String(64), nullable=True)
    status = db.Column(db.String(32), nullable=False, default="active")
    start_date = db.Column(db.Date, nullable=True)
    note = db.Column(db.String(500), nullable=True)

    branch = db.relationship("Branch", foreign_keys=[branch_id], lazy="joined")


class Service(db.Model, TimestampMixin):
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    group_name = db.Column(db.String(64), nullable=True)
    price = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    duration_minutes = db.Column(db.Integer, nullable=False, default=60)
    status = db.Column(db.String(32), nullable=False, default="active")
    description = db.Column(db.String(500), nullable=True)

    branch = db.relationship("Branch", lazy="joined")


class Appointment(db.Model, TimestampMixin):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False, index=True)
    customer_name = db.Column(db.String(255), nullable=False)
    customer_phone = db.Column(db.String(32), nullable=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False, index=True)
    technician_id = db.Column(db.Integer, db.ForeignKey("staffs.id"), nullable=False, index=True)
    appointment_date = db.Column(db.Date, nullable=False, index=True)
    appointment_time = db.Column(db.String(5), nullable=False)
    status = db.Column(db.String(16), nullable=False, default="pending", index=True)
    note = db.Column(db.String(500), nullable=True)
    created_by = db.Column(db.String(64), nullable=True)

    branch = db.relationship("Branch", lazy="joined")
    service = db.relationship("Service", lazy="joined")
    technician = db.relationship("Staff", lazy="joined")


class InventoryItem(db.Model, TimestampMixin):
    __tablename__ = "inventory_items"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    unit = db.Column(db.String(32), nullable=False, default="hộp")
    group_name = db.Column(db.String(64), nullable=True)
    min_stock = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    status = db.Column(db.String(32), nullable=False, default="active")


class InventoryStock(db.Model, TimestampMixin):
    __tablename__ = "inventory_stocks"
    __table_args__ = (UniqueConstraint("branch_id", "item_id", name="uq_inventory_stock"),)

    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey("inventory_items.id"), nullable=False, index=True)
    quantity = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    branch = db.relationship("Branch", lazy="joined")
    item = db.relationship("InventoryItem", lazy="joined")


class InventoryTransaction(db.Model):
    __tablename__ = "inventory_transactions"

    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey("inventory_items.id"), nullable=False, index=True)
    type = db.Column(db.String(16), nullable=False)
    quantity = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    note = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    branch = db.relationship("Branch", lazy="joined")
    item = db.relationship("InventoryItem", lazy="joined")


class Invoice(db.Model, TimestampMixin):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), nullable=False, unique=True, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False, index=True)
    staff_id = db.Column(db.Integer, db.ForeignKey("staffs.id"), nullable=True, index=True)
    customer_name = db.Column(db.String(255), nullable=True)
    customer_phone = db.Column(db.String(32), nullable=True)
    subtotal_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    discount_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    status = db.Column(db.String(32), nullable=False, default="draft", index=True)
    note = db.Column(db.String(500), nullable=True)
    canceled_reason = db.Column(db.String(500), nullable=True)
    canceled_at = db.Column(db.DateTime, nullable=True)
    last_action_by = db.Column(db.String(64), nullable=True)

    branch = db.relationship("Branch", lazy="joined")
    staff = db.relationship("Staff", lazy="joined")
    items = db.relationship("InvoiceItem", back_populates="invoice", cascade="all,delete-orphan")


class InvoiceItem(db.Model):
    __tablename__ = "invoice_items"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=True, index=True)
    service_name = db.Column(db.String(255), nullable=False)
    qty = db.Column(db.Numeric(12, 2), nullable=False, default=1)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    line_total = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    invoice = db.relationship("Invoice", back_populates="items", lazy="joined")
    service = db.relationship("Service", lazy="joined")


def recalc_invoice(invoice: Invoice) -> None:
    subtotal = Decimal("0.00")
    for item in invoice.items:
        qty = Decimal(str(item.qty or 0))
        unit_price = Decimal(str(item.unit_price or 0))
        item.line_total = (qty * unit_price).quantize(Decimal("0.01"))
        subtotal += Decimal(str(item.line_total or 0))

    discount = Decimal(str(invoice.discount_amount or 0))
    if discount < 0:
        discount = Decimal("0.00")
    total = subtotal - discount
    if total < 0:
        total = Decimal("0.00")

    invoice.subtotal_amount = subtotal
    invoice.total_amount = total
    if invoice.status == "canceled":
        return
    if invoice.status not in {"draft", "paid"}:
        invoice.status = "paid"


def normalize_money_to_thousand(amount: Decimal | int | float | str | None) -> Decimal:
    value = Decimal(str(amount or 0))
    if value <= 0:
        return Decimal("0.00")
    rounded = (value / Decimal("1000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * Decimal("1000")
    return rounded.quantize(Decimal("0.01"))


def migrate_remove_partial_payment_schema() -> None:
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())
    if "invoices" not in table_names:
        return

    invoice_columns = {col["name"] for col in inspector.get_columns("invoices")}

    with db.engine.begin() as conn:
        if "paid_amount" in invoice_columns:
            conn.execute(
                text(
                    """
                    UPDATE invoices
                    SET status = CASE
                        WHEN status = 'canceled' THEN 'canceled'
                        WHEN COALESCE(total_amount, 0) > 0
                             AND COALESCE(paid_amount, 0) >= COALESCE(total_amount, 0) THEN 'paid'
                        ELSE 'draft'
                    END
                    WHERE status != 'canceled'
                    """
                )
            )

        conn.execute(
            text(
                """
                UPDATE invoices
                SET status = 'draft'
                WHERE status IS NULL OR status NOT IN ('draft', 'paid', 'canceled')
                """
            )
        )

        if "balance_amount" in invoice_columns:
            conn.execute(text("ALTER TABLE invoices DROP COLUMN balance_amount"))
        if "paid_amount" in invoice_columns:
            conn.execute(text("ALTER TABLE invoices DROP COLUMN paid_amount"))

        if "invoice_payments" in table_names:
            conn.execute(text("DROP TABLE IF EXISTS invoice_payments"))


def migrate_add_branch_code() -> None:
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())
    if "branches" not in table_names:
        return

    branch_columns = {col["name"] for col in inspector.get_columns("branches")}

    with db.engine.begin() as conn:
        if "branch_code" not in branch_columns:
            conn.execute(text("ALTER TABLE branches ADD COLUMN branch_code VARCHAR(16)"))

        conn.execute(
            text(
                """
                UPDATE branches
                SET branch_code = UPPER(TRIM(COALESCE(branch_code, '')))
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE branches
                SET branch_code = 'CN' || id
                WHERE branch_code = ''
                """
            )
        )

        duplicate_rows = conn.execute(
            text(
                """
                SELECT branch_code
                FROM branches
                WHERE branch_code IS NOT NULL AND branch_code != ''
                GROUP BY branch_code
                HAVING COUNT(*) > 1
                """
            )
        ).fetchall()
        for (dup_code,) in duplicate_rows:
            conn.execute(
                text(
                    """
                    UPDATE branches
                    SET branch_code = 'CN' || id
                    WHERE branch_code = :dup_code
                    """
                ),
                {"dup_code": dup_code},
            )

        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_branches_branch_code ON branches(branch_code)"))


def migrate_add_branch_manager_staff_id() -> None:
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())
    if "branches" not in table_names:
        return

    branch_columns = {col["name"] for col in inspector.get_columns("branches")}
    has_staff_table = "staffs" in table_names

    with db.engine.begin() as conn:
        if "manager_staff_id" not in branch_columns:
            conn.execute(text("ALTER TABLE branches ADD COLUMN manager_staff_id INTEGER"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_branches_manager_staff_id ON branches(manager_staff_id)"))

        if has_staff_table and "manager_name" in branch_columns:
            missing_rows = conn.execute(
                text(
                    """
                    SELECT id, branch_id, manager_name
                    FROM (
                        SELECT b.id,
                               b.id AS branch_id,
                               TRIM(COALESCE(b.manager_name, '')) AS manager_name,
                               COALESCE(b.manager_staff_id, 0) AS manager_staff_id
                        FROM branches b
                    )
                    WHERE manager_name != '' AND manager_staff_id = 0
                    """
                )
            ).fetchall()

            for branch_id, branch_scope_id, manager_name in missing_rows:
                staff_row = conn.execute(
                    text(
                        """
                        SELECT s.id
                        FROM staffs s
                        WHERE s.branch_id = :branch_id
                          AND LOWER(TRIM(s.full_name)) = LOWER(TRIM(:manager_name))
                        ORDER BY CASE WHEN s.status = 'active' THEN 0 ELSE 1 END, s.id ASC
                        LIMIT 1
                        """
                    ),
                    {"branch_id": branch_scope_id, "manager_name": manager_name},
                ).fetchone()
                if staff_row:
                    conn.execute(
                        text("UPDATE branches SET manager_staff_id = :staff_id WHERE id = :branch_id"),
                        {"staff_id": int(staff_row[0]), "branch_id": int(branch_id)},
                    )

        if has_staff_table:
            conn.execute(
                text(
                    """
                    UPDATE branches
                    SET manager_staff_id = NULL
                    WHERE manager_staff_id IS NOT NULL
                      AND manager_staff_id NOT IN (
                          SELECT s.id
                          FROM staffs s
                          WHERE s.branch_id = branches.id
                      )
                    """
                )
            )


def migrate_add_user_staff_id() -> None:
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())
    if "users" not in table_names:
        return

    user_columns = {col["name"] for col in inspector.get_columns("users")}
    with db.engine.begin() as conn:
        if "staff_id" not in user_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN staff_id INTEGER"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_staff_id ON users(staff_id)"))


def migrate_backfill_user_staff_id() -> None:
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())
    if "users" not in table_names or "staffs" not in table_names:
        return

    with db.engine.begin() as conn:
        missing_rows = conn.execute(
            text(
                """
                SELECT id, branch_id
                FROM users
                WHERE role != 'super_admin'
                  AND branch_id IS NOT NULL
                  AND (staff_id IS NULL OR staff_id = 0)
                """
            )
        ).fetchall()

        for user_id, branch_id in missing_rows:
            staff_row = conn.execute(
                text(
                    """
                    SELECT id
                    FROM staffs
                    WHERE branch_id = :branch_id
                      AND status = 'active'
                    ORDER BY id ASC
                    LIMIT 1
                    """
                ),
                {"branch_id": branch_id},
            ).fetchone()
            if staff_row:
                conn.execute(
                    text("UPDATE users SET staff_id = :staff_id WHERE id = :user_id"),
                    {"staff_id": staff_row[0], "user_id": user_id},
                )


def migrate_normalize_service_prices_and_invoices() -> None:
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())
    required_tables = {"services", "invoice_items", "invoices"}
    if not required_tables.issubset(table_names):
        return

    changed = False
    service_price_map: dict[int, Decimal] = {}

    for service in Service.query.order_by(Service.id.asc()).all():
        new_price = normalize_money_to_thousand(service.price)
        current_price = Decimal(str(service.price or 0))
        if current_price != new_price:
            service.price = new_price
            changed = True
        service_price_map[service.id] = Decimal(str(service.price or 0))

    for item in InvoiceItem.query.order_by(InvoiceItem.id.asc()).all():
        if item.service_id and item.service_id in service_price_map:
            new_unit_price = service_price_map[item.service_id]
        else:
            new_unit_price = normalize_money_to_thousand(item.unit_price)

        current_unit_price = Decimal(str(item.unit_price or 0))
        qty = Decimal(str(item.qty or 0))
        new_line_total = (qty * new_unit_price).quantize(Decimal("0.01"))

        if current_unit_price != new_unit_price:
            item.unit_price = new_unit_price
            changed = True
        if Decimal(str(item.line_total or 0)) != new_line_total:
            item.line_total = new_line_total
            changed = True

    for invoice in Invoice.query.order_by(Invoice.id.asc()).all():
        old_subtotal = Decimal(str(invoice.subtotal_amount or 0))
        old_total = Decimal(str(invoice.total_amount or 0))
        recalc_invoice(invoice)
        if old_subtotal != Decimal(str(invoice.subtotal_amount or 0)):
            changed = True
        if old_total != Decimal(str(invoice.total_amount or 0)):
            changed = True

    if changed:
        db.session.commit()


def ensure_seed_data() -> None:
    def upsert_branch(name: str, address: str, phone: str, manager_name: str) -> Branch:
        branch = Branch.query.filter_by(name=name).first()
        if branch is None:
            branch = Branch(name=name)
            db.session.add(branch)
        branch.address = address
        branch.phone = phone
        branch.manager_name = manager_name
        branch.status = "active"
        return branch

    def upsert_user(
        username: str,
        role: str,
        branch_id: int | None,
        password: str,
        staff_id: int | None = None,
    ) -> User:
        user = User.query.filter_by(username=username).first()
        if user is None:
            user = User(username=username)
            db.session.add(user)
        user.role = role
        user.is_active = True
        user.branch_id = branch_id
        user.staff_id = staff_id
        user.set_password(password)
        return user

    b1 = upsert_branch("Chi nhánh 1", "Quận 1, TP.HCM", "02873001001", "Nguyễn Minh")
    b2 = upsert_branch("Chi nhánh 2", "Quận 7, TP.HCM", "02873002002", "Trần An")
    db.session.flush()
    if not b1.branch_code:
        b1.branch_code = f"CN{b1.id}"
    if not b2.branch_code:
        b2.branch_code = f"CN{b2.id}"

    upsert_user("admin", "super_admin", None, "admin123", staff_id=None)

    if Staff.query.count() == 0:
        db.session.add(
            Staff(
                branch_id=b1.id,
                full_name="Nhân viên Demo 1",
                phone="0900000001",
                title="Kỹ thuật viên",
                status="active",
                start_date=date(2024, 1, 10),
            )
        )
        db.session.add(
            Staff(
                branch_id=b2.id,
                full_name="Nhân viên Demo 2",
                phone="0900000002",
                title="Kỹ thuật viên",
                status="active",
                start_date=date(2024, 3, 1),
            )
        )
        db.session.add(
            Staff(
                branch_id=b1.id,
                full_name="Lê Hà",
                phone="0900000003",
                title="Quản lý ca",
                status="active",
                start_date=date(2024, 2, 15),
            )
        )

    if Service.query.count() == 0:
        db.session.add(
            Service(
                branch_id=b1.id,
                name="Chăm sóc da mặt",
                group_name="Da mặt",
                price=Decimal("300000"),
                duration_minutes=60,
                status="active",
                description="Làm sạch và cấp ẩm cơ bản",
            )
        )
        db.session.add(
            Service(
                branch_id=b1.id,
                name="Massage body",
                group_name="Body",
                price=Decimal("450000"),
                duration_minutes=90,
                status="active",
                description="Thư giãn toàn thân",
            )
        )
        db.session.add(
            Service(
                branch_id=b2.id,
                name="Trị liệu cổ vai gáy",
                group_name="Trị liệu",
                price=Decimal("400000"),
                duration_minutes=75,
                status="active",
                description="Giảm đau mỏi vùng cổ vai gáy",
            )
        )
        db.session.add(
            Service(
                branch_id=b2.id,
                name="Gội đầu dưỡng sinh",
                group_name="Body",
                price=Decimal("250000"),
                duration_minutes=45,
                status="active",
                description="Thư giãn da đầu và cổ",
            )
        )

    if InventoryItem.query.count() == 0:
        db.session.add(
            InventoryItem(
                name="Tinh dầu massage",
                unit="chai",
                group_name="Tiêu hao",
                min_stock=Decimal("8"),
                status="active",
            )
        )
        db.session.add(
            InventoryItem(
                name="Kem dưỡng da",
                unit="hộp",
                group_name="Mỹ phẩm",
                min_stock=Decimal("6"),
                status="active",
            )
        )
        db.session.add(
            InventoryItem(
                name="Khăn spa",
                unit="cái",
                group_name="Dụng cụ",
                min_stock=Decimal("20"),
                status="active",
            )
        )
    db.session.flush()

    primary_technician = (
        Staff.query.filter_by(branch_id=b1.id, status="active").order_by(Staff.id.asc()).first()
    )
    if primary_technician is None:
        primary_technician = Staff(
            branch_id=b1.id,
            full_name="KTV Demo CN1",
            phone="0900000011",
            title="Kỹ thuật viên",
            status="active",
            start_date=date(2024, 4, 1),
        )
        db.session.add(primary_technician)
        db.session.flush()

    branch_one_staffs = Staff.query.filter_by(branch_id=b1.id, status="active").order_by(Staff.id.asc()).all()
    if not branch_one_staffs:
        branch_one_staffs = [primary_technician]

    manager_staff = branch_one_staffs[1] if len(branch_one_staffs) > 1 else branch_one_staffs[0]
    reception_staff = branch_one_staffs[0]
    inventory_staff = branch_one_staffs[2] if len(branch_one_staffs) > 2 else branch_one_staffs[0]

    branch_two_manager = Staff.query.filter_by(branch_id=b2.id, status="active").order_by(Staff.id.asc()).first()
    b1.manager_staff_id = manager_staff.id if manager_staff else None
    b1.manager_name = manager_staff.full_name if manager_staff else None
    b2.manager_staff_id = branch_two_manager.id if branch_two_manager else None
    b2.manager_name = branch_two_manager.full_name if branch_two_manager else None

    upsert_user("manager", "branch_manager", b1.id, "manager123", staff_id=manager_staff.id)
    upsert_user("letan1", "receptionist", b1.id, "letan123", staff_id=reception_staff.id)
    upsert_user("kho1", "inventory_controller", b1.id, "kho12345", staff_id=inventory_staff.id)
    upsert_user("ktv1", "technician", b1.id, "ktv12345", staff_id=primary_technician.id)

    if InventoryStock.query.count() == 0:
        item_rows = InventoryItem.query.order_by(InventoryItem.id.asc()).all()
        stock_plan = {
            "Chi nhánh 1": {"Tinh dầu massage": Decimal("12"), "Kem dưỡng da": Decimal("4"), "Khăn spa": Decimal("25")},
            "Chi nhánh 2": {"Tinh dầu massage": Decimal("6"), "Kem dưỡng da": Decimal("10"), "Khăn spa": Decimal("18")},
        }
        branch_rows = {branch.name: branch for branch in Branch.query.order_by(Branch.id.asc()).all()}
        for branch_name, branch_data in stock_plan.items():
            branch = branch_rows.get(branch_name)
            if branch is None:
                continue
            for item in item_rows:
                qty = branch_data.get(item.name, Decimal("0"))
                db.session.add(
                    InventoryStock(
                        branch_id=branch.id,
                        item_id=item.id,
                        quantity=qty,
                    )
                )
                db.session.add(
                    InventoryTransaction(
                        branch_id=branch.id,
                        item_id=item.id,
                        type="adjust",
                        quantity=qty,
                        note="Khởi tạo dữ liệu demo",
                    )
                )
        db.session.flush()

    if Invoice.query.count() == 0:
        staff_b1 = Staff.query.filter_by(branch_id=b1.id, status="active").order_by(Staff.id.asc()).first()
        staff_b2 = Staff.query.filter_by(branch_id=b2.id, status="active").order_by(Staff.id.asc()).first()
        service_b1 = Service.query.filter_by(branch_id=b1.id, status="active").order_by(Service.id.asc()).all()
        service_b2 = Service.query.filter_by(branch_id=b2.id, status="active").order_by(Service.id.asc()).all()

        def seed_invoice(
            *,
            branch: Branch,
            customer_name: str,
            customer_phone: str,
            staff: Staff | None,
            lines: list[tuple[Service, Decimal]],
            discount: Decimal,
            days_ago: int,
            canceled: bool = False,
            status: str = "paid",
            note: str | None = None,
        ) -> None:
            created_at = datetime.utcnow() - timedelta(days=days_ago)
            invoice = Invoice(
                code="TMP",
                branch_id=branch.id,
                customer_name=customer_name,
                customer_phone=customer_phone,
                staff_id=staff.id if staff else None,
                discount_amount=discount,
                status=status if status in {"draft", "paid"} else "paid",
                note=note,
                last_action_by="seed",
                created_at=created_at,
                updated_at=created_at,
            )
            db.session.add(invoice)
            db.session.flush()
            invoice.code = f"HD{invoice.id:06d}"

            for service, qty in lines:
                invoice.items.append(
                    InvoiceItem(
                        service_id=service.id,
                        service_name=service.name,
                        qty=qty,
                        unit_price=service.price,
                    )
                )

            recalc_invoice(invoice)
            if canceled:
                invoice.status = "canceled"
                invoice.canceled_reason = note or "Khách đổi lịch"
                invoice.canceled_at = created_at

        if staff_b1 and staff_b2 and service_b1 and service_b2:
            seed_invoice(
                branch=b1,
                customer_name="Khách lẻ A",
                customer_phone="0901000001",
                staff=staff_b1,
                lines=[(service_b1[0], Decimal("1.00"))],
                discount=Decimal("0.00"),
                days_ago=1,
            )
            seed_invoice(
                branch=b1,
                customer_name="Khách lẻ B",
                customer_phone="0901000002",
                staff=staff_b1,
                lines=[(service_b1[0], Decimal("1.00")), (service_b1[1], Decimal("1.00"))],
                discount=Decimal("50000.00"),
                days_ago=2,
            )
            seed_invoice(
                branch=b1,
                customer_name="Khách walk-in",
                customer_phone="",
                staff=staff_b1,
                lines=[(service_b1[1], Decimal("1.00"))],
                discount=Decimal("0.00"),
                days_ago=10,
                status="draft",
                note="Đặt cọc sau",
            )
            seed_invoice(
                branch=b2,
                customer_name="Khách VIP",
                customer_phone="0902000001",
                staff=staff_b2,
                lines=[(service_b2[0], Decimal("2.00"))],
                discount=Decimal("30000.00"),
                days_ago=12,
            )
            seed_invoice(
                branch=b2,
                customer_name="Khách lẻ C",
                customer_phone="0902000002",
                staff=staff_b2,
                lines=[(service_b2[1], Decimal("1.00"))],
                discount=Decimal("0.00"),
                days_ago=15,
                canceled=True,
                note="Khách đổi lịch",
            )

    if Appointment.query.count() == 0:
        service_b1 = Service.query.filter_by(branch_id=b1.id, status="active").order_by(Service.id.asc()).all()
        service_b2 = Service.query.filter_by(branch_id=b2.id, status="active").order_by(Service.id.asc()).all()
        staff_b1 = Staff.query.filter_by(branch_id=b1.id, status="active").order_by(Staff.id.asc()).all()
        staff_b2 = Staff.query.filter_by(branch_id=b2.id, status="active").order_by(Staff.id.asc()).all()

        if service_b1 and staff_b1:
            db.session.add(
                Appointment(
                    branch_id=b1.id,
                    customer_name="Ngọc Anh",
                    customer_phone="0903111111",
                    service_id=service_b1[0].id,
                    technician_id=staff_b1[0].id,
                    appointment_date=date.today(),
                    appointment_time="09:00",
                    status="pending",
                    note="Khách đặt qua hotline",
                    created_by="letan1",
                )
            )
            db.session.add(
                Appointment(
                    branch_id=b1.id,
                    customer_name="Mai Trinh",
                    customer_phone="0903222222",
                    service_id=service_b1[0].id,
                    technician_id=staff_b1[0].id,
                    appointment_date=date.today() - timedelta(days=1),
                    appointment_time="14:30",
                    status="completed",
                    note="Đã thực hiện",
                    created_by="letan1",
                )
            )

        if service_b2 and staff_b2:
            db.session.add(
                Appointment(
                    branch_id=b2.id,
                    customer_name="Khánh Linh",
                    customer_phone="0903333333",
                    service_id=service_b2[0].id,
                    technician_id=staff_b2[0].id,
                    appointment_date=date.today() + timedelta(days=1),
                    appointment_time="10:15",
                    status="cancelled",
                    note="Khách bận việc",
                    created_by="manager",
                )
            )

    db.session.commit()
