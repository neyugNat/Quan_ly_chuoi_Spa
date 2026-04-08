from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import Blueprint, flash, g, redirect, request, session, url_for

from backend.extensions import db
from backend.models import Branch, User


web_bp = Blueprint(
    "web",
    __name__,
    url_prefix="/web",
    template_folder="templates",
    static_folder="static",
)


INVOICE_STATUS_LABELS = {
    "draft": "Nháp",
    "paid": "Đã thanh toán",
    "canceled": "Đã hủy",
}

ROLE_LABELS = {
    "super_admin": "Quản trị hệ thống",
    "branch_manager": "Quản lý chi nhánh",
    "receptionist": "Lễ tân",
    "inventory_controller": "Kiểm soát kho",
    "technician": "Kỹ thuật viên",
}

ROLE_HOME_ENDPOINT = {
    "super_admin": "web.dashboard",
    "branch_manager": "web.dashboard",
    "receptionist": "web.appointments",
    "inventory_controller": "web.inventory",
    "technician": "web.appointments",
}

ROLE_MENU_ACCESS = {
    "super_admin": {
        "dashboard",
        "branches",
        "staff",
        "services",
        "appointments",
        "inventory",
        "invoices",
        "reports",
        "accounts",
        "activity_logs",
    },
    "branch_manager": {
        "dashboard",
        "branches",
        "staff",
        "services",
        "appointments",
        "inventory",
        "invoices",
        "reports",
        "activity_logs",
    },
    "receptionist": {"appointments", "invoices"},
    "inventory_controller": {"inventory"},
    "technician": {"appointments"},
}

BRANCH_OPERATION_ROLES = {
    "branch_manager",
    "receptionist",
    "inventory_controller",
    "technician",
}

ACCOUNT_MANAGED_ROLES = BRANCH_OPERATION_ROLES


def parse_text(value: str | None) -> str:
    return (value or "").strip()


def parse_optional_text(value: str | None) -> str | None:
    text = parse_text(value)
    return text or None


def collect_non_empty_text(rows) -> list[str]:
    return [text for (value,) in rows if (text := parse_text(value))]


def parse_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_date(value):
    text = parse_text(value)
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_page(value, default=1):
    page = parse_int(value)
    if page is None or page < 1:
        return default
    return page


def normalize_choice(value, allowed, default):
    text = parse_text(value).lower()
    if text in allowed:
        return text
    return default


def paginate(query, page, per_page=10):
    return query.paginate(page=page, per_page=per_page, error_out=False)


def parse_money(value, default=Decimal("0.00")):
    try:
        parsed = Decimal(str(value or default))
    except (InvalidOperation, TypeError, ValueError):
        return default
    if parsed < 0:
        return default
    return parsed.quantize(Decimal("0.01"))


def parse_qty(value, default=Decimal("1.00")):
    try:
        parsed = Decimal(str(value or default))
    except (InvalidOperation, TypeError, ValueError):
        return default
    if parsed <= 0:
        return default
    return parsed.quantize(Decimal("0.01"))


def fmt_money(value):
    return f"{float(value or 0):,.0f} VND".replace(",", ".")


def role_label(role: str) -> str:
    return ROLE_LABELS.get(role, role)


def home_endpoint_for_user(user: User | None) -> str:
    if not user:
        return "web.login"
    return ROLE_HOME_ENDPOINT.get(user.role, "web.dashboard")


def can_access_menu_for_user(user: User | None, menu_key: str) -> bool:
    if not user:
        return False
    return menu_key in ROLE_MENU_ACCESS.get(user.role, set())


def resolve_selected_branch_id(scope_ids: list[int], requested_branch_id: int | None) -> int | None:
    if not scope_ids:
        return None

    user = getattr(g, "web_user", None)
    if user and user.is_super_admin:
        return requested_branch_id if requested_branch_id in scope_ids else None

    active_branch_id = getattr(g, "active_branch_id", None)
    if active_branch_id in scope_ids:
        return active_branch_id
    return scope_ids[0]


def list_scope_branches(scope_ids: list[int], order_by: str = "name") -> list[Branch]:
    if not scope_ids:
        return []

    query = Branch.query.filter(Branch.id.in_(scope_ids))
    if order_by == "id":
        query = query.order_by(Branch.id.asc())
    else:
        query = query.order_by(Branch.name.asc())
    return query.all()


def user_scope_branch_ids(user: User | None) -> list[int]:
    if not user:
        return []
    if user.is_super_admin:
        rows = Branch.query.with_entities(Branch.id).order_by(Branch.id.asc()).all()
        return [int(branch_id) for (branch_id,) in rows]
    return [int(user.branch_id)] if user.branch_id else []


def pick_active_branch_id(user: User | None) -> int | None:
    scope_ids = user_scope_branch_ids(user)
    if not scope_ids:
        return None
    if user and not user.is_super_admin:
        return scope_ids[0]

    from_query = parse_int(request.args.get("branch_id"))
    if from_query in scope_ids:
        session["web_branch_id"] = from_query
        return from_query

    from_session = parse_int(session.get("web_branch_id"))
    if from_session in scope_ids:
        return from_session

    fallback = scope_ids[0]
    session["web_branch_id"] = fallback
    return fallback


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not getattr(g, "web_user", None):
            return redirect(url_for("web.login"))
        return fn(*args, **kwargs)

    return wrapper


def roles_required(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            user = getattr(g, "web_user", None)
            if not user or user.role not in allowed_roles:
                flash("Bạn không có quyền truy cập module này.", "error")
                target_endpoint = home_endpoint_for_user(user)
                return redirect(url_for(target_endpoint))
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def get_current_branch_scope() -> list[int]:
    return list(getattr(g, "scope_branch_ids", []))


@web_bp.before_app_request
def load_web_user():
    if request.blueprint != "web":
        return

    user_id = parse_int(session.get("web_user_id"))
    user = db.session.get(User, user_id) if user_id else None
    if user and user.is_active:
        g.web_user = user
        g.scope_branch_ids = user_scope_branch_ids(user)
        g.active_branch_id = pick_active_branch_id(user)
    else:
        g.web_user = None
        g.scope_branch_ids = []
        g.active_branch_id = None
        session.pop("web_user_id", None)
        session.pop("web_branch_id", None)


@web_bp.app_context_processor
def inject_globals():
    user = getattr(g, "web_user", None)
    scope_branch_ids = getattr(g, "scope_branch_ids", [])
    branch_rows = list_scope_branches(scope_branch_ids, order_by="name")

    def can_access_menu(menu_key: str) -> bool:
        return can_access_menu_for_user(user, menu_key)

    return {
        "web_user": user,
        "role_label": role_label,
        "can_access_menu": can_access_menu,
        "active_branch_id": getattr(g, "active_branch_id", None),
        "branch_options": branch_rows,
        "fmt_money": fmt_money,
        "invoice_status_labels": INVOICE_STATUS_LABELS,
    }


# Register route handlers by importing each menu module.
from backend.web_modules import xac_thuc  # noqa: F401,E402
from backend.web_modules import tong_quan  # noqa: F401,E402
from backend.web_modules import chi_nhanh  # noqa: F401,E402
from backend.web_modules import nhan_su  # noqa: F401,E402
from backend.web_modules import dich_vu  # noqa: F401,E402
from backend.web_modules import lich_hen  # noqa: F401,E402
from backend.web_modules import kho  # noqa: F401,E402
from backend.web_modules import hoa_don  # noqa: F401,E402
from backend.web_modules import bao_cao  # noqa: F401,E402
from backend.web_modules import tai_khoan  # noqa: F401,E402
from backend.web_modules import nhat_ky  # noqa: F401,E402
