from flask import g, flash, redirect, render_template, request, url_for
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.models import Staff, User
from backend.web import (
    ACCOUNT_MANAGED_ROLES,
    list_scope_branches,
    normalize_choice,
    parse_int,
    parse_text,
    roles_required,
    web_bp,
)


MIN_PASSWORD_LENGTH = 6


ROLE_STAFF_TITLES = {
    "branch_manager": {"quản lý chi nhánh", "quan ly chi nhanh", "quản lý ca", "quan ly ca"},
    "receptionist": {"lễ tân", "le tan"},
    "inventory_controller": {"kiểm soát kho", "kiem soat kho"},
    "technician": {"kỹ thuật viên", "ky thuat vien"},
}


def normalize_text(value: str | None) -> str:
    return parse_text(value).lower()


def accounts_redirect(message: str, category: str = "error"):
    flash(message, category)
    return redirect(url_for("web.accounts"))


def find_non_admin_user(user_id: int | None) -> User | None:
    if not user_id:
        return None
    return User.query.filter(User.id == user_id, User.role != "super_admin").first()


def list_staff_options(scope_ids: list[int], edit_row: User | None):
    staff_query = Staff.query.filter(Staff.branch_id.in_(scope_ids))
    if edit_row and edit_row.staff_id:
        staff_query = staff_query.filter(or_(Staff.status == "active", Staff.id == edit_row.staff_id))
    else:
        staff_query = staff_query.filter(Staff.status == "active")
    return staff_query.order_by(Staff.full_name.asc()).all()


def build_form_data(edit_row: User | None) -> dict:
    return {
        "user_id": edit_row.id if edit_row else None,
        "username": edit_row.username if edit_row else "",
        "role": edit_row.role if edit_row else "",
        "branch_id": edit_row.branch_id if edit_row else "",
        "staff_id": edit_row.staff_id if edit_row else "",
        "is_active": "1" if (edit_row.is_active if edit_row else True) else "0",
    }


def is_staff_compatible_with_role(staff: Staff, role: str) -> bool:
    allowed_titles = ROLE_STAFF_TITLES.get(role, set())
    if not allowed_titles:
        return True
    return normalize_text(staff.title) in allowed_titles


def has_duplicate_staff_account(staff_id: int, exclude_user_id: int | None = None) -> bool:
    duplicate_query = User.query.filter(User.role != "super_admin", User.staff_id == staff_id)
    if exclude_user_id:
        duplicate_query = duplicate_query.filter(User.id != exclude_user_id)
    return duplicate_query.first() is not None


def is_valid_password(password: str, user_id: int | None) -> bool:
    if user_id:
        return not password or len(password) >= MIN_PASSWORD_LENGTH
    return len(password) >= MIN_PASSWORD_LENGTH


@web_bp.get("/accounts")
@roles_required("super_admin")
def accounts():
    scope_ids = getattr(g, "scope_branch_ids", [])
    edit_id = parse_int(request.args.get("edit_id"))

    rows = User.query.filter(User.role != "super_admin").order_by(User.id.desc()).all()
    branch_options = list_scope_branches(scope_ids, order_by="name")
    edit_row = find_non_admin_user(edit_id)
    if edit_id and edit_row is None:
        return accounts_redirect("Không tìm thấy tài khoản.")

    staff_options = list_staff_options(scope_ids, edit_row)
    form_data = build_form_data(edit_row)
    role_staff_titles = {role: sorted(titles) for role, titles in ROLE_STAFF_TITLES.items()}

    return render_template(
        "web/accounts.html",
        rows=rows,
        branch_options=branch_options,
        staff_options=staff_options,
        role_staff_titles=role_staff_titles,
        edit_mode=bool(edit_row),
        form_data=form_data,
    )


@web_bp.post("/accounts/save")
@roles_required("super_admin")
def accounts_save():
    scope_ids = getattr(g, "scope_branch_ids", [])
    user_id = parse_int(request.form.get("user_id"))
    username = parse_text(request.form.get("username"))
    role = normalize_choice(request.form.get("role"), ACCOUNT_MANAGED_ROLES, "")
    branch_id = parse_int(request.form.get("branch_id"))
    staff_id = parse_int(request.form.get("staff_id"))
    password = request.form.get("password") or ""
    is_active = (request.form.get("is_active") or "1") == "1"

    if not username:
        return accounts_redirect("Username không được để trống.")
    if not role:
        return accounts_redirect("Vai trò tài khoản không hợp lệ.")
    if branch_id not in scope_ids:
        return accounts_redirect("Chi nhánh là bắt buộc và phải hợp lệ.")

    staff = Staff.query.filter_by(id=staff_id, branch_id=branch_id, status="active").first() if staff_id else None
    if staff is None:
        return accounts_redirect("Tài khoản vận hành phải gắn với nhân sự hợp lệ trong chi nhánh.")

    if not is_staff_compatible_with_role(staff, role):
        return accounts_redirect("Nhân sự không phù hợp với chức vụ đã chọn.")

    if has_duplicate_staff_account(staff.id, exclude_user_id=user_id):
        return accounts_redirect("Nhân sự này đã có tài khoản khác, không thể gắn thêm.")

    if not is_valid_password(password, user_id):
        return accounts_redirect(f"Mật khẩu tối thiểu {MIN_PASSWORD_LENGTH} ký tự.")

    if user_id:
        row = find_non_admin_user(user_id)
        if row is None:
            return accounts_redirect("Không tìm thấy tài khoản.")
    else:
        row = User(role=role)
        db.session.add(row)

    row.username = username
    row.role = role
    row.is_active = is_active
    row.branch_id = branch_id
    row.staff_id = staff.id if staff else None
    if password:
        row.set_password(password)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return accounts_redirect("Username đã tồn tại.")

    return accounts_redirect("Đã lưu tài khoản.", "success")


@web_bp.post("/accounts/delete")
@roles_required("super_admin")
def accounts_delete():
    user_id = parse_int(request.form.get("user_id"))
    row = find_non_admin_user(user_id)
    if row is None:
        return accounts_redirect("Không tìm thấy tài khoản để xóa.")

    try:
        db.session.delete(row)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return accounts_redirect("Không thể xóa tài khoản vì có dữ liệu liên quan.")

    return accounts_redirect("Đã xóa tài khoản.", "success")


@web_bp.post("/accounts/password")
@roles_required("super_admin")
def accounts_change_password():
    current_password = request.form.get("current_password") or ""
    new_password = request.form.get("new_password") or ""
    confirm_password = request.form.get("confirm_password") or ""

    if not g.web_user.verify_password(current_password):
        return accounts_redirect("Mật khẩu hiện tại không đúng.")
    if len(new_password) < MIN_PASSWORD_LENGTH:
        return accounts_redirect(f"Mật khẩu mới tối thiểu {MIN_PASSWORD_LENGTH} ký tự.")
    if new_password != confirm_password:
        return accounts_redirect("Xác nhận mật khẩu chưa khớp.")

    g.web_user.set_password(new_password)
    db.session.commit()
    return accounts_redirect("Đổi mật khẩu thành công.", "success")
