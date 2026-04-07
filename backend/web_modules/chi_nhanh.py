import re

from flask import g, flash, redirect, render_template, request, url_for
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.models import (
    Appointment,
    Branch,
    InventoryStock,
    InventoryTransaction,
    Invoice,
    Service,
    Staff,
    User,
)
from backend.web import (
    normalize_choice,
    paginate,
    parse_int,
    parse_optional_text,
    parse_page,
    parse_text,
    roles_required,
    web_bp,
)


BRANCH_CODE_PATTERN = re.compile(r"^CN\d+$")
BRANCH_DEPENDENCY_LABELS = (
    ("nhân sự", Staff),
    ("hóa đơn", Invoice),
    ("lịch hẹn", Appointment),
    ("dịch vụ", Service),
    ("tồn kho", InventoryStock),
    ("giao dịch kho", InventoryTransaction),
)


def branches_redirect(page: int = 1, q: str = "", status: str = ""):
    return redirect(url_for("web.branches", page=page, q=q, status=status))


def branches_error(message: str, page: int = 1, q: str = "", status: str = ""):
    flash(message, "error")
    return branches_redirect(page=page, q=q, status=status)


def validate_branch_phone(phone: str | None) -> bool:
    if not phone:
        return True
    return phone.isdigit() and 8 <= len(phone) <= 15


def parse_branch_filters_from_form() -> tuple[str, str, int]:
    q = parse_text(request.form.get("q"))
    status = normalize_choice(request.form.get("status"), {"active", "inactive"}, "")
    page = parse_page(request.form.get("page"), default=1)
    return q, status, page


def normalize_branch_code(raw_value: str | None) -> str:
    return parse_text(raw_value).upper()


def is_manager_title(title: str | None) -> bool:
    value = parse_text(title).lower()
    return "quản lý" in value or "quan ly" in value


def list_branch_manager_candidates(branch_id: int, selected_staff_id: int | None = None) -> list[Staff]:
    query = Staff.query.filter(Staff.branch_id == branch_id)
    if selected_staff_id:
        query = query.filter(or_(Staff.status == "active", Staff.id == selected_staff_id))
    else:
        query = query.filter(Staff.status == "active")

    rows = query.order_by(Staff.full_name.asc()).all()
    return sorted(
        rows,
        key=lambda row: (
            0 if is_manager_title(row.title) else 1,
            (row.full_name or "").lower(),
        ),
    )


@web_bp.get("/branches")
@roles_required("super_admin", "branch_manager")
def branches():
    user = g.web_user
    q = parse_text(request.args.get("q"))
    status = normalize_choice(request.args.get("status"), {"active", "inactive"}, "")
    edit_id = parse_int(request.args.get("edit_id"))
    page = parse_page(request.args.get("page"), default=1)

    query = Branch.query
    if not user.is_super_admin:
        query = query.filter(Branch.id == user.branch_id)

    if q:
        keyword = f"%{q}%"
        query = query.filter(
            or_(
                Branch.branch_code.ilike(keyword),
                Branch.name.ilike(keyword),
                Branch.phone.ilike(keyword),
                Branch.address.ilike(keyword),
            )
        )
    if status:
        query = query.filter(Branch.status == status)

    pager = paginate(query.order_by(Branch.id.asc()), page=page, per_page=8)

    edit_row = None
    manager_options: list[Staff] = []
    if user.is_super_admin and edit_id:
        edit_row = db.session.get(Branch, edit_id)
        if edit_row is None:
            return branches_error("Không tìm thấy chi nhánh.", page=page, q=q, status=status)
        manager_options = list_branch_manager_candidates(edit_row.id, edit_row.manager_staff_id)

    form_data = {
        "branch_id": edit_row.id if edit_row else None,
        "branch_code": edit_row.branch_code if edit_row else "",
        "name": edit_row.name if edit_row else "",
        "address": edit_row.address if edit_row else "",
        "phone": edit_row.phone if edit_row else "",
        "manager_staff_id": edit_row.manager_staff_id if edit_row else None,
        "status": edit_row.status if edit_row else "active",
    }

    return render_template(
        "web/branches.html",
        rows=pager.items,
        pager=pager,
        q=q,
        status=status,
        edit_mode=bool(edit_row),
        form_data=form_data,
        manager_options=manager_options,
        can_edit=user.is_super_admin,
    )


@web_bp.post("/branches/save")
@roles_required("super_admin")
def branches_save():
    branch_id = parse_int(request.form.get("branch_id"))
    if branch_id is not None and branch_id < 1:
        return branches_error("ID chi nhánh phải lớn hơn hoặc bằng 1.")

    branch_code = normalize_branch_code(request.form.get("branch_code"))
    name = parse_text(request.form.get("name"))
    address = parse_optional_text(request.form.get("address"))
    phone = parse_optional_text(request.form.get("phone"))
    manager_staff_id = parse_int(request.form.get("manager_staff_id"))
    status = normalize_choice(request.form.get("status"), {"active", "inactive"}, "active")

    if not branch_id and manager_staff_id:
        return branches_error("Vui lòng tạo chi nhánh trước, sau đó vào Sửa để gán quản lý.")

    if not branch_code:
        return branches_error("Mã chi nhánh không được để trống.")
    if not BRANCH_CODE_PATTERN.fullmatch(branch_code):
        return branches_error("Mã chi nhánh phải đúng định dạng CNx (ví dụ CN1).")
    if not name:
        return branches_error("Tên chi nhánh không được để trống.")
    if not validate_branch_phone(phone):
        return branches_error("Số điện thoại chi nhánh không hợp lệ.")

    if branch_id:
        row = db.session.get(Branch, branch_id)
        if row is None:
            return branches_error("Không tìm thấy chi nhánh.")

        manager_staff = None
        if manager_staff_id:
            manager_staff = Staff.query.filter(Staff.id == manager_staff_id, Staff.branch_id == row.id).first()
            if manager_staff is None:
                return branches_error("Quản lý chi nhánh phải là nhân sự thuộc đúng chi nhánh.")
            if manager_staff.status != "active" and manager_staff.id != (row.manager_staff_id or 0):
                return branches_error("Quản lý chi nhánh phải là nhân sự đang làm việc.")
    else:
        row = Branch()
        db.session.add(row)
        manager_staff = None

    row.branch_code = branch_code
    row.name = name
    row.address = address
    row.phone = phone
    row.manager_staff_id = manager_staff.id if manager_staff else None
    row.manager_name = manager_staff.full_name if manager_staff else None
    row.status = status
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return branches_error("Mã, tên hoặc số điện thoại chi nhánh đã tồn tại.")

    flash("Đã lưu chi nhánh.", "success")
    return branches_redirect()


@web_bp.post("/branches/delete")
@roles_required("super_admin")
def branches_delete():
    branch_id = parse_int(request.form.get("branch_id"))
    row = db.session.get(Branch, branch_id) if branch_id else None
    if row is None:
        return branches_error("Không tìm thấy chi nhánh.")

    q, status, page = parse_branch_filters_from_form()

    dependency_checks = [(label, model.query.filter(model.branch_id == row.id).count()) for (label, model) in BRANCH_DEPENDENCY_LABELS]
    dependency_checks.append(
        (
            "tài khoản vận hành",
            User.query.filter(User.branch_id == row.id, User.role != "super_admin").count(),
        )
    )
    blocking_items = [f"{label}: {count}" for (label, count) in dependency_checks if count > 0]
    if blocking_items:
        return branches_error(
            "Không thể xóa chi nhánh vì đang còn dữ liệu liên quan ("
            + ", ".join(blocking_items)
            + "). Vui lòng xử lý dữ liệu trước khi xóa.",
            page=page,
            q=q,
            status=status,
        )

    try:
        db.session.delete(row)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return branches_error("Không thể xóa chi nhánh vì đang có dữ liệu liên quan.", page=page, q=q, status=status)

    flash("Đã xóa chi nhánh.", "success")
    return branches_redirect(page=page, q=q, status=status)


@web_bp.post("/branches/toggle")
@roles_required("super_admin")
def branches_toggle():
    branch_id = parse_int(request.form.get("branch_id"))
    row = db.session.get(Branch, branch_id) if branch_id else None
    if row is None:
        return branches_error("Không tìm thấy chi nhánh.")

    row.status = "inactive" if row.status == "active" else "active"
    db.session.commit()
    flash("Đã cập nhật trạng thái chi nhánh.", "success")
    return branches_redirect()
