from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import UniqueConstraint, inspect, text
from werkzeug.security import check_password_hash, generate_password_hash

from backend.extensions import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


def is_password_hash(value: str | None) -> bool:
    text_value = value or ""
    return text_value.startswith(("scrypt:", "pbkdf2:", "argon2:"))


class Branch(db.Model, TimestampMixin):
    __tablename__ = "branches"

    id = db.Column(db.Integer, primary_key=True)
    branch_code = db.Column(db.String(16), nullable=True, unique=True, index=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    address = db.Column(db.String(500), nullable=True)
    phone = db.Column(db.String(32), nullable=True, unique=True)
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
        self.password_hash = generate_password_hash(raw_password or "")

    def verify_password(self, raw_password: str) -> bool:
        stored_password = self.password_hash or ""
        if is_password_hash(stored_password):
            return check_password_hash(stored_password, raw_password or "")
        return stored_password == (raw_password or "")

    @property
    def password_needs_rehash(self) -> bool:
        return not is_password_hash(self.password_hash)

    @property
    def is_super_admin(self) -> bool:
        return self.role == "super_admin"


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    action = db.Column(db.String(64), nullable=False, index=True)
    action_label = db.Column(db.String(128), nullable=False)

    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=True, index=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    actor_username = db.Column(db.String(64), nullable=True)
    actor_role = db.Column(db.String(32), nullable=True)

    entity_type = db.Column(db.String(64), nullable=True)
    entity_id = db.Column(db.Integer, nullable=True, index=True)
    message = db.Column(db.String(500), nullable=True)
    details_json = db.Column(db.Text, nullable=True)

    branch = db.relationship("Branch", lazy="joined")
    actor_user = db.relationship("User", lazy="joined")


class Customer(db.Model, TimestampMixin):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("branch_id", "phone", name="uq_customer_branch_phone"),)

    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False, index=True)
    full_name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(32), nullable=False, index=True)
    segment = db.Column(db.String(32), nullable=False, default="regular")
    note = db.Column(db.String(500), nullable=True)
    visit_count = db.Column(db.Integer, nullable=False, default=0)
    total_spent = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    last_visit_at = db.Column(db.DateTime, nullable=True)

    branch = db.relationship("Branch", lazy="joined")


class Staff(db.Model, TimestampMixin):
    __tablename__ = "staffs"

    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False, index=True)
    full_name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(32), nullable=True, unique=True, index=True)
    title = db.Column(db.String(64), nullable=True)
    status = db.Column(db.String(32), nullable=False, default="active")
    start_date = db.Column(db.Date, nullable=True)

    branch = db.relationship("Branch", foreign_keys=[branch_id], lazy="joined")


class StaffShift(db.Model):
    __tablename__ = "staff_shifts"
    __table_args__ = (UniqueConstraint("staff_id", "weekday", name="uq_staff_shift_weekday"),)

    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False, index=True)
    staff_id = db.Column(db.Integer, db.ForeignKey("staffs.id"), nullable=False, index=True)
    weekday = db.Column(db.Integer, nullable=False, index=True)
    start_time = db.Column(db.String(5), nullable=False, default="08:00")
    end_time = db.Column(db.String(5), nullable=False, default="21:00")
    status = db.Column(db.String(32), nullable=False, default="active")

    branch = db.relationship("Branch", lazy="joined")
    staff = db.relationship("Staff", lazy="joined")


class Service(db.Model, TimestampMixin):
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    group_name = db.Column(db.String(64), nullable=True)
    price = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    duration_minutes = db.Column(db.Integer, nullable=False, default=60)
    status = db.Column(db.String(32), nullable=False, default="active")

    branch = db.relationship("Branch", lazy="joined")


class ServiceInventoryUsage(db.Model):
    __tablename__ = "service_inventory_usages"
    __table_args__ = (UniqueConstraint("service_id", "item_id", name="uq_service_inventory_usage"),)

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey("inventory_items.id"), nullable=False, index=True)
    quantity = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    service = db.relationship("Service", lazy="joined")
    item = db.relationship("InventoryItem", lazy="joined")


class Room(db.Model, TimestampMixin):
    __tablename__ = "rooms"
    __table_args__ = (UniqueConstraint("branch_id", "name", name="uq_room_branch_name"),)

    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False, index=True)
    name = db.Column(db.String(64), nullable=False)
    room_type = db.Column(db.String(64), nullable=True)
    status = db.Column(db.String(32), nullable=False, default="active")

    branch = db.relationship("Branch", lazy="joined")


class Appointment(db.Model, TimestampMixin):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=True, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=True, index=True)
    customer_name = db.Column(db.String(255), nullable=False)
    customer_phone = db.Column(db.String(32), nullable=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False, index=True)
    technician_id = db.Column(db.Integer, db.ForeignKey("staffs.id"), nullable=False, index=True)
    appointment_date = db.Column(db.Date, nullable=False, index=True)
    appointment_time = db.Column(db.String(5), nullable=False)
    end_time = db.Column(db.String(5), nullable=True)
    status = db.Column(db.String(16), nullable=False, default="pending", index=True)
    note = db.Column(db.String(500), nullable=True)
    created_by = db.Column(db.String(64), nullable=True)

    branch = db.relationship("Branch", lazy="joined")
    customer = db.relationship("Customer", lazy="joined")
    room = db.relationship("Room", lazy="joined")
    service = db.relationship("Service", lazy="joined")
    technician = db.relationship("Staff", lazy="joined")
    service_items = db.relationship("AppointmentServiceItem", back_populates="appointment", cascade="all,delete-orphan")
    invoice = db.relationship("Invoice", back_populates="appointment", uselist=False)


class AppointmentServiceItem(db.Model):
    __tablename__ = "appointment_service_items"
    __table_args__ = (UniqueConstraint("appointment_id", "service_id", name="uq_appointment_service_item"),)

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id"), nullable=False, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False, index=True)
    service_name = db.Column(db.String(255), nullable=False)

    appointment = db.relationship("Appointment", back_populates="service_items", lazy="joined")
    service = db.relationship("Service", lazy="joined")


class Supplier(db.Model, TimestampMixin):
    __tablename__ = "suppliers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    phone = db.Column(db.String(32), nullable=True)
    address = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(32), nullable=False, default="active")


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


class InventoryLot(db.Model, TimestampMixin):
    __tablename__ = "inventory_lots"
    __table_args__ = (UniqueConstraint("branch_id", "item_id", "lot_code", name="uq_inventory_lot"),)

    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey("inventory_items.id"), nullable=False, index=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=True, index=True)
    lot_code = db.Column(db.String(64), nullable=False)
    expiry_date = db.Column(db.Date, nullable=True)
    quantity = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    branch = db.relationship("Branch", lazy="joined")
    item = db.relationship("InventoryItem", lazy="joined")
    supplier = db.relationship("Supplier", lazy="joined")


class InventoryTransfer(db.Model):
    __tablename__ = "inventory_transfers"

    id = db.Column(db.Integer, primary_key=True)
    from_branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False, index=True)
    to_branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey("inventory_items.id"), nullable=False, index=True)
    quantity = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    note = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(32), nullable=False, default="completed")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    from_branch = db.relationship("Branch", foreign_keys=[from_branch_id], lazy="joined")
    to_branch = db.relationship("Branch", foreign_keys=[to_branch_id], lazy="joined")
    item = db.relationship("InventoryItem", lazy="joined")


class InventoryTransaction(db.Model):
    __tablename__ = "inventory_transactions"

    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey("inventory_items.id"), nullable=False, index=True)
    related_invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=True, index=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=True, index=True)
    source_branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=True, index=True)
    target_branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=True, index=True)
    type = db.Column(db.String(16), nullable=False)
    quantity = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    lot_code = db.Column(db.String(64), nullable=True)
    expiry_date = db.Column(db.Date, nullable=True)
    supplier_name = db.Column(db.String(255), nullable=True)
    note = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    branch = db.relationship("Branch", foreign_keys=[branch_id], lazy="joined")
    item = db.relationship("InventoryItem", lazy="joined")
    invoice = db.relationship("Invoice", lazy="joined")
    supplier = db.relationship("Supplier", lazy="joined")
    source_branch = db.relationship("Branch", foreign_keys=[source_branch_id], lazy="joined")
    target_branch = db.relationship("Branch", foreign_keys=[target_branch_id], lazy="joined")


class Invoice(db.Model, TimestampMixin):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), nullable=False, unique=True, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False, index=True)
    staff_id = db.Column(db.Integer, db.ForeignKey("staffs.id"), nullable=True, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=True, index=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id"), nullable=True, unique=True, index=True)
    customer_name = db.Column(db.String(255), nullable=True)
    customer_phone = db.Column(db.String(32), nullable=True)
    subtotal_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    discount_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    tax_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    paid_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    balance_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    refund_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    status = db.Column(db.String(32), nullable=False, default="paid", index=True)
    payment_status = db.Column(db.String(32), nullable=False, default="paid", index=True)
    payment_method = db.Column(db.String(32), nullable=True)
    note = db.Column(db.String(500), nullable=True)
    canceled_reason = db.Column(db.String(500), nullable=True)
    canceled_at = db.Column(db.DateTime, nullable=True)
    inventory_consumed_at = db.Column(db.DateTime, nullable=True)
    last_action_by = db.Column(db.String(64), nullable=True)

    branch = db.relationship("Branch", lazy="joined")
    staff = db.relationship("Staff", lazy="joined")
    customer = db.relationship("Customer", lazy="joined")
    appointment = db.relationship("Appointment", back_populates="invoice", lazy="joined")
    items = db.relationship("InvoiceItem", back_populates="invoice", cascade="all,delete-orphan")
    payments = db.relationship("InvoicePayment", back_populates="invoice", cascade="all,delete-orphan")


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


class InvoicePayment(db.Model):
    __tablename__ = "invoice_payments"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False, index=True)
    payment_type = db.Column(db.String(16), nullable=False, default="payment")
    method = db.Column(db.String(32), nullable=False, default="cash")
    amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    note = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_by = db.Column(db.String(64), nullable=True)

    invoice = db.relationship("Invoice", back_populates="payments", lazy="joined")


def recalc_invoice(invoice: Invoice) -> None:
    subtotal = Decimal("0.00")
    for item in invoice.items:
        qty = Decimal(str(item.qty or 0))
        unit_price = Decimal(str(item.unit_price or 0))
        item.line_total = (qty * unit_price).quantize(Decimal("0.01"))
        subtotal += Decimal(str(item.line_total or 0))

    invoice.subtotal_amount = subtotal
    invoice.discount_amount = Decimal("0.00")
    invoice.tax_amount = Decimal("0.00")
    invoice.total_amount = subtotal

    paid = Decimal("0.00")
    refunded = Decimal("0.00")
    for payment in getattr(invoice, "payments", []) or []:
        amount = Decimal(str(payment.amount or 0))
        if payment.payment_type == "refund":
            refunded += amount
        else:
            paid += amount

    net_paid = paid - refunded
    if net_paid < 0:
        net_paid = Decimal("0.00")
    invoice.paid_amount = net_paid.quantize(Decimal("0.01"))
    invoice.refund_amount = refunded.quantize(Decimal("0.01"))
    invoice.balance_amount = Decimal("0.00")

    if invoice.status == "canceled":
        invoice.payment_status = "canceled"
        invoice.balance_amount = Decimal("0.00")
        return
    invoice.status = "paid"
    invoice.payment_status = "paid"


def normalize_money_to_thousand(amount: Decimal | int | float | str | None) -> Decimal:
    value = Decimal(str(amount or 0))
    if value <= 0:
        return Decimal("0.00")
    rounded = (value / Decimal("1000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * Decimal("1000")
    return rounded.quantize(Decimal("0.01"))


def minutes_between(start_time: str, end_time: str) -> int:
    start_dt = datetime.strptime(start_time, "%H:%M")
    end_dt = datetime.strptime(end_time, "%H:%M")
    return int((end_dt - start_dt).total_seconds() // 60)


def add_minutes_to_time(start_time: str, minutes: int) -> str:
    start_dt = datetime.strptime(start_time, "%H:%M")
    return (start_dt + timedelta(minutes=max(minutes, 1))).strftime("%H:%M")


def upsert_customer(branch_id: int, full_name: str, phone: str, note: str | None = None) -> Customer:
    customer = Customer.query.filter_by(branch_id=branch_id, phone=phone).first()
    if customer is None:
        customer = Customer(branch_id=branch_id, full_name=full_name, phone=phone)
        db.session.add(customer)
    customer.full_name = full_name or customer.full_name
    if note and not customer.note:
        customer.note = note
    return customer


def sync_customer_stats(customer: Customer | None) -> None:
    if customer is None or customer.id is None:
        return

    rows = (
        Invoice.query.filter(
            Invoice.customer_id == customer.id,
            Invoice.status != "canceled",
        )
        .order_by(Invoice.created_at.asc(), Invoice.id.asc())
        .all()
    )
    customer.visit_count = len(rows)
    customer.total_spent = sum((Decimal(str(row.paid_amount or 0)) for row in rows), Decimal("0.00"))
    customer.last_visit_at = rows[-1].created_at if rows else None
    if customer.total_spent >= Decimal("5000000"):
        customer.segment = "vip"
    elif customer.visit_count >= 3:
        customer.segment = "returning"
    else:
        customer.segment = "regular"


def ensure_stock_row(branch_id: int, item_id: int) -> InventoryStock:
    stock = InventoryStock.query.filter_by(branch_id=branch_id, item_id=item_id).first()
    if stock is None:
        stock = InventoryStock(branch_id=branch_id, item_id=item_id, quantity=Decimal("0.00"))
        db.session.add(stock)
        db.session.flush()
    return stock


def consume_inventory_for_invoice(invoice: Invoice) -> None:
    if invoice.status == "canceled" or invoice.inventory_consumed_at is not None:
        return

    usage_by_item: dict[int, Decimal] = {}
    for item in invoice.items:
        if not item.service_id:
            continue
        usage_rows = ServiceInventoryUsage.query.filter_by(service_id=item.service_id).all()
        for usage in usage_rows:
            qty = Decimal(str(item.qty or 0)) * Decimal(str(usage.quantity or 0))
            if qty <= 0:
                continue
            usage_by_item[usage.item_id] = usage_by_item.get(usage.item_id, Decimal("0.00")) + qty

    for item_id, qty in usage_by_item.items():
        stock = ensure_stock_row(invoice.branch_id, item_id)
        current_qty = Decimal(str(stock.quantity or 0))
        stock.quantity = max(current_qty - qty, Decimal("0.00"))
        db.session.add(
            InventoryTransaction(
                branch_id=invoice.branch_id,
                item_id=item_id,
                related_invoice_id=invoice.id,
                type="service_use",
                quantity=-qty,
                note=f"Tiêu hao theo hóa đơn {invoice.code}",
            )
        )

    if usage_by_item:
        invoice.inventory_consumed_at = datetime.utcnow()


def reverse_inventory_for_invoice(invoice: Invoice) -> None:
    if invoice.inventory_consumed_at is None:
        return

    tx_rows = InventoryTransaction.query.filter_by(
        branch_id=invoice.branch_id,
        related_invoice_id=invoice.id,
        type="service_use",
    ).all()
    for tx in tx_rows:
        restore_qty = -Decimal(str(tx.quantity or 0))
        if restore_qty <= 0:
            continue
        stock = ensure_stock_row(invoice.branch_id, tx.item_id)
        stock.quantity = Decimal(str(stock.quantity or 0)) + restore_qty
        db.session.add(
            InventoryTransaction(
                branch_id=invoice.branch_id,
                item_id=tx.item_id,
                related_invoice_id=invoice.id,
                type="service_use_reversal",
                quantity=restore_qty,
                note=f"Hoàn tiêu hao do hủy hóa đơn {invoice.code}",
            )
        )
    invoice.inventory_consumed_at = None


def add_column_if_missing(conn, table_name: str, existing_columns: set[str], column_name: str, ddl: str) -> None:
    if column_name not in existing_columns:
        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}"))
        existing_columns.add(column_name)


def migrate_remove_partial_payment_schema() -> None:
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())
    if "invoices" not in table_names:
        return

    invoice_columns = {col["name"] for col in inspector.get_columns("invoices")}

    with db.engine.begin() as conn:
        add_column_if_missing(conn, "invoices", invoice_columns, "tax_amount", "NUMERIC(12, 2) DEFAULT 0 NOT NULL")
        add_column_if_missing(conn, "invoices", invoice_columns, "paid_amount", "NUMERIC(12, 2) DEFAULT 0 NOT NULL")
        add_column_if_missing(conn, "invoices", invoice_columns, "balance_amount", "NUMERIC(12, 2) DEFAULT 0 NOT NULL")
        add_column_if_missing(conn, "invoices", invoice_columns, "refund_amount", "NUMERIC(12, 2) DEFAULT 0 NOT NULL")
        add_column_if_missing(conn, "invoices", invoice_columns, "payment_status", "VARCHAR(32) DEFAULT 'paid' NOT NULL")
        add_column_if_missing(conn, "invoices", invoice_columns, "payment_method", "VARCHAR(32)")
        add_column_if_missing(conn, "invoices", invoice_columns, "customer_id", "INTEGER")
        add_column_if_missing(conn, "invoices", invoice_columns, "appointment_id", "INTEGER")
        add_column_if_missing(conn, "invoices", invoice_columns, "inventory_consumed_at", "DATETIME")

        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_invoices_customer_id ON invoices(customer_id)"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_invoices_appointment_id ON invoices(appointment_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_invoices_payment_status ON invoices(payment_status)"))
        conn.execute(text("UPDATE invoices SET tax_amount = COALESCE(tax_amount, 0)"))
        conn.execute(text("UPDATE invoices SET paid_amount = COALESCE(NULLIF(paid_amount, 0), total_amount) WHERE status = 'paid'"))
        conn.execute(text("UPDATE invoices SET refund_amount = COALESCE(refund_amount, 0)"))
        conn.execute(text("UPDATE invoices SET payment_status = 'canceled', balance_amount = 0 WHERE status = 'canceled'"))
        conn.execute(text("UPDATE invoices SET status = 'paid', payment_status = 'paid', balance_amount = 0 WHERE status != 'canceled'"))


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


def migrate_add_operational_schema() -> None:
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())

    with db.engine.begin() as conn:
        if "appointments" in table_names:
            appointment_columns = {col["name"] for col in inspector.get_columns("appointments")}
            add_column_if_missing(conn, "appointments", appointment_columns, "customer_id", "INTEGER")
            add_column_if_missing(conn, "appointments", appointment_columns, "room_id", "INTEGER")
            add_column_if_missing(conn, "appointments", appointment_columns, "end_time", "VARCHAR(5)")
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_appointments_customer_id ON appointments(customer_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_appointments_room_id ON appointments(room_id)"))

        if "inventory_transactions" in table_names:
            tx_columns = {col["name"] for col in inspector.get_columns("inventory_transactions")}
            add_column_if_missing(conn, "inventory_transactions", tx_columns, "related_invoice_id", "INTEGER")
            add_column_if_missing(conn, "inventory_transactions", tx_columns, "supplier_id", "INTEGER")
            add_column_if_missing(conn, "inventory_transactions", tx_columns, "source_branch_id", "INTEGER")
            add_column_if_missing(conn, "inventory_transactions", tx_columns, "target_branch_id", "INTEGER")
            add_column_if_missing(conn, "inventory_transactions", tx_columns, "lot_code", "VARCHAR(64)")
            add_column_if_missing(conn, "inventory_transactions", tx_columns, "expiry_date", "DATE")
            add_column_if_missing(conn, "inventory_transactions", tx_columns, "supplier_name", "VARCHAR(255)")
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_inventory_transactions_related_invoice_id ON inventory_transactions(related_invoice_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_inventory_transactions_supplier_id ON inventory_transactions(supplier_id)"))

        if "inventory_lots" in table_names:
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_inventory_lots_unique ON inventory_lots(branch_id, item_id, lot_code)"))

    backfill_customers()
    backfill_appointment_service_items_and_end_times()
    backfill_invoice_payments()
    ensure_room_and_shift_seed()
    ensure_service_inventory_usage_seed()


def migrate_hash_plaintext_passwords() -> None:
    changed = False
    for user in User.query.order_by(User.id.asc()).all():
        if user.password_needs_rehash:
            user.set_password(user.password_hash or "")
            changed = True
    if changed:
        db.session.commit()


def migrate_cleanup_unused_columns() -> None:
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())
    drop_plan = {
        "branches": ["manager_name", "updated_at"],
        "users": ["updated_at"],
        "staffs": ["note", "updated_at"],
        "services": ["description", "updated_at"],
        "appointments": ["updated_at"],
        "inventory_items": ["updated_at"],
        "inventory_stocks": ["updated_at"],
        "invoices": ["updated_at"],
    }

    with db.engine.begin() as conn:
        for table_name, columns in drop_plan.items():
            if table_name not in table_names:
                continue

            existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
            for column_name in columns:
                if column_name not in existing_columns:
                    continue
                conn.execute(text(f"ALTER TABLE {table_name} DROP COLUMN {column_name}"))


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


def backfill_customers() -> None:
    changed = False

    for appointment in Appointment.query.order_by(Appointment.id.asc()).all():
        phone = (appointment.customer_phone or "").strip()
        if not phone:
            continue
        customer = upsert_customer(appointment.branch_id, appointment.customer_name, phone)
        if appointment.customer_id != customer.id:
            appointment.customer_id = customer.id
            changed = True

    for invoice in Invoice.query.order_by(Invoice.id.asc()).all():
        phone = (invoice.customer_phone or "").strip()
        name = (invoice.customer_name or "").strip()
        if not phone or not name:
            continue
        customer = upsert_customer(invoice.branch_id, name, phone)
        if invoice.customer_id != customer.id:
            invoice.customer_id = customer.id
            changed = True

    for customer in Customer.query.order_by(Customer.id.asc()).all():
        sync_customer_stats(customer)
        changed = True

    if changed:
        db.session.commit()


def backfill_appointment_service_items_and_end_times() -> None:
    changed = False
    for appointment in Appointment.query.order_by(Appointment.id.asc()).all():
        if not appointment.service_items and appointment.service_id:
            service = db.session.get(Service, appointment.service_id)
            if service:
                appointment.service_items.append(
                    AppointmentServiceItem(
                        appointment_id=appointment.id,
                        service_id=service.id,
                        service_name=service.name,
                    )
                )
                changed = True

        if not appointment.end_time:
            duration_minutes = 0
            for service_item in appointment.service_items:
                if service_item.service:
                    duration_minutes += int(service_item.service.duration_minutes or 0)
            if duration_minutes <= 0 and appointment.service:
                duration_minutes = int(appointment.service.duration_minutes or 60)
            if appointment.appointment_time:
                try:
                    appointment.end_time = add_minutes_to_time(appointment.appointment_time, duration_minutes or 60)
                    changed = True
                except ValueError:
                    pass

    if changed:
        db.session.commit()


def backfill_invoice_payments() -> None:
    changed = False
    for invoice in Invoice.query.order_by(Invoice.id.asc()).all():
        existing_payment = InvoicePayment.query.filter_by(invoice_id=invoice.id).first()
        if existing_payment is None and invoice.status != "canceled":
            amount = Decimal(str(invoice.paid_amount or 0))
            if amount <= 0:
                amount = Decimal(str(invoice.total_amount or 0))
            if amount > 0:
                db.session.add(
                    InvoicePayment(
                        invoice_id=invoice.id,
                        payment_type="payment",
                        method=invoice.payment_method or "legacy",
                        amount=amount,
                        note="Backfill thanh toán từ dữ liệu cũ",
                        created_by=invoice.last_action_by or "migration",
                    )
                )
                changed = True
        recalc_invoice(invoice)
        changed = True

    if changed:
        db.session.commit()


def ensure_room_and_shift_seed() -> None:
    changed = False
    for branch in Branch.query.order_by(Branch.id.asc()).all():
        room_count = Room.query.filter_by(branch_id=branch.id).count()
        if room_count == 0:
            for index in range(1, 4):
                db.session.add(
                    Room(
                        branch_id=branch.id,
                        name=f"Phòng {index}",
                        room_type="Giường trị liệu",
                        status="active",
                    )
                )
            changed = True

    if changed:
        db.session.flush()

    for branch in Branch.query.order_by(Branch.id.asc()).all():
        fallback_room = Room.query.filter_by(branch_id=branch.id, status="active").order_by(Room.id.asc()).first()
        if not fallback_room:
            continue
        for appointment in Appointment.query.filter_by(branch_id=branch.id).all():
            if appointment.room_id is None:
                appointment.room_id = fallback_room.id
                changed = True

    technician_rows = Staff.query.filter(Staff.status == "active", Staff.title.ilike("%Kỹ thuật viên%")).all()
    for staff in technician_rows:
        for weekday in range(7):
            exists = StaffShift.query.filter_by(staff_id=staff.id, weekday=weekday).first()
            if exists is None:
                db.session.add(
                    StaffShift(
                        branch_id=staff.branch_id,
                        staff_id=staff.id,
                        weekday=weekday,
                        start_time="08:00",
                        end_time="21:00",
                        status="active",
                    )
                )
                changed = True

    if changed:
        db.session.commit()


def ensure_service_inventory_usage_seed() -> None:
    items = {row.name: row for row in InventoryItem.query.order_by(InventoryItem.id.asc()).all()}
    if not items:
        return

    changed = False
    for service in Service.query.order_by(Service.id.asc()).all():
        existing = ServiceInventoryUsage.query.filter_by(service_id=service.id).first()
        if existing:
            continue

        service_name = (service.name or "").lower()
        usage_plan: list[tuple[InventoryItem | None, Decimal]] = []
        if any(keyword in service_name for keyword in ("massage", "body", "cổ vai gáy", "kinh lạc", "thắt lưng")):
            usage_plan.append((items.get("Tinh dầu massage"), Decimal("1")))
            usage_plan.append((items.get("Khăn spa"), Decimal("1")))
        elif any(keyword in service_name for keyword in ("da", "mụn", "peel")):
            usage_plan.append((items.get("Kem dưỡng da"), Decimal("1")))
            usage_plan.append((items.get("Khăn spa"), Decimal("1")))
        elif any(keyword in service_name for keyword in ("gội", "ngâm chân")):
            usage_plan.append((items.get("Khăn spa"), Decimal("1")))

        for item, qty in usage_plan:
            if item is None:
                continue
            db.session.add(ServiceInventoryUsage(service_id=service.id, item_id=item.id, quantity=qty))
            changed = True

    if changed:
        db.session.commit()


def ensure_seed_data() -> None:
    def upsert_branch(branch_code: str, name: str, address: str, phone: str, manager_name: str) -> Branch:
        branch = None
        if branch_code:
            branch = Branch.query.filter_by(branch_code=branch_code).first()
        if branch is None and phone:
            branch = Branch.query.filter_by(phone=phone).first()
        if branch is None:
            branch = Branch.query.filter_by(name=name).first()
        if branch is None:
            branch = Branch(name=name)
            db.session.add(branch)
        branch.branch_code = branch_code
        branch.address = address
        branch.phone = phone
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

    branch_seed = [
        {
            "code": "CN1",
            "name": "Chi nhánh 1",
            "address": "126 Nguyễn Trãi, Quận 1, TP.HCM",
            "phone": "02873001001",
            "manager_name": "Phạm Khắc Sang",
        },
        {
            "code": "CN2",
            "name": "Chi nhánh 2",
            "address": "88 Nguyễn Thị Thập, Quận 7, TP.HCM",
            "phone": "02873002002",
            "manager_name": "Vũ Quốc Nghĩa",
        },
        {
            "code": "CN3",
            "name": "Chi nhánh 3",
            "address": "45 Võ Văn Ngân, TP. Thủ Đức, TP.HCM",
            "phone": "02873003003",
            "manager_name": "Nguyễn Quang Tấn",
        },
    ]

    branch_map: dict[str, Branch] = {}
    for payload in branch_seed:
        branch = upsert_branch(
            payload["code"],
            payload["name"],
            payload["address"],
            payload["phone"],
            payload["manager_name"],
        )
        branch_map[payload["code"]] = branch

    db.session.flush()

    upsert_user("admin", "super_admin", None, "admin123", staff_id=None)

    if Staff.query.count() == 0:
        staff_seed = [
            # Active branch managers (IDs are created in this exact order).
            {
                "branch_code": "CN1",
                "full_name": "Phạm Khắc Sang",
                "phone": "0911000001",
                "title": "Quản lý chi nhánh",
                "status": "active",
                "start_date": date(2024, 1, 15),
            },
            {
                "branch_code": "CN2",
                "full_name": "Vũ Quốc Nghĩa",
                "phone": "0911000002",
                "title": "Quản lý chi nhánh",
                "status": "active",
                "start_date": date(2024, 2, 12),
            },
            {
                "branch_code": "CN3",
                "full_name": "Nguyễn Quang Tấn",
                "phone": "0911000003",
                "title": "Quản lý chi nhánh",
                "status": "active",
                "start_date": date(2024, 3, 8),
            },
            # Active receptionists (1 per branch).
            {
                "branch_code": "CN1",
                "full_name": "Trần Mai Hương",
                "phone": "0912000001",
                "title": "Lễ tân",
                "status": "active",
                "start_date": date(2024, 1, 18),
            },
            {
                "branch_code": "CN2",
                "full_name": "Nguyễn Yến Nhi",
                "phone": "0912000002",
                "title": "Lễ tân",
                "status": "active",
                "start_date": date(2024, 2, 16),
            },
            {
                "branch_code": "CN3",
                "full_name": "Lê Thu Hà",
                "phone": "0912000003",
                "title": "Lễ tân",
                "status": "active",
                "start_date": date(2024, 3, 12),
            },
            # Active technicians (3 per branch).
            {
                "branch_code": "CN1",
                "full_name": "Võ Hoàng Nam",
                "phone": "0913000001",
                "title": "Kỹ thuật viên",
                "status": "active",
                "start_date": date(2024, 1, 20),
            },
            {
                "branch_code": "CN1",
                "full_name": "Phan Gia Bảo",
                "phone": "0913000002",
                "title": "Kỹ thuật viên",
                "status": "active",
                "start_date": date(2024, 1, 22),
            },
            {
                "branch_code": "CN1",
                "full_name": "Đỗ Minh Châu",
                "phone": "0913000003",
                "title": "Kỹ thuật viên",
                "status": "active",
                "start_date": date(2024, 1, 25),
            },
            {
                "branch_code": "CN2",
                "full_name": "Bùi Quang Huy",
                "phone": "0913000004",
                "title": "Kỹ thuật viên",
                "status": "active",
                "start_date": date(2024, 2, 18),
            },
            {
                "branch_code": "CN2",
                "full_name": "Trịnh Khánh Ly",
                "phone": "0913000005",
                "title": "Kỹ thuật viên",
                "status": "active",
                "start_date": date(2024, 2, 20),
            },
            {
                "branch_code": "CN2",
                "full_name": "Hồ Nhật Nam",
                "phone": "0913000006",
                "title": "Kỹ thuật viên",
                "status": "active",
                "start_date": date(2024, 2, 23),
            },
            {
                "branch_code": "CN3",
                "full_name": "Đặng Anh Khoa",
                "phone": "0913000007",
                "title": "Kỹ thuật viên",
                "status": "active",
                "start_date": date(2024, 3, 14),
            },
            {
                "branch_code": "CN3",
                "full_name": "Tạ Diễm My",
                "phone": "0913000008",
                "title": "Kỹ thuật viên",
                "status": "active",
                "start_date": date(2024, 3, 16),
            },
            {
                "branch_code": "CN3",
                "full_name": "Phạm Quốc Khôi",
                "phone": "0913000009",
                "title": "Kỹ thuật viên",
                "status": "active",
                "start_date": date(2024, 3, 18),
            },
            # Active inventory controllers (1 per branch).
            {
                "branch_code": "CN1",
                "full_name": "Nguyễn Thanh Bình",
                "phone": "0914000001",
                "title": "Kiểm soát kho",
                "status": "active",
                "start_date": date(2024, 1, 28),
            },
            {
                "branch_code": "CN2",
                "full_name": "Vũ Bảo Trâm",
                "phone": "0914000002",
                "title": "Kiểm soát kho",
                "status": "active",
                "start_date": date(2024, 2, 26),
            },
            {
                "branch_code": "CN3",
                "full_name": "Trần Duy Khánh",
                "phone": "0914000003",
                "title": "Kiểm soát kho",
                "status": "active",
                "start_date": date(2024, 3, 20),
            },
            # Additional inactive records for realism.
            {
                "branch_code": "CN1",
                "full_name": "Hoàng Đức An",
                "phone": "0915000001",
                "title": "Kỹ thuật viên",
                "status": "inactive",
                "start_date": date(2024, 2, 2),
            },
            {
                "branch_code": "CN2",
                "full_name": "Lâm Ngọc Hân",
                "phone": "0915000002",
                "title": "Kỹ thuật viên",
                "status": "inactive",
                "start_date": date(2024, 3, 2),
            },
            {
                "branch_code": "CN3",
                "full_name": "Cao Minh Phúc",
                "phone": "0915000003",
                "title": "Kỹ thuật viên",
                "status": "inactive",
                "start_date": date(2024, 4, 2),
            },
            {
                "branch_code": "CN1",
                "full_name": "Phạm Tú Anh",
                "phone": "0915000004",
                "title": "Lễ tân",
                "status": "inactive",
                "start_date": date(2024, 2, 6),
            },
            {
                "branch_code": "CN3",
                "full_name": "Nguyễn Gia Hân",
                "phone": "0915000005",
                "title": "Lễ tân",
                "status": "inactive",
                "start_date": date(2024, 4, 6),
            },
            {
                "branch_code": "CN2",
                "full_name": "Lý Minh Khoa",
                "phone": "0915000006",
                "title": "Kiểm soát kho",
                "status": "inactive",
                "start_date": date(2024, 3, 5),
            },
            {
                "branch_code": "CN3",
                "full_name": "Trần Quốc Bảo",
                "phone": "0915000007",
                "title": "Quản lý chi nhánh",
                "status": "inactive",
                "start_date": date(2024, 4, 8),
            },
        ]

        for payload in staff_seed:
            branch = branch_map[payload["branch_code"]]
            db.session.add(
                Staff(
                    branch_id=branch.id,
                    full_name=payload["full_name"],
                    phone=payload["phone"],
                    title=payload["title"],
                    status=payload["status"],
                    start_date=payload["start_date"],
                )
            )
        db.session.flush()

    manager_by_branch = {
        "CN1": "Phạm Khắc Sang",
        "CN2": "Vũ Quốc Nghĩa",
        "CN3": "Nguyễn Quang Tấn",
    }

    for branch_code, manager_name in manager_by_branch.items():
        branch = branch_map[branch_code]
        manager_staff = Staff.query.filter_by(
            branch_id=branch.id,
            full_name=manager_name,
            title="Quản lý chi nhánh",
            status="active",
        ).first()
        branch.manager_staff_id = manager_staff.id if manager_staff else None

    def get_active_staff(branch_code: str, title: str, offset: int = 0) -> Staff | None:
        rows = (
            Staff.query.filter_by(
                branch_id=branch_map[branch_code].id,
                status="active",
                title=title,
            )
            .order_by(Staff.id.asc())
            .all()
        )
        if offset < 0 or offset >= len(rows):
            return None
        return rows[offset]

    manager_staff_cn1 = get_active_staff("CN1", "Quản lý chi nhánh")
    manager_staff_cn2 = get_active_staff("CN2", "Quản lý chi nhánh")
    manager_staff_cn3 = get_active_staff("CN3", "Quản lý chi nhánh")

    if manager_staff_cn1:
        upsert_user("manager", "branch_manager", manager_staff_cn1.branch_id, "manager123", manager_staff_cn1.id)
    if manager_staff_cn2:
        upsert_user("manager2", "branch_manager", manager_staff_cn2.branch_id, "manager123", manager_staff_cn2.id)
    if manager_staff_cn3:
        upsert_user("manager3", "branch_manager", manager_staff_cn3.branch_id, "manager123", manager_staff_cn3.id)

    for idx, branch_code in enumerate(("CN1", "CN2", "CN3"), start=1):
        receptionist = get_active_staff(branch_code, "Lễ tân")
        inventory_controller = get_active_staff(branch_code, "Kiểm soát kho")
        technician = get_active_staff(branch_code, "Kỹ thuật viên")

        if receptionist:
            upsert_user(
                f"letan{idx}",
                "receptionist",
                receptionist.branch_id,
                "letan123",
                receptionist.id,
            )
        if inventory_controller:
            upsert_user(
                f"kho{idx}",
                "inventory_controller",
                inventory_controller.branch_id,
                "kho12345",
                inventory_controller.id,
            )
        if technician:
            upsert_user(
                f"ktv{idx}",
                "technician",
                technician.branch_id,
                "ktv12345",
                technician.id,
            )

    if Service.query.count() == 0:
        service_catalog = [
            ("Chăm sóc da chuyên sâu", "Da mặt", Decimal("800000"), 60, "active"),
            ("Peel da sinh học", "Da mặt", Decimal("1200000"), 45, "active"),
            ("Nặn mụn chuẩn y khoa", "Da mặt", Decimal("500000"), 90, "inactive"),
            ("Massage Body tinh dầu", "Body", Decimal("700000"), 60, "active"),
            ("Tẩy tế bào chết toàn thân", "Body", Decimal("400000"), 40, "active"),
            ("Gội đầu dưỡng sinh VIP", "Thư giãn", Decimal("300000"), 45, "active"),
            ("Massage đá nóng Volcano", "Thư giãn", Decimal("900000"), 90, "active"),
            ("Ngâm chân thảo dược", "Thư giãn", Decimal("200000"), 30, "inactive"),
            ("Trị liệu cổ vai gáy", "Trị liệu", Decimal("800000"), 60, "active"),
            ("Thông kinh lạc chuyên sâu", "Trị liệu", Decimal("1300000"), 120, "active"),
            ("Phục hồi thắt lưng cột sống", "Trị liệu", Decimal("1000000"), 90, "active"),
        ]

        for branch in Branch.query.order_by(Branch.id.asc()).all():
            for name, group_name, price, duration_minutes, status in service_catalog:
                db.session.add(
                    Service(
                        branch_id=branch.id,
                        name=name,
                        group_name=group_name,
                        price=price,
                        duration_minutes=duration_minutes,
                        status=status,
                    )
                )
        db.session.flush()

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

    if InventoryStock.query.count() == 0:
        item_rows = InventoryItem.query.order_by(InventoryItem.id.asc()).all()
        stock_plan = {
            "CN1": {
                "Tinh dầu massage": Decimal("14"),
                "Kem dưỡng da": Decimal("10"),
                "Khăn spa": Decimal("30"),
            },
            "CN2": {
                "Tinh dầu massage": Decimal("12"),
                "Kem dưỡng da": Decimal("9"),
                "Khăn spa": Decimal("28"),
            },
            "CN3": {
                "Tinh dầu massage": Decimal("11"),
                "Kem dưỡng da": Decimal("8"),
                "Khăn spa": Decimal("26"),
            },
        }

        for branch_code, branch_data in stock_plan.items():
            branch = branch_map.get(branch_code)
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
                    )
                )
        db.session.flush()

    if Invoice.query.count() == 0:
        from random import Random

        rng = Random(20260410)
        customer_pool = [
            "Ngọc Bích",
            "Thanh Huyền",
            "Mỹ Linh",
            "Kiều Trinh",
            "Anh Duy",
            "Nhật Hạ",
            "Hoài Nam",
            "Hà Phương",
            "Phương Vy",
            "Minh Tú",
            "Thu Thảo",
            "Bảo Trân",
            "Như Quỳnh",
            "Gia Hân",
            "Khánh Linh",
            "Mai Phương",
            "Kim Ngân",
            "Thanh Tú",
            "Bích Trâm",
            "Tuấn Anh",
        ]
        canceled_reasons = [
            "Khách đổi lịch cá nhân",
            "Khách bận công tác đột xuất",
            "Khách yêu cầu chuyển sang chi nhánh khác",
            "Khách muốn dời sang tuần sau",
        ]
        invoice_note_pool = [
            None,
            None,
            "Khách mới",
            "Khách đặt qua fanpage",
            "Khách đặt qua hotline",
            "Khách thành viên VIP",
            "Khách quay lại theo lịch chăm sóc",
        ]

        def resolve_branch_ready_date(branch_id: int) -> date:
            required_titles = {
                "Quản lý chi nhánh",
                "Lễ tân",
                "Kỹ thuật viên",
                "Kiểm soát kho",
            }
            rows = (
                Staff.query.filter(
                    Staff.branch_id == branch_id,
                    Staff.status == "active",
                    Staff.title.in_(required_titles),
                )
                .order_by(Staff.start_date.asc(), Staff.id.asc())
                .all()
            )
            dates = [row.start_date for row in rows if row.start_date is not None]
            if not dates:
                return date.today() - timedelta(days=120)
            return max(dates)

        def split_candidate_dates(start_date: date, end_date: date) -> tuple[list[date], list[date], list[date]]:
            early_april_dates: list[date] = []
            april_remaining_dates: list[date] = []
            other_dates: list[date] = []

            cursor = start_date
            while cursor <= end_date:
                if cursor.month == 4 and cursor.day <= 10:
                    early_april_dates.append(cursor)
                elif cursor.month == 4:
                    april_remaining_dates.append(cursor)
                else:
                    other_dates.append(cursor)
                cursor += timedelta(days=1)

            return early_april_dates, april_remaining_dates, other_dates

        def pick_weighted_invoice_date(
            early_april_dates: list[date],
            april_remaining_dates: list[date],
            other_dates: list[date],
        ) -> date:
            weighted_buckets = [
                (early_april_dates, 0.60),
                (april_remaining_dates, 0.20),
                (other_dates, 0.20),
            ]
            available_buckets = [(rows, weight) for rows, weight in weighted_buckets if rows]
            if not available_buckets:
                return date.today()

            total_weight = sum(weight for _, weight in available_buckets)
            roll = rng.random() * total_weight
            running = 0.0
            for rows, weight in available_buckets:
                running += weight
                if roll <= running:
                    return rows[rng.randrange(len(rows))]

            tail_rows = available_buckets[-1][0]
            return tail_rows[rng.randrange(len(tail_rows))]

        for branch in Branch.query.order_by(Branch.id.asc()).all():
            receptionist_rows = (
                Staff.query.filter_by(
                    branch_id=branch.id,
                    status="active",
                    title="Lễ tân",
                )
                .order_by(Staff.id.asc())
                .all()
            )
            service_rows = (
                Service.query.filter_by(branch_id=branch.id, status="active")
                .order_by(Service.id.asc())
                .all()
            )
            if not receptionist_rows or not service_rows:
                continue

            today = date.today()
            six_month_window_start = today - timedelta(days=183)
            ready_date = resolve_branch_ready_date(branch.id)
            start_date = max(six_month_window_start, ready_date)
            if start_date > today:
                start_date = today - timedelta(days=7)

            early_april_dates, april_remaining_dates, other_dates = split_candidate_dates(start_date, today)
            invoice_count = rng.randint(18, 28)

            for _ in range(invoice_count):
                created_date = pick_weighted_invoice_date(early_april_dates, april_remaining_dates, other_dates)
                created_at = datetime.combine(created_date, datetime.min.time()) + timedelta(
                    hours=rng.randint(8, 20),
                    minutes=rng.choice([0, 10, 15, 20, 30, 40, 45, 50]),
                )

                customer_name = rng.choice(customer_pool)
                customer_phone = f"0{rng.randint(300000000, 999999999)}"
                operator_staff = rng.choice(receptionist_rows)
                discount = Decimal(str(rng.choice([0, 0, 0, 20000, 30000, 50000, 80000, 100000, 150000]))).quantize(
                    Decimal("0.01")
                )

                invoice = Invoice(
                    code="TMP",
                    branch_id=branch.id,
                    customer_name=customer_name,
                    customer_phone=customer_phone,
                    staff_id=operator_staff.id,
                    discount_amount=discount,
                    status="paid",
                    note=rng.choice(invoice_note_pool),
                    last_action_by="seed",
                    created_at=created_at,
                )
                db.session.add(invoice)
                db.session.flush()
                invoice.code = f"HD{invoice.id:06d}"

                line_count = min(len(service_rows), rng.randint(1, 4))
                selected_services = rng.sample(service_rows, k=line_count)
                for service in selected_services:
                    qty = Decimal(str(rng.choice([1, 1, 1, 2, 2, 3]))).quantize(Decimal("0.01"))
                    invoice.items.append(
                        InvoiceItem(
                            service_id=service.id,
                            service_name=service.name,
                            qty=qty,
                            unit_price=service.price,
                        )
                    )

                recalc_invoice(invoice)
                if rng.random() < 0.18:
                    invoice.status = "canceled"
                    invoice.canceled_reason = rng.choice(canceled_reasons)
                    canceled_at = created_at + timedelta(hours=rng.randint(1, 36))
                    if canceled_at > datetime.now():
                        canceled_at = datetime.now()
                    invoice.canceled_at = canceled_at

    if Appointment.query.count() == 0:
        for idx, branch in enumerate(Branch.query.order_by(Branch.id.asc()).all(), start=1):
            service_rows = Service.query.filter_by(branch_id=branch.id, status="active").order_by(Service.id.asc()).all()
            technician_rows = (
                Staff.query.filter_by(branch_id=branch.id, status="active", title="Kỹ thuật viên")
                .order_by(Staff.id.asc())
                .all()
            )
            if not service_rows or not technician_rows:
                continue

            db.session.add(
                Appointment(
                    branch_id=branch.id,
                    customer_name=f"Khách hẹn CN{idx}A",
                    customer_phone=f"094{idx}111111",
                    service_id=service_rows[0].id,
                    technician_id=technician_rows[0].id,
                    appointment_date=date.today(),
                    appointment_time="09:00",
                    status="pending",
                    note="Khách đặt qua fanpage",
                    created_by=f"letan{idx}",
                )
            )
            db.session.add(
                Appointment(
                    branch_id=branch.id,
                    customer_name=f"Khách hẹn CN{idx}B",
                    customer_phone=f"094{idx}222222",
                    service_id=service_rows[min(1, len(service_rows) - 1)].id,
                    technician_id=technician_rows[min(1, len(technician_rows) - 1)].id,
                    appointment_date=date.today() - timedelta(days=1),
                    appointment_time="14:30",
                    status="completed",
                    note="Đã hoàn thành liệu trình",
                    created_by=f"letan{idx}",
                )
            )

    db.session.commit()
    backfill_customers()
    backfill_appointment_service_items_and_end_times()
    backfill_invoice_payments()
    ensure_room_and_shift_seed()
    ensure_service_inventory_usage_seed()
