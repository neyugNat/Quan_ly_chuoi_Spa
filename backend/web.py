from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import wraps
import json
import re
import secrets
from typing import Any

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import and_, case, func
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError

from backend.extensions import db
from backend.models.appointment import Appointment
from backend.models.audit_log import AuditLog
from backend.models.branch import Branch
from backend.models.commission_record import CommissionRecord
from backend.models.customer import Customer
from backend.models.customer_account import CustomerAccount
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
from backend.utils.mailer import send_mail


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
        "label": "Tổng quan",
        "roles": ["super_admin", "branch_manager"],
    },
    {
        "endpoint": "web.branches",
        "path": "/web/branches",
        "label": "Chi nhánh",
        "roles": ["super_admin"],
    },
    {
        "endpoint": "web.pos",
        "path": "/web/pos",
        "label": "POS / Hóa đơn",
        "roles": ["super_admin", "branch_manager", "reception", "cashier"],
    },
    {
        "endpoint": "web.customers",
        "path": "/web/customers",
        "label": "Khách hàng",
        "roles": ["super_admin", "branch_manager", "reception", "cashier"],
    },
    {
        "endpoint": "web.appointments",
        "path": "/web/appointments",
        "label": "Lịch hẹn",
        "roles": ["super_admin", "branch_manager", "reception", "technician"],
    },
    {
        "endpoint": "web.services",
        "path": "/web/services",
        "label": "Dịch vụ",
        "roles": ["super_admin", "branch_manager"],
    },
    {
        "endpoint": "web.packages",
        "path": "/web/packages",
        "label": "Gói liệu trình",
        "roles": ["super_admin", "branch_manager"],
    },
    {
        "endpoint": "web.resources",
        "path": "/web/resources",
        "label": "Tài nguyên",
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
        "label": "Nhân sự",
        "roles": ["super_admin", "branch_manager"],
    },
    {
        "endpoint": "web.reports",
        "path": "/web/reports",
        "label": "Báo cáo",
        "roles": ["super_admin", "branch_manager"],
    },
    {
        "endpoint": "web.users",
        "path": "/web/users",
        "label": "Tài khoản",
        "roles": ["super_admin"],
    },
    {
        "endpoint": "web.audit_logs",
        "path": "/web/audit-logs",
        "label": "Nhật ký hệ thống",
        "roles": ["super_admin"],
    },
    {
        "endpoint": "web.settings",
        "path": "/web/settings",
        "label": "Cài đặt",
        "roles": [
            "super_admin",
            "branch_manager",
            "reception",
            "technician",
            "cashier",
            "warehouse",
        ],
    },
    {
        "endpoint": "web.technician",
        "path": "/web/technician",
        "label": "Kỹ thuật viên",
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


def _normalize_email(value: str | None) -> str:
    return (value or "").strip().lower()


def _set_login_state(*, mode: str = "staff", view: str = "login", token: str | None = None) -> None:
    session["web_login_state"] = {
        "mode": mode,
        "view": view,
        "token": (token or "").strip(),
    }


def _consume_login_state() -> dict[str, str]:
    raw = session.pop("web_login_state", None)
    if not isinstance(raw, dict):
        return {}
    return {
        "mode": str(raw.get("mode") or "").strip().lower(),
        "view": str(raw.get("view") or "").strip().lower(),
        "token": str(raw.get("token") or "").strip(),
    }


def _set_appointment_form_state(payload: dict[str, Any]) -> None:
    session["web_appointments_form_state"] = dict(payload)


def _consume_appointment_form_state() -> dict[str, Any]:
    raw = session.pop("web_appointments_form_state", None)
    if not isinstance(raw, dict):
        return {}
    return dict(raw)


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


def _customer_login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not getattr(g, "web_customer", None):
            target = request.full_path if request.query_string else request.path
            _set_login_state(mode="customer", view="login")
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

    g.web_customer = None
    customer_account_id = _parse_int(session.get("web_customer_account_id"))
    if customer_account_id is not None:
        try:
            customer_account = (
                CustomerAccount.query.filter_by(id=customer_account_id, is_active=True).first()
            )
            if customer_account and customer_account.customer:
                g.web_customer = customer_account
            else:
                session.pop("web_customer_account_id", None)
        except (OperationalError, ProgrammingError):
            session.pop("web_customer_account_id", None)

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
        "web_customer": getattr(g, "web_customer", None),
        "web_roles": _role_names(user),
        "web_nav_items": visible_nav,
        "web_branch_options": branch_options,
        "web_current_branch_id": getattr(g, "web_branch_id", None),
        "web_today_label": datetime.now().strftime("%d/%m/%Y"),
        "fmt_money": _format_money,
        "fmt_number": _format_number,
        "fmt_datetime": _format_datetime,
    }


@web_bp.route("/")
def index():
    user = getattr(g, "web_user", None)
    if user:
        return redirect(_first_allowed_path(user))
    if getattr(g, "web_customer", None):
        return redirect(url_for("web.customer_portal"))
    return redirect(url_for("web.login"))


@web_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        user = getattr(g, "web_user", None)
        if user:
            return redirect(_first_allowed_path(user))
        if getattr(g, "web_customer", None):
            return redirect(url_for("web.customer_portal"))
        login_state = _consume_login_state()
        requested_mode = (request.args.get("mode") or login_state.get("mode") or "").strip().lower()
        requested_view = (request.args.get("view") or login_state.get("view") or "").strip().lower()
        reset_token = (
            request.args.get("token")
            or login_state.get("token")
            or ""
        ).strip()

        mode = requested_mode if requested_mode in {"staff", "customer"} else "staff"
        if mode == "customer":
            if requested_view in {"login", "register", "forgot", "reset"}:
                view = requested_view
            else:
                view = "reset" if reset_token else "login"
        else:
            view = "login"

        return render_template(
            "web/login.html",
            initial_mode=mode,
            initial_view=view,
            reset_token=reset_token,
        )

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    if not username or not password:
        flash("Vui lòng nhập đầy đủ tài khoản và mật khẩu.", "error")
        return render_template(
            "web/login.html",
            initial_mode="staff",
            initial_view="login",
            reset_token="",
        ), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.is_active or not user.verify_password(password):
        flash("Thông tin đăng nhập không đúng.", "error")
        return render_template(
            "web/login.html",
            initial_mode="staff",
            initial_view="login",
            reset_token="",
        ), 401

    session["web_user_id"] = user.id
    session.pop("web_customer_account_id", None)
    session.pop("web_login_state", None)
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
    session.pop("web_customer_account_id", None)
    return redirect(url_for("web.login"))


@web_bp.post("/customer/login")
def customer_login():
    email = _normalize_email(request.form.get("email"))
    password = request.form.get("password") or ""
    if not email or not password:
        flash("Vui lòng nhập đầy đủ email và mật khẩu.", "error")
        _set_login_state(mode="customer", view="login")
        return redirect(url_for("web.login"))

    account = CustomerAccount.query.filter(func.lower(CustomerAccount.email) == email).first()
    if not account or not account.is_active or not account.verify_password(password):
        flash("Thông tin đăng nhập khách hàng không đúng.", "error")
        _set_login_state(mode="customer", view="login")
        return redirect(url_for("web.login"))
    if not account.customer or account.customer.status not in {"active", "vip", "new"}:
        flash("Tài khoản khách hàng chưa hoạt động.", "error")
        _set_login_state(mode="customer", view="login")
        return redirect(url_for("web.login"))

    session["web_customer_account_id"] = account.id
    session.pop("web_user_id", None)
    session.pop("web_branch_id", None)
    session.pop("web_login_state", None)
    next_path = _safe_next(request.form.get("next"))
    return redirect(next_path or url_for("web.customer_portal"))


@web_bp.post("/customer/register")
def customer_register():
    full_name = (request.form.get("full_name") or "").strip()
    email = _normalize_email(request.form.get("email"))
    phone = (request.form.get("phone") or "").strip()
    password = request.form.get("password") or ""
    confirm_password = request.form.get("confirm_password") or ""

    if not full_name or not email or not password:
        flash("Vui lòng nhập đầy đủ họ tên, email và mật khẩu.", "error")
        _set_login_state(mode="customer", view="register")
        return redirect(url_for("web.login"))
    if len(password) < 6:
        flash("Mật khẩu cần tối thiểu 6 ký tự.", "error")
        _set_login_state(mode="customer", view="register")
        return redirect(url_for("web.login"))
    if password != confirm_password:
        flash("Mật khẩu xác nhận không khớp.", "error")
        _set_login_state(mode="customer", view="register")
        return redirect(url_for("web.login"))

    if CustomerAccount.query.filter(func.lower(CustomerAccount.email) == email).first():
        flash("Email đã tồn tại. Vui lòng đăng nhập hoặc đặt lại mật khẩu.", "error")
        _set_login_state(mode="customer", view="login")
        return redirect(url_for("web.login"))

    branch = Branch.query.order_by(Branch.id.asc()).first()
    if branch is None:
        flash("Hệ thống chưa có chi nhánh để tạo tài khoản.", "error")
        _set_login_state(mode="customer", view="register")
        return redirect(url_for("web.login"))

    customer = (
        Customer.query.filter(func.lower(Customer.email) == email)
        .order_by(Customer.id.asc())
        .first()
    )
    if customer is None:
        customer = Customer(
            branch_id=branch.id,
            full_name=full_name,
            phone=phone or f"guest-{datetime.utcnow().strftime('%y%m%d%H%M%S')}",
            email=email,
            status="active",
            marketing_consent=False,
        )
        db.session.add(customer)
        db.session.flush()
    else:
        if not customer.full_name:
            customer.full_name = full_name
        if not customer.phone and phone:
            customer.phone = phone
        if not customer.status:
            customer.status = "active"

    if CustomerAccount.query.filter_by(customer_id=customer.id).first():
        flash("Khách hàng này đã có tài khoản.", "error")
        _set_login_state(mode="customer", view="login")
        return redirect(url_for("web.login"))

    account = CustomerAccount(customer_id=customer.id, email=email, is_active=True)
    account.set_password(password)
    db.session.add(account)

    try:
        send_mail(
            to_email=email,
            subject="Lotus Spa - Tạo tài khoản thành công",
            text_body=(
                f"Xin chào {customer.full_name},\n\n"
                "Tài khoản khách hàng của bạn đã được tạo thành công.\n"
                "Bạn có thể đăng nhập và đặt lịch tại Lotus Spa."
            ),
        )
    except Exception:
        current_app.logger.exception("customer register welcome mail failed (web)")

    db.session.commit()
    flash("Tạo tài khoản thành công. Bạn có thể đăng nhập ngay.", "success")
    _set_login_state(mode="customer", view="login")
    return redirect(url_for("web.login"))


@web_bp.post("/customer/forgot-password")
def customer_forgot_password():
    session.pop("web_customer_account_id", None)
    email = _normalize_email(request.form.get("email"))
    if not email:
        flash("Vui lòng nhập email.", "error")
        _set_login_state(mode="customer", view="forgot")
        return redirect(url_for("web.login"))

    account = CustomerAccount.query.filter(func.lower(CustomerAccount.email) == email).first()
    if not account or not account.is_active:
        flash("Nếu email tồn tại, hệ thống đã gửi hướng dẫn đặt lại mật khẩu.", "success")
        _set_login_state(mode="customer", view="forgot")
        return redirect(url_for("web.login"))

    token = secrets.token_urlsafe(32)
    account.reset_password_token = token
    account.reset_password_expires_at = datetime.utcnow() + timedelta(minutes=30)
    reset_url = url_for("web.login", token=token, _external=True)

    try:
        send_mail(
            to_email=email,
            subject="Lotus Spa - Đặt lại mật khẩu",
            text_body=(
                "Bạn vừa yêu cầu đặt lại mật khẩu.\n\n"
                f"Truy cập link sau để đặt lại mật khẩu (hiệu lực 30 phút):\n{reset_url}"
            ),
        )
    except Exception:
        db.session.rollback()
        current_app.logger.exception("customer forgot-password mail failed (web)")
        flash("Không gửi được email. Vui lòng kiểm tra cấu hình mail.", "error")
        _set_login_state(mode="customer", view="forgot")
        return redirect(url_for("web.login"))

    db.session.commit()
    flash("Nếu email tồn tại, hệ thống đã gửi hướng dẫn đặt lại mật khẩu.", "success")
    if current_app.config.get("MAIL_MODE") == "console":
        flash(f"Dev token: {token}", "info")
    _set_login_state(mode="customer", view="forgot")
    return redirect(url_for("web.login"))


@web_bp.post("/customer/reset-password")
def customer_reset_password():
    session.pop("web_customer_account_id", None)
    token = (request.form.get("token") or "").strip()
    new_password = request.form.get("new_password") or ""
    confirm_password = request.form.get("confirm_password") or ""

    if not token or not new_password:
        flash("Vui lòng nhập token và mật khẩu mới.", "error")
        _set_login_state(mode="customer", view="reset", token=token)
        return redirect(url_for("web.login"))
    if len(new_password) < 6:
        flash("Mật khẩu mới cần tối thiểu 6 ký tự.", "error")
        _set_login_state(mode="customer", view="reset", token=token)
        return redirect(url_for("web.login"))
    if new_password != confirm_password:
        flash("Mật khẩu xác nhận không khớp.", "error")
        _set_login_state(mode="customer", view="reset", token=token)
        return redirect(url_for("web.login"))

    account = CustomerAccount.query.filter_by(reset_password_token=token).first()
    if not account:
        flash("Token không hợp lệ.", "error")
        _set_login_state(mode="customer", view="reset")
        return redirect(url_for("web.login"))

    expires_at = account.reset_password_expires_at
    if not expires_at or expires_at < datetime.utcnow():
        account.reset_password_token = None
        account.reset_password_expires_at = None
        db.session.commit()
        flash("Token đã hết hạn. Vui lòng gửi lại yêu cầu.", "error")
        _set_login_state(mode="customer", view="forgot")
        return redirect(url_for("web.login"))

    account.set_password(new_password)
    account.reset_password_token = None
    account.reset_password_expires_at = None
    db.session.commit()
    flash("Đặt lại mật khẩu thành công. Bạn hãy đăng nhập lại.", "success")
    _set_login_state(mode="customer", view="login")
    return redirect(url_for("web.login"))


@web_bp.post("/customer/logout")
def customer_logout():
    session.pop("web_customer_account_id", None)
    _set_login_state(mode="customer", view="login")
    return redirect(url_for("web.login"))


@web_bp.get("/customer-portal")
@_customer_login_required
def customer_portal():
    account = getattr(g, "web_customer", None)
    customer = account.customer
    now = datetime.utcnow()

    upcoming_rows = (
        db.session.query(Appointment, Service.name, Branch.name)
        .outerjoin(Service, Appointment.service_id == Service.id)
        .outerjoin(Branch, Appointment.branch_id == Branch.id)
        .filter(Appointment.customer_id == customer.id)
        .filter(Appointment.start_time >= now)
        .order_by(Appointment.start_time.asc())
        .limit(12)
        .all()
    )
    history_rows = (
        db.session.query(Appointment, Service.name, Branch.name)
        .outerjoin(Service, Appointment.service_id == Service.id)
        .outerjoin(Branch, Appointment.branch_id == Branch.id)
        .filter(Appointment.customer_id == customer.id)
        .order_by(Appointment.start_time.desc())
        .limit(12)
        .all()
    )

    upcoming_items = [
        {
            "time": _format_datetime(appointment.start_time),
            "service": service_name or "Chua gan",
            "branch": branch_name or f"CN #{appointment.branch_id}",
            "status": appointment.status,
        }
        for appointment, service_name, branch_name in upcoming_rows
    ]
    history_items = [
        {
            "time": _format_datetime(appointment.start_time),
            "service": service_name or "Chua gan",
            "branch": branch_name or f"CN #{appointment.branch_id}",
            "status": appointment.status,
        }
        for appointment, service_name, branch_name in history_rows
    ]

    return render_template(
        "web/customer_portal.html",
        customer=customer,
        account=account,
        upcoming_items=upcoming_items,
        history_items=history_items,
    )


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


@web_bp.get("/settings")
@_roles_required(
    "super_admin",
    "branch_manager",
    "reception",
    "technician",
    "cashier",
    "warehouse",
)
def settings():
    theme_items = [
        {
            "id": "aurora",
            "name": "Aurora",
            "emoji": "🌌",
            "sidebar": "linear-gradient(165deg, #1e1b4b 0%, #312e81 45%, #1e3a8a 100%)",
            "bg": (
                "radial-gradient(ellipse at 0% 0%, rgba(167,139,250,0.25) 0px, transparent 55%), "
                "radial-gradient(ellipse at 100% 0%, rgba(96,165,250,0.2) 0px, transparent 55%), "
                "radial-gradient(ellipse at 50% 100%, rgba(52,211,153,0.15) 0px, transparent 55%), #f3f0ff"
            ),
        },
        {
            "id": "ocean",
            "name": "Đại Dương",
            "emoji": "🌊",
            "sidebar": "linear-gradient(165deg, #0c4a6e 0%, #075985 45%, #1d4ed8 100%)",
            "bg": (
                "radial-gradient(ellipse at 0% 0%, rgba(56,189,248,0.2) 0px, transparent 55%), "
                "radial-gradient(ellipse at 100% 0%, rgba(99,102,241,0.15) 0px, transparent 55%), "
                "radial-gradient(ellipse at 50% 100%, rgba(34,211,238,0.15) 0px, transparent 55%), #eff8ff"
            ),
        },
        {
            "id": "sunset",
            "name": "Hoàng Hôn",
            "emoji": "🌅",
            "sidebar": "linear-gradient(165deg, #4c0519 0%, #7c2d12 40%, #78350f 70%, #713f12 100%)",
            "bg": (
                "radial-gradient(ellipse at 0% 0%, rgba(252,165,50,0.2) 0px, transparent 55%), "
                "radial-gradient(ellipse at 100% 0%, rgba(251,113,133,0.2) 0px, transparent 55%), "
                "radial-gradient(ellipse at 50% 100%, rgba(167,139,250,0.15) 0px, transparent 55%), #fff8f0"
            ),
        },
        {
            "id": "forest",
            "name": "Rừng Xanh",
            "emoji": "🌿",
            "sidebar": "linear-gradient(165deg, #064e3b 0%, #065f46 45%, #134e4a 100%)",
            "bg": (
                "radial-gradient(ellipse at 0% 0%, rgba(52,211,153,0.2) 0px, transparent 55%), "
                "radial-gradient(ellipse at 100% 0%, rgba(56,189,248,0.15) 0px, transparent 55%), "
                "radial-gradient(ellipse at 50% 100%, rgba(167,243,208,0.2) 0px, transparent 55%), #f0fdf6"
            ),
        },
        {
            "id": "rose",
            "name": "Hoa Hồng",
            "emoji": "🌸",
            "sidebar": "linear-gradient(165deg, #500724 0%, #881337 45%, #6b21a8 100%)",
            "bg": (
                "radial-gradient(ellipse at 0% 0%, rgba(251,113,133,0.2) 0px, transparent 55%), "
                "radial-gradient(ellipse at 100% 0%, rgba(167,139,250,0.18) 0px, transparent 55%), "
                "radial-gradient(ellipse at 50% 100%, rgba(252,165,165,0.15) 0px, transparent 55%), #fff0f6"
            ),
        },
    ]
    wallpaper_items = [
        {"id": "none", "name": "Không có", "style": "background: #f9fafb; border: 1px dashed #d1d5db;"},
        {"id": "gradient1", "name": "Bình Minh", "style": "background: linear-gradient(135deg, #f093fb 0%, #f5576c 50%, #4facfe 100%);"},
        {"id": "gradient2", "name": "Xanh Biển", "style": "background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);"},
        {"id": "gradient3", "name": "Cánh Đồng", "style": "background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);"},
        {"id": "gradient4", "name": "Hoàng Kim", "style": "background: linear-gradient(135deg, #f7971e 0%, #ffd200 100%);"},
        {"id": "gradient5", "name": "Mây Hồng", "style": "background: linear-gradient(135deg, #ee9ca7 0%, #ffdde1 100%);"},
        {
            "id": "mesh1",
            "name": "Aurora Mesh",
            "style": (
                "background: radial-gradient(at 40% 20%, hsla(28,100%,74%,1) 0px, transparent 50%), "
                "radial-gradient(at 80% 0%, hsla(189,100%,56%,1) 0px, transparent 50%), "
                "radial-gradient(at 0% 50%, hsla(355,100%,93%,1) 0px, transparent 50%), "
                "radial-gradient(at 80% 50%, hsla(340,100%,76%,1) 0px, transparent 50%), "
                "radial-gradient(at 0% 100%, hsla(22,100%,77%,1) 0px, transparent 50%), "
                "radial-gradient(at 80% 100%, hsla(242,100%,70%,1) 0px, transparent 50%), "
                "radial-gradient(at 0% 0%, hsla(343,100%,76%,1) 0px, transparent 50%);"
            ),
        },
        {
            "id": "mesh2",
            "name": "Cosmic",
            "style": (
                "background: radial-gradient(at 40% 20%, hsla(260,100%,70%,1) 0px, transparent 50%), "
                "radial-gradient(at 80% 0%, hsla(220,100%,56%,1) 0px, transparent 50%), "
                "radial-gradient(at 0% 50%, hsla(290,100%,60%,1) 0px, transparent 50%), "
                "radial-gradient(at 80% 50%, hsla(200,100%,70%,1) 0px, transparent 50%), "
                "radial-gradient(at 0% 100%, hsla(250,100%,65%,1) 0px, transparent 50%);"
            ),
        },
    ]
    language_items = [
        {"id": "vi", "name": "Tiếng Việt", "flag": "🇻🇳"},
        {"id": "en", "name": "English", "flag": "🇬🇧"},
        {"id": "zh", "name": "中文", "flag": "🇨🇳"},
        {"id": "ja", "name": "日本語", "flag": "🇯🇵"},
    ]
    allowed_sections = {
        "appearance",
        "language",
        "notifications",
        "display",
        "account",
        "security",
        "data",
    }
    current_section = (request.args.get("section") or "appearance").strip().lower()
    if current_section not in allowed_sections:
        current_section = "appearance"

    user = getattr(g, "web_user", None)
    role_aliases = {
        "super_admin": "Super Admin",
        "branch_manager": "Quản lý chi nhánh",
        "reception": "Lễ tân",
        "technician": "Kỹ thuật viên",
        "cashier": "Thu ngân",
        "warehouse": "Kho",
    }
    role_name = user.role_names()[0] if user and user.role_names() else "user"
    account_profile = {
        "username": user.username if user else "",
        "full_name": "Nguyễn Văn Admin",
        "role": role_aliases.get(role_name, role_name.replace("_", " ").title()),
        "email": (getattr(user, "email", None) or f"{user.username}@lotusspa.vn") if user else "admin@lotusspa.vn",
        "phone": "0901234567",
        "title": "Giám đốc vận hành",
    }

    return render_template(
        "web/settings.html",
        page_title="Cài đặt",
        page_subtitle="Tuỳ chỉnh giao diện, ngôn ngữ và hệ thống",
        current_section=current_section,
        theme_items=theme_items,
        wallpaper_items=wallpaper_items,
        language_items=language_items,
        account_profile=account_profile,
    )


@web_bp.post("/settings/change-password")
@_roles_required(
    "super_admin",
    "branch_manager",
    "reception",
    "technician",
    "cashier",
    "warehouse",
)
def settings_change_password():
    user = getattr(g, "web_user", None)
    old_password = request.form.get("old_password") or ""
    new_password = request.form.get("new_password") or ""
    confirm_password = request.form.get("confirm_password") or ""

    if not old_password or not new_password or not confirm_password:
        flash("Vui lòng nhập đầy đủ thông tin mật khẩu.", "error")
        return redirect(url_for("web.settings", section="security"))

    if len(new_password) < 6:
        flash("Mật khẩu mới cần tối thiểu 6 ký tự.", "error")
        return redirect(url_for("web.settings", section="security"))

    if new_password != confirm_password:
        flash("Mật khẩu xác nhận không khớp.", "error")
        return redirect(url_for("web.settings", section="security"))

    if not user or not user.verify_password(old_password):
        flash("Mật khẩu hiện tại không đúng.", "error")
        return redirect(url_for("web.settings", section="security"))

    user.set_password(new_password)
    db.session.add(
        AuditLog(
            user_id=user.id,
            branch_id=getattr(g, "web_branch_id", None),
            action="web.settings.change_password",
            entity="User",
            before_json=AuditLog.dumps({"user_id": user.id}),
            after_json=AuditLog.dumps({"user_id": user.id}),
        )
    )
    db.session.commit()

    flash("Cập nhật mật khẩu thành công.", "success")
    return redirect(url_for("web.settings", section="security"))


@web_bp.get("/dashboard")
@_roles_required("super_admin", "branch_manager")
def dashboard():
    branch_id = getattr(g, "web_branch_id", None)
    if branch_id is None:
        flash("Tai khoan khong duoc gan chi nhanh.", "error")
        return redirect(url_for("web.login"))

    today = date.today()
    tomorrow = today + timedelta(days=1)
    yesterday = today - timedelta(days=1)

    def _trend_from_pair(current_value: float, previous_value: float) -> tuple[str, bool]:
        current_value = float(current_value or 0)
        previous_value = float(previous_value or 0)
        if previous_value <= 0:
            if current_value <= 0:
                return "+0.0%", True
            return "+100.0%", True
        pct = ((current_value - previous_value) / previous_value) * 100
        return f"{pct:+.1f}%", pct >= 0

    month_start = date(today.year, today.month, 1)
    if today.month == 12:
        next_month_start = date(today.year + 1, 1, 1)
    else:
        next_month_start = date(today.year, today.month + 1, 1)

    if today.month == 1:
        prev_month_start = date(today.year - 1, 12, 1)
    else:
        prev_month_start = date(today.year, today.month - 1, 1)

    month_start_dt = datetime.combine(month_start, datetime.min.time())
    next_month_start_dt = datetime.combine(next_month_start, datetime.min.time())
    prev_month_start_dt = datetime.combine(prev_month_start, datetime.min.time())

    yesterday_start_dt = datetime.combine(yesterday, datetime.min.time())
    today_start_dt = datetime.combine(today, datetime.min.time())

    revenue_total = (
        db.session.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.branch_id == branch_id,
            Payment.status == "posted",
        )
        .scalar()
    )
    current_month_revenue = (
        db.session.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.branch_id == branch_id,
            Payment.status == "posted",
            Payment.paid_at >= month_start_dt,
            Payment.paid_at < next_month_start_dt,
        )
        .scalar()
    )
    previous_month_revenue = (
        db.session.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.branch_id == branch_id,
            Payment.status == "posted",
            Payment.paid_at >= prev_month_start_dt,
            Payment.paid_at < month_start_dt,
        )
        .scalar()
    )

    two_weeks_start = datetime.combine(today, datetime.min.time()) - timedelta(days=13)
    previous_two_weeks_start = two_weeks_start - timedelta(days=14)
    new_customer_2w_count = (
        db.session.query(func.count(Customer.id))
        .filter(
            Customer.branch_id == branch_id,
            Customer.created_at >= two_weeks_start,
        )
        .scalar()
    )
    previous_new_customer_2w_count = (
        db.session.query(func.count(Customer.id))
        .filter(
            Customer.branch_id == branch_id,
            Customer.created_at >= previous_two_weeks_start,
            Customer.created_at < two_weeks_start,
        )
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
    appointment_totals = {
        str((status or "unknown")).lower(): int(total or 0)
        for status, total in status_rows
    }
    appointments_total = sum(appointment_totals.values())
    appointments_cancelled = (
        appointment_totals.get("cancelled", 0) + appointment_totals.get("no_show", 0)
    )
    cancel_rate = (appointments_cancelled / appointments_total * 100.0) if appointments_total else 0.0

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

    today_report_count = (
        db.session.query(func.count(Appointment.id))
        .filter(
            Appointment.branch_id == branch_id,
            Appointment.start_time >= datetime.combine(today, datetime.min.time()),
            Appointment.start_time < datetime.combine(tomorrow, datetime.min.time()),
        )
        .scalar()
    )

    appointment_rows = (
        db.session.query(Appointment, Customer.full_name, Service.name, Branch.name)
        .outerjoin(Customer, Appointment.customer_id == Customer.id)
        .outerjoin(Service, Appointment.service_id == Service.id)
        .outerjoin(Branch, Appointment.branch_id == Branch.id)
        .filter(
            Appointment.branch_id == branch_id,
            Appointment.start_time >= datetime.combine(today, datetime.min.time()),
            Appointment.start_time < datetime.combine(tomorrow, datetime.min.time()),
        )
        .order_by(Appointment.start_time.asc(), Appointment.id.asc())
        .limit(5)
        .all()
    )

    status_meta = {
        "booked": {"label": "Da dat", "icon": "calendar"},
        "confirmed": {"label": "Xac nhan", "icon": "check"},
        "arrived": {"label": "Da den", "icon": "check"},
        "in_service": {"label": "Dang lam", "icon": "activity"},
        "completed": {"label": "Hoan thanh", "icon": "check"},
        "paid": {"label": "Da thanh toan", "icon": "money"},
        "pending": {"label": "Cho xu ly", "icon": "alert"},
        "cancelled": {"label": "Da huy", "icon": "x"},
        "no_show": {"label": "Khong den", "icon": "x"},
    }
    today_appointments = [
        {
            "id": appointment.id,
            "time": appointment.start_time.strftime("%H:%M") if appointment.start_time else "",
            "customer": customer_name or f"Khach #{appointment.customer_id}",
            "service": service_name or "Chua gan",
            "branch": branch_name or f"CN #{appointment.branch_id}",
            "status_key": str((appointment.status or "booked")).lower(),
            "status_label": status_meta.get(
                str((appointment.status or "booked")).lower(),
                {"label": "Da dat", "icon": "calendar"},
            )["label"],
            "status_icon": status_meta.get(
                str((appointment.status or "booked")).lower(),
                {"label": "Da dat", "icon": "calendar"},
            )["icon"],
        }
        for appointment, customer_name, service_name, branch_name in appointment_rows
    ]
    yesterday_appointment_count = (
        db.session.query(func.count(Appointment.id))
        .filter(
            Appointment.branch_id == branch_id,
            Appointment.start_time >= yesterday_start_dt,
            Appointment.start_time < today_start_dt,
        )
        .scalar()
    )

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
    if not branch_performance:
        current_branch = Branch.query.filter_by(id=branch_id).first()
        branch_performance = [
            {
                "branch": current_branch.name if current_branch else f"CN #{branch_id}",
                "revenue": float(revenue_total or 0),
            }
        ]

    staff_total = (
        db.session.query(func.count(Staff.id))
        .filter(Staff.branch_id == branch_id)
        .scalar()
    )
    active_staff_count = (
        db.session.query(func.count(Staff.id))
        .filter(Staff.branch_id == branch_id, Staff.status == "active")
        .scalar()
    )
    service_total = (
        db.session.query(func.count(Service.id))
        .filter(Service.branch_id == branch_id)
        .scalar()
    )
    active_service_count = (
        db.session.query(func.count(Service.id))
        .filter(Service.branch_id == branch_id, Service.status == "active")
        .scalar()
    )

    user = getattr(g, "web_user", None)
    if _has_roles(user, ["super_admin"]):
        branch_total = db.session.query(func.count(Branch.id)).scalar()
        branch_subtitle = "Dang hoat dong" if branch_total else "Theo chi nhanh hien tai"
    else:
        branch_total = len(_allowed_branch_ids(user)) or 1
        branch_subtitle = "Theo chi nhanh hien tai"

    max_branch_revenue = max((row["revenue"] for row in branch_performance), default=0)
    branch_chart = []
    for row in branch_performance[:5]:
        revenue = float(row.get("revenue") or 0)
        if max_branch_revenue > 0:
            pct = max(8, int((revenue / max_branch_revenue) * 100))
        else:
            pct = 0
        branch_chart.append(
            {
                "branch": row.get("branch") or "Khong xac dinh",
                "revenue_m": _format_number(round(revenue / 1_000_000, 1)),
                "pct": pct,
            }
        )

    month_key = func.strftime("%m", Payment.paid_at)
    monthly_rows = (
        db.session.query(
            month_key.label("month"),
            func.coalesce(func.sum(Payment.amount), 0).label("revenue"),
        )
        .filter(
            Payment.branch_id == branch_id,
            Payment.status == "posted",
            Payment.paid_at >= datetime(today.year, 1, 1),
            Payment.paid_at < datetime(today.year + 1, 1, 1),
        )
        .group_by(month_key)
        .all()
    )
    monthly_revenue_map = {
        int(month or 0): float(revenue or 0)
        for month, revenue in monthly_rows
    }
    monthly_revenue = [
        round(monthly_revenue_map.get(month_index, 0) / 1_000_000, 1)
        for month_index in range(1, 13)
    ]
    if max(monthly_revenue, default=0) <= 0 and revenue_series:
        fallback_values = [round(item["revenue"] / 1_000_000, 1) for item in revenue_series[-12:]]
        while len(fallback_values) < 12:
            fallback_values.insert(0, 0.0)
        monthly_revenue = fallback_values[-12:]

    monthly_target = [round(value * 1.08, 1) for value in monthly_revenue]

    chart_width = 760
    chart_height = 240
    chart_left = 32
    chart_right = 16
    chart_top = 18
    chart_bottom = 38
    chart_inner_width = chart_width - chart_left - chart_right
    chart_inner_height = chart_height - chart_top - chart_bottom
    chart_max = max(monthly_revenue + monthly_target + [1.0])

    def _line_points(values: list[float]) -> list[tuple[float, float]]:
        if not values:
            return []
        if len(values) == 1:
            return [(float(chart_left), float(chart_top + chart_inner_height))]
        step = chart_inner_width / (len(values) - 1)
        points: list[tuple[float, float]] = []
        for index, value in enumerate(values):
            x = chart_left + (step * index)
            y = chart_top + chart_inner_height - ((float(value or 0) / chart_max) * chart_inner_height)
            points.append((round(x, 1), round(y, 1)))
        return points

    revenue_points_xy = _line_points(monthly_revenue)
    target_points_xy = _line_points(monthly_target)
    revenue_polyline_points = " ".join(f"{x},{y}" for x, y in revenue_points_xy)
    target_polyline_points = " ".join(f"{x},{y}" for x, y in target_points_xy)
    baseline_y = chart_height - chart_bottom
    revenue_area_points = ""
    target_area_points = ""
    if revenue_points_xy:
        revenue_area_points = (
            f"{revenue_polyline_points} "
            f"{revenue_points_xy[-1][0]},{baseline_y} "
            f"{revenue_points_xy[0][0]},{baseline_y}"
        )
    if target_points_xy:
        target_area_points = (
            f"{target_polyline_points} "
            f"{target_points_xy[-1][0]},{baseline_y} "
            f"{target_points_xy[0][0]},{baseline_y}"
        )

    revenue_month_labels = [
        {"label": f"T{index + 1}", "x": point[0]}
        for index, point in enumerate(revenue_points_xy)
    ]
    revenue_chart_grid = []
    for ratio in [0.0, 0.25, 0.5, 0.75, 1.0]:
        y = chart_top + (chart_inner_height * ratio)
        label_value = int(round((1 - ratio) * chart_max))
        revenue_chart_grid.append({"y": round(y, 1), "label": label_value})

    chart_hit_width = round(
        chart_inner_width / max(1, len(monthly_revenue) - 1),
        1,
    )
    revenue_chart_data = []
    for index, revenue_value in enumerate(monthly_revenue):
        month_label = f"T{index + 1}"
        target_value = float(monthly_target[index] if index < len(monthly_target) else 0)
        actual_point = (
            revenue_points_xy[index] if index < len(revenue_points_xy) else (chart_left, baseline_y)
        )
        target_point = (
            target_points_xy[index] if index < len(target_points_xy) else (chart_left, baseline_y)
        )
        revenue_chart_data.append(
            {
                "month": month_label,
                "revenue": round(float(revenue_value or 0), 1),
                "target": round(target_value, 1),
                "x": float(actual_point[0]),
                "actual_y": float(actual_point[1]),
                "target_y": float(target_point[1]),
            }
        )

    service_palette = ["#2563eb", "#0ea5e9", "#6366f1", "#06b6d4"]
    service_distribution = []
    seed_services = top_services[:4]
    total_service_revenue = sum(float(item.get("revenue") or 0) for item in seed_services)
    if seed_services and total_service_revenue > 0:
        for index, item in enumerate(seed_services):
            pct = round((float(item.get("revenue") or 0) / total_service_revenue) * 100, 1)
            service_distribution.append(
                {
                    "name": item.get("name") or "Dich vu",
                    "pct": pct,
                    "color": service_palette[index % len(service_palette)],
                }
            )
    else:
        service_distribution = [
            {"name": "Massage", "pct": 35.0, "color": service_palette[0]},
            {"name": "Cham soc da", "pct": 28.0, "color": service_palette[1]},
            {"name": "Nail & Toc", "pct": 20.0, "color": service_palette[2]},
            {"name": "Xong hoi", "pct": 17.0, "color": service_palette[3]},
        ]

    total_pct = round(sum(float(item["pct"]) for item in service_distribution), 1)
    if service_distribution:
        service_distribution[0]["pct"] = round(float(service_distribution[0]["pct"]) + (100.0 - total_pct), 1)

    donut_parts = []
    donut_start = 0.0
    for item in service_distribution:
        pct = max(0.1, float(item["pct"]))
        donut_end = donut_start + pct
        item["pct_text"] = f"{pct:.1f}%".replace(".0%", "%")
        donut_parts.append(f"{item['color']} {donut_start:.1f}% {donut_end:.1f}%")
        donut_start = donut_end
    service_donut_gradient = "conic-gradient(" + ", ".join(donut_parts) + ")"

    revenue_trend_text, revenue_trend_up = _trend_from_pair(current_month_revenue, previous_month_revenue)
    appointment_trend_text, appointment_trend_up = _trend_from_pair(today_report_count, yesterday_appointment_count)
    new_customer_trend_text, new_customer_trend_up = _trend_from_pair(
        new_customer_2w_count,
        previous_new_customer_2w_count,
    )

    low_stock_count = len(low_stock_rows)
    if low_stock_count > 0:
        low_stock_trend_text = f"{low_stock_count} canh bao"
        low_stock_trend_up = False
    else:
        low_stock_trend_text = "On dinh"
        low_stock_trend_up = True

    stats = [
        {
            "label": "Doanh thu",
            "value": f"{_format_number(revenue_total)}d",
            "trend_text": revenue_trend_text,
            "trend_up": revenue_trend_up,
            "icon": "money",
            "icon_class": "money",
        },
        {
            "label": "Lich hen hom nay",
            "value": _format_number(today_report_count),
            "trend_text": appointment_trend_text,
            "trend_up": appointment_trend_up,
            "icon": "calendar",
            "icon_class": "calendar",
        },
        {
            "label": "Luot khach hang moi (2 tuan)",
            "value": _format_number(new_customer_2w_count),
            "trend_text": new_customer_trend_text,
            "trend_up": new_customer_trend_up,
            "icon": "users",
            "icon_class": "customers",
        },
        {
            "label": "Hang sap het",
            "value": _format_number(low_stock_count),
            "trend_text": low_stock_trend_text,
            "trend_up": low_stock_trend_up,
            "icon": "alert",
            "icon_class": "alert",
        },
    ]

    quick_stats = [
        {
            "label": "Tong chi nhanh",
            "value": _format_number(branch_total),
            "sub": branch_subtitle,
            "icon": "branches",
        },
        {
            "label": "Nhan vien",
            "value": _format_number(staff_total),
            "sub": f"{_format_number(active_staff_count)} dang hoat dong",
            "icon": "staff",
        },
        {
            "label": "Dich vu",
            "value": _format_number(service_total),
            "sub": f"{_format_number(active_service_count)} dang hoat dong",
            "icon": "services",
        },
        {
            "label": "Ti le huy",
            "value": f"{cancel_rate:.1f}%",
            "sub": f"{appointments_cancelled}/{appointments_total} lich",
            "icon": "cancel",
        },
    ]

    return render_template(
        "web/dashboard.html",
        stats=stats,
        quick_stats=quick_stats,
        revenue_chart_year=today.year,
        revenue_polyline_points=revenue_polyline_points,
        target_polyline_points=target_polyline_points,
        revenue_area_points=revenue_area_points,
        target_area_points=target_area_points,
        revenue_month_labels=revenue_month_labels,
        revenue_chart_grid=revenue_chart_grid,
        revenue_chart_data=revenue_chart_data,
        chart_hit_width=chart_hit_width,
        service_distribution=service_distribution,
        service_donut_gradient=service_donut_gradient,
        branch_chart=branch_chart,
        today_label=today.strftime("%d/%m/%Y"),
        today_report_count=today_report_count,
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
        .limit(260)
        .all()
    )
    customer_ids = [row.id for row in customer_rows]

    visit_by_customer: dict[int, int] = {}
    last_visit_by_customer: dict[int, datetime] = {}
    spent_by_customer: dict[int, float] = {}
    history_by_customer: dict[int, list[dict[str, Any]]] = {}
    package_price_by_customer: dict[tuple[int, int], float] = {}

    if customer_ids:
        appointment_rows = (
            db.session.query(Appointment.customer_id, Appointment.start_time)
            .filter(
                Appointment.branch_id == branch_id,
                Appointment.customer_id.isnot(None),
                Appointment.customer_id.in_(customer_ids),
            )
            .all()
        )
        for customer_id, start_time in appointment_rows:
            parsed_customer_id = _parse_int(customer_id)
            if parsed_customer_id is None:
                continue
            visit_by_customer[parsed_customer_id] = visit_by_customer.get(parsed_customer_id, 0) + 1
            if start_time:
                current_latest = last_visit_by_customer.get(parsed_customer_id)
                if current_latest is None or start_time > current_latest:
                    last_visit_by_customer[parsed_customer_id] = start_time

        invoice_rows = (
            db.session.query(Invoice.customer_id, Invoice.total_amount)
            .filter(
                Invoice.branch_id == branch_id,
                Invoice.customer_id.isnot(None),
                Invoice.customer_id.in_(customer_ids),
            )
            .all()
        )
        for customer_id, total_amount in invoice_rows:
            parsed_customer_id = _parse_int(customer_id)
            if parsed_customer_id is None:
                continue
            spent_by_customer[parsed_customer_id] = (
                spent_by_customer.get(parsed_customer_id, 0.0) + float(total_amount or 0)
            )

        service_name_by_id = {
            int(row.id): ((row.name or "").strip() or f"Dịch vụ #{row.id}")
            for row in Service.query.filter(Service.branch_id == branch_id).all()
        }
        package_name_by_id = {
            int(row.id): ((row.name or "").strip() or f"Gói #{row.id}")
            for row in Package.query.filter(Package.branch_id == branch_id).all()
        }

        invoice_history_rows = (
            Invoice.query.filter(
                Invoice.branch_id == branch_id,
                Invoice.customer_id.isnot(None),
                Invoice.customer_id.in_(customer_ids),
            )
            .order_by(Invoice.created_at.desc(), Invoice.id.desc())
            .limit(1200)
            .all()
        )

        for invoice in invoice_history_rows:
            parsed_customer_id = _parse_int(invoice.customer_id)
            if parsed_customer_id is None:
                continue

            history_time = invoice.created_at or invoice.updated_at
            history_time_display = _format_datetime(history_time)

            def _safe_amount(value: Any) -> float:
                try:
                    return float(value or 0)
                except (TypeError, ValueError):
                    return 0.0

            line_items: list[dict[str, Any]] = []
            raw_line_items = (invoice.line_items_json or "").strip()
            if raw_line_items:
                try:
                    parsed_line_items = json.loads(raw_line_items)
                    if isinstance(parsed_line_items, list):
                        line_items = [item for item in parsed_line_items if isinstance(item, dict)]
                except (TypeError, ValueError, json.JSONDecodeError):
                    line_items = []

            if not line_items:
                history_by_customer.setdefault(parsed_customer_id, []).append(
                    {
                        "title": f"Hóa đơn #{invoice.id}",
                        "time": history_time_display or "-",
                        "price": _format_money(invoice.total_amount),
                        "sort_at": history_time,
                    }
                )
                continue

            for item in line_items:
                item_type = str(item.get("type") or "").strip().lower()
                service_id = _parse_int(item.get("service_id"))
                package_id = _parse_int(item.get("package_id"))
                qty = _parse_int(item.get("qty")) or 1
                unit_price = _safe_amount(item.get("unit_price"))
                amount = _safe_amount(item.get("amount")) or (unit_price * max(qty, 1))
                if amount <= 0:
                    amount = _safe_amount(invoice.total_amount)

                if item_type == "package":
                    title = package_name_by_id.get(package_id or -1) or f"Gói #{package_id or '?'}"
                    if package_id is not None:
                        package_price_by_customer[(parsed_customer_id, package_id)] = amount
                elif item_type == "service":
                    title = service_name_by_id.get(service_id or -1) or f"Dịch vụ #{service_id or '?'}"
                else:
                    title = (
                        (str(item.get("name") or "").strip())
                        or package_name_by_id.get(package_id or -1)
                        or service_name_by_id.get(service_id or -1)
                        or f"Hạng mục #{invoice.id}"
                    )

                history_by_customer.setdefault(parsed_customer_id, []).append(
                    {
                        "title": title,
                        "time": history_time_display or "-",
                        "price": _format_money(amount),
                        "sort_at": history_time,
                    }
                )

        customer_package_rows = (
            db.session.query(CustomerPackage)
            .filter(
                CustomerPackage.branch_id == branch_id,
                CustomerPackage.customer_id.in_(customer_ids),
            )
            .order_by(CustomerPackage.created_at.desc(), CustomerPackage.id.desc())
            .limit(800)
            .all()
        )
        for customer_package in customer_package_rows:
            parsed_customer_id = _parse_int(customer_package.customer_id)
            parsed_package_id = _parse_int(customer_package.package_id)
            if parsed_customer_id is None or parsed_package_id is None:
                continue

            package_key = (parsed_customer_id, parsed_package_id)
            if package_key in package_price_by_customer:
                continue

            package_title = package_name_by_id.get(parsed_package_id) or f"Gói #{parsed_package_id}"
            history_time = customer_package.created_at or customer_package.updated_at
            history_by_customer.setdefault(parsed_customer_id, []).append(
                {
                    "title": package_title,
                    "time": _format_datetime(history_time) or "-",
                    "price": "-",
                    "sort_at": history_time,
                }
            )

    def _to_tier(total_spent: float) -> str:
        if total_spent >= 20_000_000:
            return "vip"
        if total_spent >= 10_000_000:
            return "gold"
        if total_spent >= 5_000_000:
            return "silver"
        return "member"

    def _to_rating(visits: int) -> int:
        if visits >= 20:
            return 5
        if visits >= 8:
            return 4
        return 3

    def _to_dob_display(raw_dob: Any) -> str:
        dob_text = str(raw_dob or "").strip()
        if not dob_text:
            return "-"
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(dob_text, fmt).strftime("%d/%m/%Y")
            except ValueError:
                continue
        return dob_text

    customer_items: list[dict[str, Any]] = []
    customer_detail_map: dict[str, dict[str, str]] = {}
    customer_history_map: dict[str, list[dict[str, str]]] = {}
    for row in customer_rows:
        customer_id = row.id
        display_name = (row.full_name or "").strip() or f"Khách #{customer_id}"
        phone = (row.phone or "").strip() or "-"
        email = (row.email or "").strip() or "-"
        note = (row.note or "").strip() or "-"
        dob_display = _to_dob_display(row.dob)
        visits = int(visit_by_customer.get(customer_id, 0))
        total_spent = float(spent_by_customer.get(customer_id, 0.0))
        created_at = row.created_at
        joined = created_at.strftime("%d/%m/%Y") if created_at else "-"
        joined_month = created_at.strftime("%Y-%m") if created_at else ""

        last_visit_dt = last_visit_by_customer.get(customer_id)
        last_visit = last_visit_dt.strftime("%d/%m/%Y") if last_visit_dt else "Chưa có"

        raw_history_rows = history_by_customer.get(customer_id, [])
        sorted_history_rows = sorted(
            raw_history_rows,
            key=lambda item: item.get("sort_at") or datetime.min,
            reverse=True,
        )
        customer_history_map[str(customer_id)] = [
            {
                "title": str(item.get("title") or "-"),
                "time": str(item.get("time") or "-"),
                "price": str(item.get("price") or "-"),
            }
            for item in sorted_history_rows[:40]
        ]
        customer_detail_map[str(customer_id)] = {
            "name": display_name,
            "dob": dob_display,
            "phone": phone,
            "email": email,
            "note": note,
        }

        customer_items.append(
            {
                "id": customer_id,
                "name": display_name,
                "name_initial": display_name[0].upper() if display_name else "K",
                "phone": phone,
                "dob_display": dob_display,
                "email": email,
                "note": note,
                "joined": joined,
                "joined_month": joined_month,
                "visits": visits,
                "total_spent_display": _format_number(total_spent),
                "last_visit": last_visit,
                "tier": _to_tier(total_spent),
                "rating": _to_rating(visits),
            }
        )

    month_key = date.today().strftime("%Y-%m")
    summary = {
        "total_customers": len(customer_items),
        "vip_customers": len([item for item in customer_items if item["tier"] == "vip"]),
        "gold_customers": len([item for item in customer_items if item["tier"] == "gold"]),
        "new_this_month": len(
            [item for item in customer_items if item.get("joined_month", "").startswith(month_key)]
        ),
    }

    return render_template(
        "web/customers.html",
        page_title="Khách hàng",
        page_subtitle="Quản lý hồ sơ và hành trình khách hàng",
        customers=customer_items,
        customer_detail_map=customer_detail_map,
        customer_history_map=customer_history_map,
        summary=summary,
        tier_filters=["Tất cả", "VIP", "Vàng", "Bạc", "Thành viên"],
    )


@web_bp.post("/customers/create")
@_roles_required("super_admin", "branch_manager", "reception", "cashier")
def customers_create():
    branch_id = getattr(g, "web_branch_id", None)
    if branch_id is None:
        return redirect(url_for("web.index"))

    full_name = (request.form.get("full_name") or "").strip()
    phone = (request.form.get("phone") or "").strip()
    email = (request.form.get("email") or "").strip() or None
    dob = (request.form.get("dob") or "").strip() or None
    note = (request.form.get("note") or "").strip() or None

    if not full_name or not phone:
        flash("Vui lòng nhập họ tên và số điện thoại.", "error")
        return redirect(url_for("web.customers"))

    existing_phone = (
        Customer.query.filter(Customer.branch_id == branch_id, Customer.phone == phone)
        .order_by(Customer.id.asc())
        .first()
    )
    if existing_phone:
        flash("Số điện thoại đã tồn tại trong chi nhánh hiện tại.", "error")
        return redirect(url_for("web.customers"))

    if email:
        existing_email = (
            Customer.query.filter(
                Customer.branch_id == branch_id,
                func.lower(Customer.email) == email.lower(),
            )
            .order_by(Customer.id.asc())
            .first()
        )
        if existing_email:
            flash("Email đã tồn tại trong chi nhánh hiện tại.", "error")
            return redirect(url_for("web.customers"))

    customer = Customer(
        branch_id=branch_id,
        full_name=full_name,
        phone=phone,
        email=email,
        dob=dob,
        note=note,
        status="active",
    )
    db.session.add(customer)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Không thể thêm khách hàng. Vui lòng thử lại.", "error")
        return redirect(url_for("web.customers"))

    flash("Đã thêm khách hàng mới.", "success")
    return redirect(url_for("web.customers"))


@web_bp.get("/appointments")
@_roles_required("super_admin", "branch_manager", "reception", "technician")
def appointments():
    branch_id = getattr(g, "web_branch_id", None)
    if branch_id is None:
        return redirect(url_for("web.index"))

    def _to_ui_status(raw_status: str | None) -> tuple[str, str]:
        status_value = str(raw_status or "").strip().lower()
        if status_value in {"booked", "confirmed"}:
            return "confirmed", "Xác nhận"
        if status_value in {"arrived", "in_service"}:
            return "pending", "Chờ xử lý"
        if status_value in {"cancelled", "no_show"}:
            return "cancelled", "Đã hủy"
        if status_value in {"completed", "paid"}:
            return "completed", "Hoàn thành"
        return "pending", "Chờ xử lý"

    query = (
        db.session.query(
            Appointment,
            Customer.full_name,
            Customer.phone,
            Customer.dob,
            Service.name,
            Service.price,
            Service.duration_minutes,
            Staff.full_name,
            Branch.name,
        )
        .outerjoin(Customer, Appointment.customer_id == Customer.id)
        .outerjoin(Service, Appointment.service_id == Service.id)
        .outerjoin(Staff, Appointment.staff_id == Staff.id)
        .outerjoin(Branch, Appointment.branch_id == Branch.id)
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

    avatar_classes = ["avatar-a", "avatar-b", "avatar-c", "avatar-d", "avatar-e"]
    appointment_items: list[dict[str, Any]] = []
    for idx, (appointment, customer_name, customer_phone, customer_dob, service_name, service_price, service_duration, staff_name, branch_name) in enumerate(appt_rows):
        status_key, status_label = _to_ui_status(appointment.status)
        customer_display = (customer_name or "").strip() or f"Khách #{appointment.customer_id}"
        service_display = (service_name or "").strip() or "Chưa gán dịch vụ"
        phone_display = (customer_phone or "").strip() or "-"
        branch_display = (branch_name or "").strip() or f"CN #{appointment.branch_id}"
        staff_display = (staff_name or "").strip() or "Chưa phân công"
        start_time = appointment.start_time
        dob_text = str(customer_dob or "").strip()
        dob_match = re.search(r"(19|20)\d{2}", dob_text)
        dob_year = dob_match.group(0) if dob_match else "----"

        appointment_items.append(
            {
                "id": appointment.id,
                "customer": customer_display,
                "customer_initial": customer_display[:1].upper() if customer_display else "K",
                "avatar_class": avatar_classes[idx % len(avatar_classes)],
                "phone": phone_display,
                "dob_year": dob_year,
                "service": service_display,
                "service_duration": int(service_duration or 0),
                "time": start_time.strftime("%H:%M") if start_time else "--:--",
                "date": start_time.strftime("%d/%m/%Y") if start_time else "-",
                "branch": branch_display,
                "staff": staff_display,
                "price_display": _format_money(service_price or 0),
                "status_key": status_key,
                "status_label": status_label,
                "search_text": f"{customer_display} {service_display} {phone_display}".lower(),
            }
        )

    branch_filters = sorted({item["branch"] for item in appointment_items if item["branch"]})
    branch_filters = ["Tất cả chi nhánh", *branch_filters]

    summary = {
        "total": len(appointment_items),
        "confirmed": len([item for item in appointment_items if item["status_key"] == "confirmed"]),
        "pending": len([item for item in appointment_items if item["status_key"] == "pending"]),
        "cancelled": len([item for item in appointment_items if item["status_key"] == "cancelled"]),
        "completed": len([item for item in appointment_items if item["status_key"] == "completed"]),
    }

    customer_rows = (
        Customer.query.filter(Customer.branch_id == branch_id)
        .order_by(Customer.full_name.asc(), Customer.id.asc())
        .limit(800)
        .all()
    )
    customer_options: list[dict[str, Any]] = []
    for row in customer_rows:
        name = (row.full_name or "").strip() or f"Khách #{row.id}"
        phone = (row.phone or "").strip() or "-"
        dob_text = str(row.dob or "").strip()
        dob_match = re.search(r"(19|20)\d{2}", dob_text)
        dob_year = dob_match.group(0) if dob_match else "----"
        customer_options.append(
            {
                "id": row.id,
                "display": f"{name} - {dob_year} - {phone}",
                "search": f"{name} {dob_year} {phone}".lower(),
            }
        )

    service_rows = (
        Service.query.filter(Service.branch_id == branch_id)
        .order_by(Service.name.asc(), Service.id.asc())
        .limit(500)
        .all()
    )
    service_options: list[dict[str, Any]] = []
    for row in service_rows:
        duration = int(row.duration_minutes or 0)
        service_options.append(
            {
                "id": row.id,
                "duration_minutes": duration,
                "display": f"{row.name} ({duration} phút - {_format_money(row.price)})",
                "search": str(row.name or "").lower(),
            }
        )

    form_state = _consume_appointment_form_state()
    appointment_form_state = {
        "open": bool(form_state.get("open")),
        "customer_query": str(form_state.get("customer_query") or ""),
        "customer_id": str(form_state.get("customer_id") or ""),
        "service_query": str(form_state.get("service_query") or ""),
        "service_id": str(form_state.get("service_id") or ""),
        "start_at": str(form_state.get("start_at") or ""),
    }
    min_start_at = datetime.combine(date.today(), datetime.min.time()).strftime("%Y-%m-%dT%H:%M")

    return render_template(
        "web/appointments.html",
        page_title="Lịch hẹn",
        page_subtitle="Quản lý toàn bộ lịch hẹn trong chuỗi",
        appointments=appointment_items,
        summary=summary,
        branch_filters=branch_filters,
        status_filters=["Tất cả", "Xác nhận", "Chờ xử lý", "Đã hủy", "Hoàn thành"],
        customer_options=customer_options,
        service_options=service_options,
        appointment_form_state=appointment_form_state,
        min_start_at=min_start_at,
    )


@web_bp.post("/appointments/create")
@_roles_required("super_admin", "branch_manager", "reception")
def create_appointment_from_web():
    branch_id = getattr(g, "web_branch_id", None)
    if branch_id is None:
        return redirect(url_for("web.index"))

    customer_query = (request.form.get("customer_query") or "").strip()
    customer_id = _parse_int(request.form.get("customer_id"))
    service_query = (request.form.get("service_query") or "").strip()
    service_id = _parse_int(request.form.get("service_id"))
    start_at_raw = (request.form.get("start_at") or "").strip()

    def _redirect_error(message: str):
        flash(message, "error")
        _set_appointment_form_state(
            {
                "open": True,
                "customer_query": customer_query,
                "customer_id": customer_id or "",
                "service_query": service_query,
                "service_id": service_id or "",
                "start_at": start_at_raw,
            }
        )
        return redirect(url_for("web.appointments"))

    if customer_id is None:
        return _redirect_error("Vui lòng chọn khách hàng từ danh sách gợi ý.")
    if service_id is None:
        return _redirect_error("Vui lòng chọn dịch vụ từ danh sách gợi ý.")
    if not start_at_raw:
        return _redirect_error("Vui lòng chọn thời gian lịch hẹn.")

    try:
        start_at = datetime.fromisoformat(start_at_raw)
    except ValueError:
        return _redirect_error("Thời gian lịch hẹn không hợp lệ.")

    if start_at.date() < date.today():
        return _redirect_error("Không thể chọn ngày cũ hơn hôm nay.")

    customer = Customer.query.filter_by(id=customer_id, branch_id=branch_id).first()
    if customer is None:
        return _redirect_error("Khách hàng không thuộc chi nhánh hiện tại.")

    service = Service.query.filter_by(id=service_id, branch_id=branch_id).first()
    if service is None:
        return _redirect_error("Dịch vụ không thuộc chi nhánh hiện tại.")

    duration_minutes = int(service.duration_minutes or 0)
    if duration_minutes <= 0:
        duration_minutes = 60
    end_at = start_at + timedelta(minutes=duration_minutes)

    conflict = (
        Appointment.query.filter(
            Appointment.branch_id == branch_id,
            Appointment.customer_id == customer.id,
            Appointment.status.in_(["booked", "confirmed", "arrived", "in_service"]),
            Appointment.start_time < end_at,
            Appointment.end_time > start_at,
        )
        .order_by(Appointment.start_time.asc())
        .first()
    )
    if conflict is not None:
        return _redirect_error("Khách hàng đã có lịch hẹn trùng thời gian.")

    appointment = Appointment(
        branch_id=branch_id,
        customer_id=customer.id,
        service_id=service.id,
        start_time=start_at,
        end_time=end_at,
        status="booked",
    )
    db.session.add(appointment)
    db.session.flush()

    web_user = getattr(g, "web_user", None)
    db.session.add(
        AuditLog(
            user_id=web_user.id if web_user else None,
            branch_id=branch_id,
            action="web.appointments.create",
            entity="Appointment",
            after_json=AuditLog.dumps(appointment.to_dict()),
        )
    )
    db.session.commit()

    flash("Tạo lịch hẹn thành công.", "success")
    session.pop("web_appointments_form_state", None)
    return redirect(url_for("web.appointments"))


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
    if not rows:
        return render_template(
            "web/branches.html",
            page_title="Chi nhánh",
            page_subtitle="Quản lý thông tin các chi nhánh trong chuỗi",
            branches=[],
            summary={
                "active_branches": 0,
                "total_staff": 0,
                "total_rooms": 0,
                "avg_rating": "N/A",
            },
            manager_options_by_branch={},
        )

    branch_ids = [int(row.id) for row in rows]

    staff_rows = (
        Staff.query.filter(Staff.branch_id.in_(branch_ids))
        .order_by(Staff.branch_id.asc(), Staff.full_name.asc(), Staff.id.asc())
        .all()
    )
    staff_count_by_branch: dict[int, int] = {}
    manager_options_by_branch: dict[str, list[dict[str, Any]]] = {}
    manager_fallback_by_branch: dict[int, str] = {}
    staff_by_id: dict[int, Staff] = {}
    for staff in staff_rows:
        parsed_branch_id = _parse_int(staff.branch_id)
        if parsed_branch_id is None:
            continue
        parsed_staff_id = _parse_int(staff.id)
        if parsed_staff_id is not None:
            staff_by_id[parsed_staff_id] = staff
        staff_count_by_branch[parsed_branch_id] = staff_count_by_branch.get(parsed_branch_id, 0) + 1
        manager_options_by_branch.setdefault(str(parsed_branch_id), []).append(
            {
                "id": parsed_staff_id or "",
                "display": " - ".join(
                    [
                        (staff.full_name or "").strip() or f"Nhân sự #{staff.id}",
                        (staff.title or "").strip() or "Nhân sự",
                        (staff.phone or "").strip() or "-",
                    ]
                ),
                "search": " ".join(
                    [
                        (staff.full_name or "").strip(),
                        (staff.title or "").strip(),
                        (staff.phone or "").strip(),
                    ]
                ).lower(),
            }
        )
        if (staff.role or "").strip().lower() == "branch_manager" and parsed_branch_id not in manager_fallback_by_branch:
            manager_fallback_by_branch[parsed_branch_id] = (staff.full_name or "").strip() or "-"

    room_count_rows = (
        db.session.query(Resource.branch_id, func.count(Resource.id))
        .filter(Resource.branch_id.in_(branch_ids))
        .group_by(Resource.branch_id)
        .all()
    )
    room_count_by_branch = {
        int(branch_id): int(total or 0)
        for branch_id, total in room_count_rows
        if _parse_int(branch_id) is not None
    }

    today = date.today()
    month_start = datetime(today.year, today.month, 1)
    if today.month == 12:
        next_month_start = datetime(today.year + 1, 1, 1)
    else:
        next_month_start = datetime(today.year, today.month + 1, 1)

    appt_count_rows = (
        db.session.query(Appointment.branch_id, func.count(Appointment.id))
        .filter(
            Appointment.branch_id.in_(branch_ids),
            Appointment.start_time >= month_start,
            Appointment.start_time < next_month_start,
        )
        .group_by(Appointment.branch_id)
        .all()
    )
    appt_count_by_branch = {
        int(branch_id): int(total or 0)
        for branch_id, total in appt_count_rows
        if _parse_int(branch_id) is not None
    }

    revenue_rows = (
        db.session.query(Invoice.branch_id, func.coalesce(func.sum(Invoice.total_amount), 0))
        .filter(
            Invoice.branch_id.in_(branch_ids),
            Invoice.created_at >= month_start,
            Invoice.created_at < next_month_start,
            Invoice.status != "voided",
        )
        .group_by(Invoice.branch_id)
        .all()
    )
    revenue_by_branch = {
        int(branch_id): float(total or 0)
        for branch_id, total in revenue_rows
        if _parse_int(branch_id) is not None
    }

    def _format_money_million(value: Any) -> str:
        try:
            number = float(value or 0) / 1_000_000
        except (TypeError, ValueError):
            number = 0.0
        return f"{number:.1f} tr"

    def _parse_branch_working_hours(raw_value: Any) -> tuple[str, str, int | None]:
        open_time = "08:00"
        close_time = "22:00"
        manager_staff_id: int | None = None
        text = str(raw_value or "").strip()
        if not text:
            return open_time, close_time, manager_staff_id
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                open_candidate = str(parsed.get("open") or "").strip()
                close_candidate = str(parsed.get("close") or "").strip()
                if re.match(r"^\d{2}:\d{2}$", open_candidate):
                    open_time = open_candidate
                if re.match(r"^\d{2}:\d{2}$", close_candidate):
                    close_time = close_candidate
                manager_staff_id = _parse_int(parsed.get("manager_staff_id"))
                return open_time, close_time, manager_staff_id
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
        if " - " in text:
            parts = [part.strip() for part in text.split(" - ", 1)]
            if len(parts) == 2:
                if re.match(r"^\d{2}:\d{2}$", parts[0]):
                    open_time = parts[0]
                if re.match(r"^\d{2}:\d{2}$", parts[1]):
                    close_time = parts[1]
        return open_time, close_time, manager_staff_id

    branch_images = [
        "https://images.unsplash.com/photo-1633526543913-d30e3c230d1f?w=800&q=80",
        "https://images.unsplash.com/photo-1700142360825-d21edc53c8db?w=800&q=80",
        "https://images.unsplash.com/photo-1633526543913-d30e3c230d1f?w=800&q=80",
        "https://images.unsplash.com/photo-1700142360825-d21edc53c8db?w=800&q=80",
        "https://images.unsplash.com/photo-1633526543913-d30e3c230d1f?w=800&q=80",
    ]

    branch_items: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        branch_id = int(row.id)
        open_time, close_time, manager_staff_id = _parse_branch_working_hours(row.working_hours_json)
        manager_name = "-"
        manager_option_display = ""
        if manager_staff_id is not None:
            manager_staff = staff_by_id.get(manager_staff_id)
            if manager_staff and _parse_int(manager_staff.branch_id) == branch_id:
                manager_name = (manager_staff.full_name or "").strip() or "-"
                manager_option_display = " - ".join(
                    [
                        manager_name,
                        (manager_staff.title or "").strip() or "Nhân sự",
                        (manager_staff.phone or "").strip() or "-",
                    ]
                )
        if manager_name == "-":
            manager_name = manager_fallback_by_branch.get(branch_id, "-")

        created_at = row.created_at
        established = created_at.strftime("%m/%Y") if created_at else "-"
        status_value = (row.status or "").strip().lower()
        status_key = "inactive" if status_value == "inactive" else "active"

        branch_items.append(
            {
                "id": branch_id,
                "name": (row.name or "").strip() or f"Chi nhánh #{branch_id}",
                "short": f"CN {branch_id}",
                "address": (row.address or "").strip() or "-",
                "phone": "-",
                "hours": f"{open_time} - {close_time}",
                "open_time": open_time,
                "close_time": close_time,
                "manager_name": manager_name,
                "manager_staff_id": manager_staff_id,
                "manager_option_display": manager_option_display,
                "staff": int(staff_count_by_branch.get(branch_id, 0)),
                "rooms": int(room_count_by_branch.get(branch_id, 0)),
                "rating": "-",
                "revenue": _format_money_million(revenue_by_branch.get(branch_id, 0)),
                "appointments": int(appt_count_by_branch.get(branch_id, 0)),
                "established": established,
                "image": branch_images[index % len(branch_images)],
                "status": status_key,
            }
        )

    summary = {
        "active_branches": len([item for item in branch_items if item["status"] == "active"]),
        "total_staff": sum(int(item["staff"] or 0) for item in branch_items),
        "total_rooms": sum(int(item["rooms"] or 0) for item in branch_items),
        "avg_rating": "N/A",
    }

    return render_template(
        "web/branches.html",
        page_title="Chi nhánh",
        page_subtitle="Quản lý thông tin các chi nhánh trong chuỗi",
        branches=branch_items,
        summary=summary,
        manager_options_by_branch=manager_options_by_branch,
    )


@web_bp.post("/branches/save")
@_roles_required("super_admin")
def branches_save():
    branch_id = _parse_int(request.form.get("branch_id"))
    name = (request.form.get("name") or "").strip()
    address = (request.form.get("address") or "").strip() or None
    status = (request.form.get("status") or "").strip().lower()
    open_time = (request.form.get("open_time") or "").strip()
    close_time = (request.form.get("close_time") or "").strip()
    manager_staff_id = _parse_int(request.form.get("manager_staff_id"))

    if not name:
        flash("Vui lòng nhập tên chi nhánh.", "error")
        return redirect(url_for("web.branches"))

    if status not in {"active", "inactive"}:
        status = "active"

    if not re.match(r"^\d{2}:\d{2}$", open_time):
        open_time = "08:00"
    if not re.match(r"^\d{2}:\d{2}$", close_time):
        close_time = "22:00"

    editing = branch_id is not None
    if editing:
        branch = Branch.query.filter_by(id=branch_id).first()
        if branch is None:
            flash("Không tìm thấy chi nhánh cần cập nhật.", "error")
            return redirect(url_for("web.branches"))
    else:
        branch = Branch(name=name, status=status)
        db.session.add(branch)
        db.session.flush()

    if branch is None:
        flash("Không thể lưu chi nhánh.", "error")
        return redirect(url_for("web.branches"))

    if manager_staff_id is not None:
        manager_staff = Staff.query.filter_by(id=manager_staff_id, branch_id=branch.id).first()
        if manager_staff is None:
            flash("Quản lí được chọn không thuộc chi nhánh này.", "error")
            return redirect(url_for("web.branches"))

    working_hours_payload: dict[str, Any] = {
        "open": open_time,
        "close": close_time,
    }
    if manager_staff_id is not None:
        working_hours_payload["manager_staff_id"] = manager_staff_id
    else:
        working_hours_payload["manager_staff_id"] = None

    branch.name = name
    branch.address = address
    branch.status = status
    branch.working_hours_json = json.dumps(working_hours_payload, ensure_ascii=True, separators=(",", ":"))

    db.session.commit()

    if editing:
        flash("Đã cập nhật chi nhánh.", "success")
    else:
        flash("Đã tạo chi nhánh mới.", "success")
    return redirect(url_for("web.branches"))


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
