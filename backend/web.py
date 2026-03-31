from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import wraps
from typing import Any

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import and_, case, func

from backend.extensions import db
from backend.models.appointment import Appointment
from backend.models.audit_log import AuditLog
from backend.models.branch import Branch
from backend.models.commission_record import CommissionRecord
from backend.models.customer import Customer
from backend.models.customer_package import CustomerPackage
from backend.models.inventory_item import InventoryItem
from backend.models.invoice import Invoice
from backend.models.package import Package
from backend.models.payment import Payment
from backend.models.resource import Resource
from backend.models.service import Service
from backend.models.shift import Shift
from backend.models.staff import Staff
from backend.models.stock_transaction import StockTransaction
from backend.models.treatment_note import TreatmentNote
from backend.models.user import Role, User


web_bp = Blueprint(
    "web",
    __name__,
    url_prefix="/web",
    template_folder="templates",
    static_folder="static",
)


NAV_ITEMS: list[dict[str, Any]] = [
    {
        "endpoint": "web.dashboard",
        "path": "/web/dashboard",
        "label": "Tong quan",
        "roles": ["super_admin", "branch_manager"],
    },
    {
        "endpoint": "web.pos",
        "path": "/web/pos",
        "label": "POS / Hoa don",
        "roles": ["super_admin", "branch_manager", "reception", "cashier"],
    },
    {
        "endpoint": "web.customers",
        "path": "/web/customers",
        "label": "Khach hang",
        "roles": ["super_admin", "branch_manager", "reception", "cashier"],
    },
    {
        "endpoint": "web.appointments",
        "path": "/web/appointments",
        "label": "Lich hen",
        "roles": ["super_admin", "branch_manager", "reception", "technician"],
    },
    {
        "endpoint": "web.services",
        "path": "/web/services",
        "label": "Dich vu",
        "roles": ["super_admin", "branch_manager"],
    },
    {
        "endpoint": "web.packages",
        "path": "/web/packages",
        "label": "Goi lieu trinh",
        "roles": ["super_admin", "branch_manager"],
    },
    {
        "endpoint": "web.resources",
        "path": "/web/resources",
        "label": "Tai nguyen",
        "roles": ["super_admin", "branch_manager"],
    },
    {
        "endpoint": "web.inventory",
        "path": "/web/inventory",
        "label": "Kho",
        "roles": ["super_admin", "branch_manager", "warehouse"],
    },
    {
        "endpoint": "web.hr",
        "path": "/web/hr",
        "label": "Nhan su",
        "roles": ["super_admin", "branch_manager"],
    },
    {
        "endpoint": "web.reports",
        "path": "/web/reports",
        "label": "Bao cao",
        "roles": ["super_admin", "branch_manager"],
    },
    {
        "endpoint": "web.users",
        "path": "/web/users",
        "label": "Tai khoan",
        "roles": ["super_admin"],
    },
    {
        "endpoint": "web.branches",
        "path": "/web/branches",
        "label": "Chi nhanh",
        "roles": ["super_admin"],
    },
    {
        "endpoint": "web.audit_logs",
        "path": "/web/audit-logs",
        "label": "Nhat ky he thong",
        "roles": ["super_admin"],
    },
    {
        "endpoint": "web.technician",
        "path": "/web/technician",
        "label": "Ky thuat vien",
        "roles": ["technician"],
    },
]


def _format_money(value: Any) -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        number = 0
    return f"{number:,.0f} VND".replace(",", ".")


def _format_number(value: Any) -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        number = 0
    if number.is_integer():
        return f"{int(number):,}".replace(",", ".")
    return f"{number:,.2f}".replace(",", ".")


def _format_datetime(value: datetime | None) -> str:
    if not value:
        return ""
    return value.strftime("%d/%m/%Y %H:%M")


def _parse_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_next(target: str | None) -> str | None:
    if not target:
        return None
    if target.startswith("/") and not target.startswith("//"):
        return target
    return None


def _role_names(user: User | None) -> list[str]:
    if not user:
        return []
    return [str(role_name) for role_name in (user.role_names() or [])]


def _is_technician_only(user: User | None) -> bool:
    roles = set(_role_names(user))
    if "technician" not in roles:
        return False
    return not any(role in roles for role in ["super_admin", "branch_manager", "reception"])


def _allowed_branch_ids(user: User | None) -> list[int]:
    if not user:
        return []
    branch_ids = user.branch_ids() or []
    values = [_parse_int(branch_id) for branch_id in branch_ids]
    return [branch_id for branch_id in values if branch_id is not None]


def _active_branch_id(user: User | None) -> int | None:
    allowed = _allowed_branch_ids(user)
    if not allowed:
        return None

    from_query = _parse_int(request.args.get("branch_id"))
    if from_query in allowed:
        session["web_branch_id"] = from_query
        return from_query

    from_session = _parse_int(session.get("web_branch_id"))
    if from_session in allowed:
        return from_session

    fallback = allowed[0]
    session["web_branch_id"] = fallback
    return fallback


def _has_roles(user: User | None, allowed_roles: list[str]) -> bool:
    if not user:
        return False
    roles = set(_role_names(user))
    return any(role in roles for role in allowed_roles)


def _first_allowed_path(user: User | None) -> str:
    for item in NAV_ITEMS:
        if _has_roles(user, item["roles"]):
            return item["path"]
    return "/web/login"


def _login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not getattr(g, "web_user", None):
            target = request.full_path if request.query_string else request.path
            return redirect(url_for("web.login", next=target))
        return fn(*args, **kwargs)

    return wrapper


def _roles_required(*roles: str):
    def decorator(fn):
        @wraps(fn)
        @_login_required
        def wrapper(*args, **kwargs):
            if not _has_roles(getattr(g, "web_user", None), list(roles)):
                return render_template("web/forbidden.html"), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def _module_table(
    *,
    title: str,
    columns: list[dict[str, str]],
    rows: list[dict[str, Any]],
    empty_text: str = "Khong co du lieu.",
) -> dict[str, Any]:
    return {
        "title": title,
        "columns": columns,
        "rows": rows,
        "empty_text": empty_text,
    }


def _render_module_page(
    *,
    title: str,
    subtitle: str,
    cards: list[dict[str, str]],
    tables: list[dict[str, Any]],
):
    return render_template(
        "web/module.html",
        page_title=title,
        page_subtitle=subtitle,
        cards=cards,
        tables=tables,
    )


def _inventory_snapshot(branch_id: int) -> list[dict[str, Any]]:
    current_stock_expr = func.coalesce(func.sum(StockTransaction.delta_qty), 0)
    rows = (
        db.session.query(
            InventoryItem,
            current_stock_expr.label("current_stock"),
        )
        .outerjoin(
            StockTransaction,
            and_(
                StockTransaction.branch_id == branch_id,
                StockTransaction.inventory_item_id == InventoryItem.id,
            ),
        )
        .filter(InventoryItem.branch_id == branch_id)
        .group_by(InventoryItem.id)
        .order_by(InventoryItem.name.asc())
        .limit(400)
        .all()
    )

    items: list[dict[str, Any]] = []
    for item, current_stock in rows:
        stock_value = float(current_stock or 0)
        min_stock = float(item.min_stock or 0)
        items.append(
            {
                "id": item.id,
                "name": item.name,
                "sku": item.sku or "",
                "unit": item.unit,
                "min_stock": min_stock,
                "current_stock": stock_value,
                "low_stock": stock_value < min_stock,
            }
        )
    return items


@web_bp.before_app_request
def _load_web_context():
    if request.blueprint != "web":
        return

    user_id = _parse_int(session.get("web_user_id"))
    if user_id is None:
        g.web_user = None
        g.web_branch_id = None
        return

    user = User.query.filter_by(id=user_id, is_active=True).first()
    if user is None:
        session.pop("web_user_id", None)
        session.pop("web_branch_id", None)
        g.web_user = None
        g.web_branch_id = None
        return

    g.web_user = user
    g.web_branch_id = _active_branch_id(user)


@web_bp.app_context_processor
def _inject_web_context():
    user = getattr(g, "web_user", None)
    branch_ids = _allowed_branch_ids(user)
    branch_options = []
    if branch_ids:
        branch_rows = (
            Branch.query.filter(Branch.id.in_(branch_ids))
            .order_by(Branch.name.asc(), Branch.id.asc())
            .all()
        )
        branch_options = [{"id": row.id, "name": row.name} for row in branch_rows]

    visible_nav = [
        item for item in NAV_ITEMS if _has_roles(user, item["roles"])
    ]
    return {
        "web_user": user,
        "web_roles": _role_names(user),
        "web_nav_items": visible_nav,
        "web_branch_options": branch_options,
        "web_current_branch_id": getattr(g, "web_branch_id", None),
        "fmt_money": _format_money,
        "fmt_number": _format_number,
        "fmt_datetime": _format_datetime,
    }


@web_bp.route("/")
@_login_required
def index():
    return redirect(_first_allowed_path(getattr(g, "web_user", None)))


@web_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if getattr(g, "web_user", None):
            return redirect(_first_allowed_path(getattr(g, "web_user", None)))
        return render_template("web/login.html")

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    if not username or not password:
        flash("Vui long nhap day du tai khoan va mat khau.", "error")
        return render_template("web/login.html"), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.is_active or not user.verify_password(password):
        flash("Thong tin dang nhap khong dung.", "error")
        return render_template("web/login.html"), 401

    session["web_user_id"] = user.id
    branch_ids = _allowed_branch_ids(user)
    if branch_ids:
        session["web_branch_id"] = branch_ids[0]
    else:
        session.pop("web_branch_id", None)

    next_path = _safe_next(request.args.get("next") or request.form.get("next"))
    return redirect(next_path or _first_allowed_path(user))


@web_bp.post("/logout")
@_login_required
def logout():
    session.pop("web_user_id", None)
    session.pop("web_branch_id", None)
    return redirect(url_for("web.login"))


@web_bp.post("/switch-branch")
@_login_required
def switch_branch():
    user = getattr(g, "web_user", None)
    branch_ids = _allowed_branch_ids(user)
    selected = _parse_int(request.form.get("branch_id"))
    if selected in branch_ids:
        session["web_branch_id"] = selected
    return redirect(_safe_next(request.form.get("next")) or request.referrer or url_for("web.index"))


@web_bp.get("/forbidden")
def forbidden():
    return render_template("web/forbidden.html"), 403


@web_bp.get("/dashboard")
@_roles_required("super_admin", "branch_manager")
def dashboard():
    branch_id = getattr(g, "web_branch_id", None)
    if branch_id is None:
        flash("Tai khoan khong duoc gan chi nhanh.", "error")
        return redirect(url_for("web.login"))

    today = date.today()
    tomorrow = today + timedelta(days=1)

    revenue_total = (
        db.session.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.branch_id == branch_id,
            Payment.status == "posted",
        )
        .scalar()
    )
    payment_count = (
        db.session.query(func.count(Payment.id))
        .filter(
            Payment.branch_id == branch_id,
            Payment.status == "posted",
        )
        .scalar()
    )
    appointment_count = (
        db.session.query(func.count(Appointment.id))
        .filter(Appointment.branch_id == branch_id)
        .scalar()
    )
    customer_count = (
        db.session.query(func.count(Customer.id))
        .filter(Customer.branch_id == branch_id)
        .scalar()
    )

    low_stock_rows = [row for row in _inventory_snapshot(branch_id) if row["low_stock"]]

    paid_day = func.strftime("%Y-%m-%d", Payment.paid_at)
    revenue_rows = (
        db.session.query(
            paid_day.label("day"),
            func.coalesce(func.sum(Payment.amount), 0).label("revenue"),
        )
        .filter(
            Payment.branch_id == branch_id,
            Payment.status == "posted",
            Payment.paid_at.isnot(None),
        )
        .group_by(paid_day)
        .order_by(paid_day.desc())
        .limit(30)
        .all()
    )
    revenue_series = [
        {"day": day, "revenue": float(revenue or 0)}
        for day, revenue in reversed(revenue_rows)
    ]
    max_revenue = max([item["revenue"] for item in revenue_series], default=0)
    for item in revenue_series:
        if max_revenue > 0:
            item["pct"] = max(3, int((item["revenue"] / max_revenue) * 100))
        else:
            item["pct"] = 0

    status_rows = (
        db.session.query(Appointment.status, func.count(Appointment.id))
        .filter(Appointment.branch_id == branch_id)
        .group_by(Appointment.status)
        .order_by(func.count(Appointment.id).desc())
        .all()
    )
    appointment_status = [
        {"status": status or "unknown", "count": int(total or 0)}
        for status, total in status_rows
    ]

    top_service_rows = (
        db.session.query(
            Service.name,
            func.coalesce(func.sum(Payment.amount), 0).label("revenue"),
        )
        .join(
            Invoice,
            and_(
                Payment.invoice_id == Invoice.id,
                Invoice.branch_id == branch_id,
            ),
        )
        .join(
            Appointment,
            and_(
                Invoice.appointment_id == Appointment.id,
                Appointment.branch_id == branch_id,
            ),
        )
        .join(
            Service,
            and_(
                Appointment.service_id == Service.id,
                Service.branch_id == branch_id,
            ),
        )
        .filter(
            Payment.branch_id == branch_id,
            Payment.status == "posted",
        )
        .group_by(Service.id, Service.name)
        .order_by(func.sum(Payment.amount).desc())
        .limit(6)
        .all()
    )
    top_services = [
        {"name": name or "Chua gan dich vu", "revenue": float(revenue or 0)}
        for name, revenue in top_service_rows
    ]

    appointment_rows = (
        db.session.query(Appointment, Customer.full_name, Service.name, Staff.full_name)
        .outerjoin(Customer, Appointment.customer_id == Customer.id)
        .outerjoin(Service, Appointment.service_id == Service.id)
        .outerjoin(Staff, Appointment.staff_id == Staff.id)
        .filter(
            Appointment.branch_id == branch_id,
            Appointment.start_time >= datetime.combine(today, datetime.min.time()),
            Appointment.start_time < datetime.combine(tomorrow, datetime.min.time()),
        )
        .order_by(Appointment.start_time.asc(), Appointment.id.asc())
        .limit(12)
        .all()
    )
    today_appointments = [
        {
            "id": appointment.id,
            "time": appointment.start_time.strftime("%H:%M") if appointment.start_time else "",
            "customer": customer_name or f"Khach #{appointment.customer_id}",
            "service": service_name or "Chua gan",
            "staff": staff_name or "Chua phan cong",
            "status": appointment.status,
        }
        for appointment, customer_name, service_name, staff_name in appointment_rows
    ]

    branch_performance: list[dict[str, Any]] = []
    if _has_roles(getattr(g, "web_user", None), ["super_admin"]):
        branch_rows = (
            db.session.query(
                Branch.name,
                func.coalesce(func.sum(Payment.amount), 0).label("revenue"),
            )
            .outerjoin(
                Payment,
                and_(
                    Payment.branch_id == Branch.id,
                    Payment.status == "posted",
                ),
            )
            .group_by(Branch.id, Branch.name)
            .order_by(func.sum(Payment.amount).desc())
            .limit(8)
            .all()
        )
        branch_performance = [
            {"branch": name, "revenue": float(revenue or 0)}
            for name, revenue in branch_rows
        ]

    stats = [
        {"label": "Doanh thu", "value": _format_money(revenue_total)},
        {"label": "Giao dich", "value": _format_number(payment_count)},
        {"label": "Lich hen", "value": _format_number(appointment_count)},
        {"label": "Khach hang", "value": _format_number(customer_count)},
        {"label": "Canh bao kho", "value": _format_number(len(low_stock_rows))},
    ]

    return render_template(
        "web/dashboard.html",
        stats=stats,
        revenue_series=revenue_series,
        appointment_status=appointment_status,
        top_services=top_services,
        today_appointments=today_appointments,
        branch_performance=branch_performance,
        low_stock_items=low_stock_rows[:10],
    )


@web_bp.get("/pos")
@_roles_required("super_admin", "branch_manager", "reception", "cashier")
def pos():
    branch_id = getattr(g, "web_branch_id", None)
    if branch_id is None:
        return redirect(url_for("web.index"))

    invoice_rows = (
        db.session.query(Invoice, Customer.full_name)
        .outerjoin(Customer, Invoice.customer_id == Customer.id)
        .filter(Invoice.branch_id == branch_id)
        .order_by(Invoice.id.desc())
        .limit(120)
        .all()
    )
    payment_rows = (
        Payment.query.filter(Payment.branch_id == branch_id)
        .order_by(Payment.id.desc())
        .limit(120)
        .all()
    )

    invoice_items = []
    for invoice, customer_name in invoice_rows:
        invoice_items.append(
            {
                "id": invoice.id,
                "khach_hang": customer_name or f"#{invoice.customer_id}" if invoice.customer_id else "Khach le",
                "tong_tien": _format_money(invoice.total_amount),
                "da_thu": _format_money(invoice.paid_amount),
                "con_lai": _format_money(invoice.balance_amount),
                "trang_thai": invoice.status,
                "tao_luc": _format_datetime(invoice.created_at),
            }
        )

    payment_items = [
        {
            "id": payment.id,
            "hoa_don": f"#{payment.invoice_id}",
            "so_tien": _format_money(payment.amount),
            "phuong_thuc": payment.method,
            "trang_thai": payment.status,
            "thoi_diem": _format_datetime(payment.paid_at or payment.created_at),
            "ma_tham_chieu": payment.reference_code or "",
        }
        for payment in payment_rows
    ]

    cards = [
        {"label": "Hoa don", "value": _format_number(len(invoice_items))},
        {"label": "Thanh toan", "value": _format_number(len(payment_items))},
        {
            "label": "Tong thu",
            "value": _format_money(
                sum(float(payment.amount or 0) for payment in payment_rows if payment.status == "posted")
            ),
        },
    ]
    tables = [
        _module_table(
            title="Danh sach hoa don",
            columns=[
                {"key": "id", "label": "ID"},
                {"key": "khach_hang", "label": "Khach hang"},
                {"key": "tong_tien", "label": "Tong tien"},
                {"key": "da_thu", "label": "Da thu"},
                {"key": "con_lai", "label": "Con lai"},
                {"key": "trang_thai", "label": "Trang thai"},
                {"key": "tao_luc", "label": "Tao luc"},
            ],
            rows=invoice_items,
        ),
        _module_table(
            title="Danh sach thanh toan",
            columns=[
                {"key": "id", "label": "ID"},
                {"key": "hoa_don", "label": "Hoa don"},
                {"key": "so_tien", "label": "So tien"},
                {"key": "phuong_thuc", "label": "Phuong thuc"},
                {"key": "trang_thai", "label": "Trang thai"},
                {"key": "thoi_diem", "label": "Thoi diem"},
                {"key": "ma_tham_chieu", "label": "Ma tham chieu"},
            ],
            rows=payment_items,
        ),
    ]
    return _render_module_page(
        title="POS / Hoa don",
        subtitle="Du lieu dong bo truc tiep tu invoices va payments trong backend.",
        cards=cards,
        tables=tables,
    )


@web_bp.get("/customers")
@_roles_required("super_admin", "branch_manager", "reception", "cashier")
def customers():
    branch_id = getattr(g, "web_branch_id", None)
    if branch_id is None:
        return redirect(url_for("web.index"))

    customer_rows = (
        Customer.query.filter(Customer.branch_id == branch_id)
        .order_by(Customer.id.desc())
        .limit(200)
        .all()
    )
    package_rows = (
        db.session.query(CustomerPackage, Customer.full_name, Package.name)
        .outerjoin(Customer, CustomerPackage.customer_id == Customer.id)
        .outerjoin(Package, CustomerPackage.package_id == Package.id)
        .filter(CustomerPackage.branch_id == branch_id)
        .order_by(CustomerPackage.id.desc())
        .limit(200)
        .all()
    )

    customer_items = [
        {
            "id": row.id,
            "ho_ten": row.full_name,
            "dien_thoai": row.phone,
            "email": row.email or "",
            "gioi_tinh": row.gender or "",
            "trang_thai": row.status,
            "tao_luc": _format_datetime(row.created_at),
        }
        for row in customer_rows
    ]
    package_items = [
        {
            "id": customer_package.id,
            "khach_hang": customer_name or f"#{customer_package.customer_id}",
            "goi": package_name or f"#{customer_package.package_id}",
            "tong_buoi": customer_package.sessions_total,
            "con_lai": customer_package.sessions_remaining,
            "het_han": customer_package.expires_at.strftime("%d/%m/%Y")
            if customer_package.expires_at
            else "",
            "trang_thai": customer_package.status,
        }
        for customer_package, customer_name, package_name in package_rows
    ]

    cards = [
        {"label": "Khach hang", "value": _format_number(len(customer_items))},
        {"label": "Goi da ban", "value": _format_number(len(package_items))},
        {
            "label": "Dang hoat dong",
            "value": _format_number(len([item for item in customer_items if item["trang_thai"] == "active"])),
        },
    ]
    tables = [
        _module_table(
            title="Khach hang",
            columns=[
                {"key": "id", "label": "ID"},
                {"key": "ho_ten", "label": "Ho ten"},
                {"key": "dien_thoai", "label": "Dien thoai"},
                {"key": "email", "label": "Email"},
                {"key": "gioi_tinh", "label": "Gioi tinh"},
                {"key": "trang_thai", "label": "Trang thai"},
                {"key": "tao_luc", "label": "Tao luc"},
            ],
            rows=customer_items,
        ),
        _module_table(
            title="Customer Packages",
            columns=[
                {"key": "id", "label": "ID"},
                {"key": "khach_hang", "label": "Khach hang"},
                {"key": "goi", "label": "Goi"},
                {"key": "tong_buoi", "label": "Tong buoi"},
                {"key": "con_lai", "label": "Con lai"},
                {"key": "het_han", "label": "Het han"},
                {"key": "trang_thai", "label": "Trang thai"},
            ],
            rows=package_items,
        ),
    ]
    return _render_module_page(
        title="Khach hang",
        subtitle="Dong bo tu customers va customer_packages.",
        cards=cards,
        tables=tables,
    )


@web_bp.get("/appointments")
@_roles_required("super_admin", "branch_manager", "reception", "technician")
def appointments():
    branch_id = getattr(g, "web_branch_id", None)
    if branch_id is None:
        return redirect(url_for("web.index"))

    query = (
        db.session.query(
            Appointment,
            Customer.full_name,
            Service.name,
            Staff.full_name,
            Resource.name,
        )
        .outerjoin(Customer, Appointment.customer_id == Customer.id)
        .outerjoin(Service, Appointment.service_id == Service.id)
        .outerjoin(Staff, Appointment.staff_id == Staff.id)
        .outerjoin(Resource, Appointment.resource_id == Resource.id)
        .filter(Appointment.branch_id == branch_id)
    )
    if _is_technician_only(getattr(g, "web_user", None)):
        current_user_id = getattr(g, "web_user", None).id
        staff = Staff.query.filter_by(branch_id=branch_id, user_id=current_user_id).first()
        if staff:
            query = query.filter(Appointment.staff_id == staff.id)
        else:
            query = query.filter(Appointment.id == -1)

    appt_rows = query.order_by(Appointment.start_time.desc()).limit(220).all()
    appt_ids = [appointment.id for appointment, *_ in appt_rows]
    note_map: dict[int, TreatmentNote] = {}
    if appt_ids:
        notes = TreatmentNote.query.filter(TreatmentNote.appointment_id.in_(appt_ids)).all()
        note_map = {row.appointment_id: row for row in notes}

    appointment_items = []
    for appointment, customer_name, service_name, staff_name, resource_name in appt_rows:
        has_note = "co" if appointment.id in note_map else "khong"
        appointment_items.append(
            {
                "id": appointment.id,
                "khach_hang": customer_name or f"#{appointment.customer_id}",
                "dich_vu": service_name or "",
                "nhan_vien": staff_name or "",
                "tai_nguyen": resource_name or "",
                "bat_dau": _format_datetime(appointment.start_time),
                "ket_thuc": _format_datetime(appointment.end_time),
                "trang_thai": appointment.status,
                "treatment_note": has_note,
            }
        )

    cards = [
        {"label": "Tong lich hen", "value": _format_number(len(appointment_items))},
        {
            "label": "Dang phuc vu",
            "value": _format_number(
                len([item for item in appointment_items if item["trang_thai"] in {"arrived", "in_service"}])
            ),
        },
        {
            "label": "Da hoan tat",
            "value": _format_number(
                len([item for item in appointment_items if item["trang_thai"] in {"completed", "paid"}])
            ),
        },
    ]
    tables = [
        _module_table(
            title="Lich hen",
            columns=[
                {"key": "id", "label": "ID"},
                {"key": "khach_hang", "label": "Khach hang"},
                {"key": "dich_vu", "label": "Dich vu"},
                {"key": "nhan_vien", "label": "Nhan vien"},
                {"key": "tai_nguyen", "label": "Tai nguyen"},
                {"key": "bat_dau", "label": "Bat dau"},
                {"key": "ket_thuc", "label": "Ket thuc"},
                {"key": "trang_thai", "label": "Trang thai"},
                {"key": "treatment_note", "label": "Treatment note"},
            ],
            rows=appointment_items,
        ),
    ]
    return _render_module_page(
        title="Lich hen",
        subtitle="Dong bo tu appointments va treatment_notes.",
        cards=cards,
        tables=tables,
    )


@web_bp.get("/services")
@_roles_required("super_admin", "branch_manager")
def services():
    branch_id = getattr(g, "web_branch_id", None)
    if branch_id is None:
        return redirect(url_for("web.index"))

    rows = (
        Service.query.filter(Service.branch_id == branch_id)
        .order_by(Service.id.desc())
        .limit(220)
        .all()
    )
    items = [
        {
            "id": row.id,
            "ten": row.name,
            "gia": _format_money(row.price),
            "thoi_gian_phut": row.duration_minutes,
            "trang_thai": row.status,
            "tao_luc": _format_datetime(row.created_at),
        }
        for row in rows
    ]
    cards = [
        {"label": "Tong dich vu", "value": _format_number(len(items))},
        {"label": "Dang hoat dong", "value": _format_number(len([row for row in items if row["trang_thai"] == "active"]))},
        {
            "label": "Gia trung binh",
            "value": _format_money(
                (
                    sum(float(service.price or 0) for service in rows) / len(rows)
                    if rows
                    else 0
                )
            ),
        },
    ]
    tables = [
        _module_table(
            title="Danh muc dich vu",
            columns=[
                {"key": "id", "label": "ID"},
                {"key": "ten", "label": "Ten"},
                {"key": "gia", "label": "Gia"},
                {"key": "thoi_gian_phut", "label": "Thoi gian (phut)"},
                {"key": "trang_thai", "label": "Trang thai"},
                {"key": "tao_luc", "label": "Tao luc"},
            ],
            rows=items,
        )
    ]
    return _render_module_page(
        title="Dich vu",
        subtitle="Du lieu tu services backend.",
        cards=cards,
        tables=tables,
    )


@web_bp.get("/packages")
@_roles_required("super_admin", "branch_manager")
def packages():
    branch_id = getattr(g, "web_branch_id", None)
    if branch_id is None:
        return redirect(url_for("web.index"))

    rows = (
        Package.query.filter(Package.branch_id == branch_id)
        .order_by(Package.id.desc())
        .limit(220)
        .all()
    )
    items = [
        {
            "id": row.id,
            "ten_goi": row.name,
            "tong_buoi": row.sessions_total,
            "hieu_luc_ngay": row.validity_days if row.validity_days is not None else "",
            "shareable": "co" if row.shareable else "khong",
            "trang_thai": row.status,
        }
        for row in rows
    ]
    cards = [
        {"label": "Tong goi", "value": _format_number(len(items))},
        {"label": "Dang hoat dong", "value": _format_number(len([row for row in rows if row.status == "active"]))},
    ]
    tables = [
        _module_table(
            title="Goi lieu trinh",
            columns=[
                {"key": "id", "label": "ID"},
                {"key": "ten_goi", "label": "Ten goi"},
                {"key": "tong_buoi", "label": "Tong buoi"},
                {"key": "hieu_luc_ngay", "label": "Hieu luc (ngay)"},
                {"key": "shareable", "label": "Chia se"},
                {"key": "trang_thai", "label": "Trang thai"},
            ],
            rows=items,
        )
    ]
    return _render_module_page(
        title="Goi lieu trinh",
        subtitle="Du lieu tu packages backend.",
        cards=cards,
        tables=tables,
    )


@web_bp.get("/resources")
@_roles_required("super_admin", "branch_manager")
def resources():
    branch_id = getattr(g, "web_branch_id", None)
    if branch_id is None:
        return redirect(url_for("web.index"))

    rows = (
        Resource.query.filter(Resource.branch_id == branch_id)
        .order_by(Resource.id.desc())
        .limit(220)
        .all()
    )
    items = [
        {
            "id": row.id,
            "ten": row.name,
            "loai": row.resource_type,
            "code": row.code or "",
            "bao_tri": "co" if row.maintenance_flag else "khong",
            "trang_thai": row.status,
        }
        for row in rows
    ]
    cards = [
        {"label": "Tai nguyen", "value": _format_number(len(items))},
        {
            "label": "Dang bao tri",
            "value": _format_number(len([row for row in rows if row.maintenance_flag])),
        },
    ]
    tables = [
        _module_table(
            title="Tai nguyen chi nhanh",
            columns=[
                {"key": "id", "label": "ID"},
                {"key": "ten", "label": "Ten"},
                {"key": "loai", "label": "Loai"},
                {"key": "code", "label": "Code"},
                {"key": "bao_tri", "label": "Bao tri"},
                {"key": "trang_thai", "label": "Trang thai"},
            ],
            rows=items,
        )
    ]
    return _render_module_page(
        title="Tai nguyen",
        subtitle="Du lieu tu resources backend.",
        cards=cards,
        tables=tables,
    )


@web_bp.get("/inventory")
@_roles_required("super_admin", "branch_manager", "warehouse")
def inventory():
    branch_id = getattr(g, "web_branch_id", None)
    if branch_id is None:
        return redirect(url_for("web.index"))

    snapshot_rows = _inventory_snapshot(branch_id)
    tx_rows = (
        db.session.query(StockTransaction, InventoryItem.name)
        .outerjoin(InventoryItem, StockTransaction.inventory_item_id == InventoryItem.id)
        .filter(StockTransaction.branch_id == branch_id)
        .order_by(StockTransaction.id.desc())
        .limit(220)
        .all()
    )
    inventory_items = [
        {
            "id": row["id"],
            "ten": row["name"],
            "sku": row["sku"],
            "ton_hien_tai": _format_number(row["current_stock"]),
            "ton_toi_thieu": _format_number(row["min_stock"]),
            "don_vi": row["unit"],
            "canh_bao": "thieu" if row["low_stock"] else "ok",
        }
        for row in snapshot_rows
    ]
    tx_items = [
        {
            "id": tx.id,
            "mat_hang": item_name or f"#{tx.inventory_item_id}",
            "loai": tx.transaction_type,
            "delta": _format_number(tx.delta_qty),
            "nguon": tx.source_type or "",
            "source_id": tx.source_id if tx.source_id is not None else "",
            "ghi_chu": tx.note or "",
            "tao_luc": _format_datetime(tx.created_at),
        }
        for tx, item_name in tx_rows
    ]

    cards = [
        {"label": "Mat hang", "value": _format_number(len(inventory_items))},
        {"label": "Sap het", "value": _format_number(len([row for row in snapshot_rows if row["low_stock"]]))},
        {"label": "Giao dich kho", "value": _format_number(len(tx_items))},
    ]
    tables = [
        _module_table(
            title="Ton kho hien tai",
            columns=[
                {"key": "id", "label": "ID"},
                {"key": "ten", "label": "Ten"},
                {"key": "sku", "label": "SKU"},
                {"key": "ton_hien_tai", "label": "Ton hien tai"},
                {"key": "ton_toi_thieu", "label": "Ton toi thieu"},
                {"key": "don_vi", "label": "Don vi"},
                {"key": "canh_bao", "label": "Canh bao"},
            ],
            rows=inventory_items,
        ),
        _module_table(
            title="Stock Transactions",
            columns=[
                {"key": "id", "label": "ID"},
                {"key": "mat_hang", "label": "Mat hang"},
                {"key": "loai", "label": "Loai"},
                {"key": "delta", "label": "Delta"},
                {"key": "nguon", "label": "Nguon"},
                {"key": "source_id", "label": "Source ID"},
                {"key": "ghi_chu", "label": "Ghi chu"},
                {"key": "tao_luc", "label": "Tao luc"},
            ],
            rows=tx_items,
        ),
    ]
    return _render_module_page(
        title="Kho",
        subtitle="Dong bo tu inventory_items va stock_transactions.",
        cards=cards,
        tables=tables,
    )


@web_bp.get("/hr")
@_roles_required("super_admin", "branch_manager")
def hr():
    branch_id = getattr(g, "web_branch_id", None)
    if branch_id is None:
        return redirect(url_for("web.index"))

    staff_rows = (
        Staff.query.filter(Staff.branch_id == branch_id)
        .order_by(Staff.id.desc())
        .limit(200)
        .all()
    )
    shift_rows = (
        db.session.query(Shift, Staff.full_name)
        .outerjoin(Staff, Shift.staff_id == Staff.id)
        .filter(Shift.branch_id == branch_id)
        .order_by(Shift.id.desc())
        .limit(200)
        .all()
    )
    commission_rows = (
        db.session.query(CommissionRecord, Staff.full_name)
        .outerjoin(Staff, CommissionRecord.staff_id == Staff.id)
        .filter(CommissionRecord.branch_id == branch_id)
        .order_by(CommissionRecord.id.desc())
        .limit(200)
        .all()
    )

    staff_items = [
        {
            "id": row.id,
            "ho_ten": row.full_name,
            "vai_tro": row.role or "",
            "chuc_danh": row.title or "",
            "ky_nang": row.skill_level or "",
            "dien_thoai": row.phone or "",
            "trang_thai": row.status,
        }
        for row in staff_rows
    ]
    shift_items = [
        {
            "id": shift.id,
            "nhan_vien": staff_name or f"#{shift.staff_id}",
            "bat_dau": _format_datetime(shift.start_time),
            "ket_thuc": _format_datetime(shift.end_time),
            "trang_thai": shift.status,
            "ghi_chu": shift.note or "",
        }
        for shift, staff_name in shift_rows
    ]
    commission_items = [
        {
            "id": row.id,
            "nhan_vien": staff_name or f"#{row.staff_id}",
            "hoa_don": f"#{row.invoice_id}" if row.invoice_id else "",
            "co_so": _format_money(row.base_amount),
            "ty_le": _format_number(row.rate_percent) if row.rate_percent is not None else "",
            "hoa_hong": _format_money(row.commission_amount),
            "trang_thai": row.status,
        }
        for row, staff_name in commission_rows
    ]

    cards = [
        {"label": "Nhan vien", "value": _format_number(len(staff_items))},
        {"label": "Ca lam", "value": _format_number(len(shift_items))},
        {"label": "Hoa hong", "value": _format_number(len(commission_items))},
    ]
    tables = [
        _module_table(
            title="Nhan su",
            columns=[
                {"key": "id", "label": "ID"},
                {"key": "ho_ten", "label": "Ho ten"},
                {"key": "vai_tro", "label": "Vai tro"},
                {"key": "chuc_danh", "label": "Chuc danh"},
                {"key": "ky_nang", "label": "Ky nang"},
                {"key": "dien_thoai", "label": "Dien thoai"},
                {"key": "trang_thai", "label": "Trang thai"},
            ],
            rows=staff_items,
        ),
        _module_table(
            title="Shifts",
            columns=[
                {"key": "id", "label": "ID"},
                {"key": "nhan_vien", "label": "Nhan vien"},
                {"key": "bat_dau", "label": "Bat dau"},
                {"key": "ket_thuc", "label": "Ket thuc"},
                {"key": "trang_thai", "label": "Trang thai"},
                {"key": "ghi_chu", "label": "Ghi chu"},
            ],
            rows=shift_items,
        ),
        _module_table(
            title="Commission Records",
            columns=[
                {"key": "id", "label": "ID"},
                {"key": "nhan_vien", "label": "Nhan vien"},
                {"key": "hoa_don", "label": "Hoa don"},
                {"key": "co_so", "label": "Co so"},
                {"key": "ty_le", "label": "Ty le (%)"},
                {"key": "hoa_hong", "label": "Hoa hong"},
                {"key": "trang_thai", "label": "Trang thai"},
            ],
            rows=commission_items,
        ),
    ]
    return _render_module_page(
        title="Nhan su",
        subtitle="Tong hop staffs, shifts va commission_records.",
        cards=cards,
        tables=tables,
    )


@web_bp.get("/reports")
@_roles_required("super_admin", "branch_manager")
def reports():
    branch_id = getattr(g, "web_branch_id", None)
    if branch_id is None:
        return redirect(url_for("web.index"))

    paid_day = func.strftime("%Y-%m-%d", Payment.paid_at)
    revenue_rows = (
        db.session.query(
            paid_day.label("day"),
            func.coalesce(func.sum(Payment.amount), 0).label("revenue"),
            func.count(Payment.id).label("payments"),
        )
        .filter(
            Payment.branch_id == branch_id,
            Payment.status == "posted",
            Payment.paid_at.isnot(None),
        )
        .group_by(paid_day)
        .order_by(paid_day.desc())
        .limit(60)
        .all()
    )
    appointment_day = func.strftime("%Y-%m-%d", Appointment.start_time)
    appointment_rows = (
        db.session.query(
            appointment_day.label("day"),
            func.count(Appointment.id).label("total"),
            func.sum(case((Appointment.status == "cancelled", 1), else_=0)).label("cancelled"),
            func.sum(case((Appointment.status == "no_show", 1), else_=0)).label("no_show"),
        )
        .filter(Appointment.branch_id == branch_id)
        .group_by(appointment_day)
        .order_by(appointment_day.desc())
        .limit(60)
        .all()
    )
    low_stock_rows = [row for row in _inventory_snapshot(branch_id) if row["low_stock"]]

    revenue_items = [
        {
            "ngay": day,
            "doanh_thu": _format_money(revenue),
            "giao_dich": int(payments or 0),
        }
        for day, revenue, payments in revenue_rows
    ]
    appointment_items = [
        {
            "ngay": day,
            "tong_lich": int(total or 0),
            "huy": int(cancelled or 0),
            "no_show": int(no_show or 0),
        }
        for day, total, cancelled, no_show in appointment_rows
    ]
    inventory_items = [
        {
            "id": row["id"],
            "ten": row["name"],
            "sku": row["sku"],
            "ton_hien_tai": _format_number(row["current_stock"]),
            "ton_toi_thieu": _format_number(row["min_stock"]),
            "thieu_hut": _format_number(row["min_stock"] - row["current_stock"]),
        }
        for row in low_stock_rows
    ]

    cards = [
        {"label": "Dong doanh thu", "value": _format_number(len(revenue_items))},
        {"label": "Dong lich hen", "value": _format_number(len(appointment_items))},
        {"label": "Mat hang sap het", "value": _format_number(len(inventory_items))},
    ]
    tables = [
        _module_table(
            title="Bao cao doanh thu",
            columns=[
                {"key": "ngay", "label": "Ngay"},
                {"key": "doanh_thu", "label": "Doanh thu"},
                {"key": "giao_dich", "label": "Giao dich"},
            ],
            rows=revenue_items,
        ),
        _module_table(
            title="Bao cao lich hen",
            columns=[
                {"key": "ngay", "label": "Ngay"},
                {"key": "tong_lich", "label": "Tong lich"},
                {"key": "huy", "label": "Huy"},
                {"key": "no_show", "label": "No show"},
            ],
            rows=appointment_items,
        ),
        _module_table(
            title="Bao cao low-stock",
            columns=[
                {"key": "id", "label": "ID"},
                {"key": "ten", "label": "Ten"},
                {"key": "sku", "label": "SKU"},
                {"key": "ton_hien_tai", "label": "Ton hien tai"},
                {"key": "ton_toi_thieu", "label": "Ton toi thieu"},
                {"key": "thieu_hut", "label": "Thieu hut"},
            ],
            rows=inventory_items,
        ),
    ]
    return _render_module_page(
        title="Bao cao",
        subtitle="Du lieu tong hop tu reports backend (revenue, appointments, inventory).",
        cards=cards,
        tables=tables,
    )


@web_bp.get("/users")
@_roles_required("super_admin")
def users():
    user_rows = User.query.order_by(User.id.desc()).limit(240).all()
    role_rows = Role.query.order_by(Role.id.asc()).all()
    user_items = [
        {
            "id": row.id,
            "username": row.username,
            "roles": ", ".join(row.role_names() or []),
            "branch_ids": ", ".join([str(branch_id) for branch_id in row.branch_ids()]),
            "active": "active" if row.is_active else "inactive",
            "tao_luc": _format_datetime(row.created_at),
        }
        for row in user_rows
    ]
    role_items = [{"id": row.id, "ten_role": row.name} for row in role_rows]
    cards = [
        {"label": "Users", "value": _format_number(len(user_items))},
        {"label": "Roles", "value": _format_number(len(role_items))},
    ]
    tables = [
        _module_table(
            title="Tai khoan",
            columns=[
                {"key": "id", "label": "ID"},
                {"key": "username", "label": "Username"},
                {"key": "roles", "label": "Roles"},
                {"key": "branch_ids", "label": "Branch IDs"},
                {"key": "active", "label": "Trang thai"},
                {"key": "tao_luc", "label": "Tao luc"},
            ],
            rows=user_items,
        ),
        _module_table(
            title="Danh muc role",
            columns=[
                {"key": "id", "label": "ID"},
                {"key": "ten_role", "label": "Role"},
            ],
            rows=role_items,
        ),
    ]
    return _render_module_page(
        title="Tai khoan",
        subtitle="Du lieu tu users va roles.",
        cards=cards,
        tables=tables,
    )


@web_bp.get("/branches")
@_roles_required("super_admin")
def branches():
    rows = Branch.query.order_by(Branch.id.asc()).all()
    items = [
        {
            "id": row.id,
            "ten_chi_nhanh": row.name,
            "dia_chi": row.address or "",
            "trang_thai": row.status,
            "gio_lam": row.working_hours_json or "",
        }
        for row in rows
    ]
    cards = [
        {"label": "Tong chi nhanh", "value": _format_number(len(items))},
        {"label": "Dang hoat dong", "value": _format_number(len([row for row in rows if row.status == "active"]))},
    ]
    tables = [
        _module_table(
            title="Danh sach chi nhanh",
            columns=[
                {"key": "id", "label": "ID"},
                {"key": "ten_chi_nhanh", "label": "Ten chi nhanh"},
                {"key": "dia_chi", "label": "Dia chi"},
                {"key": "trang_thai", "label": "Trang thai"},
                {"key": "gio_lam", "label": "Working hours json"},
            ],
            rows=items,
        ),
    ]
    return _render_module_page(
        title="Chi nhanh",
        subtitle="Du lieu tu branches backend.",
        cards=cards,
        tables=tables,
    )


@web_bp.get("/audit-logs")
@_roles_required("super_admin")
def audit_logs():
    rows = AuditLog.query.order_by(AuditLog.id.desc()).limit(300).all()
    items = [
        {
            "id": row.id,
            "user_id": row.user_id if row.user_id is not None else "",
            "branch_id": row.branch_id if row.branch_id is not None else "",
            "action": row.action,
            "entity": row.entity or "",
            "tao_luc": _format_datetime(row.created_at),
        }
        for row in rows
    ]
    cards = [
        {"label": "Tong log", "value": _format_number(len(items))},
    ]
    tables = [
        _module_table(
            title="Nhat ky he thong",
            columns=[
                {"key": "id", "label": "ID"},
                {"key": "user_id", "label": "User ID"},
                {"key": "branch_id", "label": "Branch ID"},
                {"key": "action", "label": "Action"},
                {"key": "entity", "label": "Entity"},
                {"key": "tao_luc", "label": "Tao luc"},
            ],
            rows=items,
        ),
    ]
    return _render_module_page(
        title="Nhat ky he thong",
        subtitle="Du lieu tu audit_logs backend.",
        cards=cards,
        tables=tables,
    )


@web_bp.get("/technician")
@_roles_required("technician", "super_admin", "branch_manager")
def technician():
    branch_id = getattr(g, "web_branch_id", None)
    if branch_id is None:
        return redirect(url_for("web.index"))

    query = (
        db.session.query(Appointment, Customer.full_name, Service.name, Staff.full_name)
        .outerjoin(Customer, Appointment.customer_id == Customer.id)
        .outerjoin(Service, Appointment.service_id == Service.id)
        .outerjoin(Staff, Appointment.staff_id == Staff.id)
        .filter(Appointment.branch_id == branch_id)
    )

    if _is_technician_only(getattr(g, "web_user", None)):
        current_user_id = getattr(g, "web_user", None).id
        staff = Staff.query.filter_by(branch_id=branch_id, user_id=current_user_id).first()
        if staff is None:
            query = query.filter(Appointment.id == -1)
        else:
            query = query.filter(Appointment.staff_id == staff.id)

    appt_rows = query.order_by(Appointment.start_time.desc()).limit(240).all()
    appt_ids = [appointment.id for appointment, *_ in appt_rows]
    note_count = 0
    if appt_ids:
        note_count = (
            db.session.query(func.count(TreatmentNote.id))
            .filter(TreatmentNote.appointment_id.in_(appt_ids))
            .scalar()
        )

    items = [
        {
            "id": appointment.id,
            "khach_hang": customer_name or "",
            "dich_vu": service_name or "",
            "ky_thuat_vien": staff_name or "",
            "bat_dau": _format_datetime(appointment.start_time),
            "ket_thuc": _format_datetime(appointment.end_time),
            "trang_thai": appointment.status,
        }
        for appointment, customer_name, service_name, staff_name in appt_rows
    ]
    cards = [
        {"label": "Lich hen ky thuat vien", "value": _format_number(len(items))},
        {"label": "Treatment notes", "value": _format_number(note_count)},
        {
            "label": "Dang xu ly",
            "value": _format_number(
                len([row for row in items if row["trang_thai"] in {"arrived", "in_service"}])
            ),
        },
    ]
    tables = [
        _module_table(
            title="Cong viec ky thuat vien",
            columns=[
                {"key": "id", "label": "ID"},
                {"key": "khach_hang", "label": "Khach hang"},
                {"key": "dich_vu", "label": "Dich vu"},
                {"key": "ky_thuat_vien", "label": "Ky thuat vien"},
                {"key": "bat_dau", "label": "Bat dau"},
                {"key": "ket_thuc", "label": "Ket thuc"},
                {"key": "trang_thai", "label": "Trang thai"},
            ],
            rows=items,
        ),
    ]
    return _render_module_page(
        title="Ky thuat vien",
        subtitle="Du lieu tu appointments/treatment_notes theo pham vi ky thuat vien.",
        cards=cards,
        tables=tables,
    )
