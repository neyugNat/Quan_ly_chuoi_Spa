from flask import g, flash, redirect, render_template, request, url_for
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.models import Branch, Invoice, Staff
from backend.web import (
    collect_non_empty_text,
    list_scope_branches,
    normalize_choice,
    paginate,
    parse_date,
    parse_int,
    parse_optional_text,
    parse_page,
    parse_text,
    resolve_selected_branch_id,
    roles_required,
    web_bp,
)


STAFF_TITLE_DEFAULTS = [
    "Quản lý",
    "Quản lý chi nhánh",
    "Lễ tân",
    "Kiểm soát kho",
    "Kỹ thuật viên",
    "Quản lý ca",
]


def build_staff_title_options(scope_ids: list[int]) -> list[str]:
    if not scope_ids:
        return STAFF_TITLE_DEFAULTS[:]

    title_rows = (
        db.session.query(Staff.title)
        .filter(
            Staff.branch_id.in_(scope_ids),
            Staff.title.isnot(None),
            Staff.title != "",
        )
        .distinct()
        .order_by(Staff.title.asc())
        .all()
    )
    dynamic_titles = collect_non_empty_text(title_rows)

    options: list[str] = []
    for title in STAFF_TITLE_DEFAULTS + dynamic_titles:
        if title and title not in options:
            options.append(title)
    return options


@web_bp.get("/staff")
@roles_required("super_admin", "branch_manager")
def staff():
    user = g.web_user
    scope_ids = getattr(g, "scope_branch_ids", [])

    q = parse_text(request.args.get("q"))
    title = parse_text(request.args.get("title"))
    status = normalize_choice(request.args.get("status"), {"active", "inactive"}, "")
    selected_branch_id = resolve_selected_branch_id(scope_ids, parse_int(request.args.get("branch_id")))
    edit_id = parse_int(request.args.get("edit_id"))
    page = parse_page(request.args.get("page"), default=1)

    query = Staff.query.filter(Staff.branch_id.in_(scope_ids))
    if selected_branch_id:
        query = query.filter(Staff.branch_id == selected_branch_id)

    if q:
        keyword = f"%{q}%"
        query = query.filter(or_(Staff.full_name.ilike(keyword), Staff.phone.ilike(keyword)))
    if title:
        query = query.filter(Staff.title == title)
    if status:
        query = query.filter(Staff.status == status)

    pager = paginate(query.order_by(Staff.id.asc()), page=page, per_page=10)
    branch_options = list_scope_branches(scope_ids, order_by="id")
    title_options = build_staff_title_options(scope_ids)
    if title and title not in title_options:
        title_options.insert(0, title)

    edit_row = None
    if edit_id:
        edit_row = Staff.query.filter(Staff.id == edit_id, Staff.branch_id.in_(scope_ids)).first()

    form_branch_id = (
        edit_row.branch_id
        if edit_row
        else selected_branch_id
    )
    if form_branch_id is None and scope_ids:
        form_branch_id = scope_ids[0]

    form_data = {
        "staff_id": edit_row.id if edit_row else None,
        "branch_id": form_branch_id,
        "full_name": edit_row.full_name if edit_row else "",
        "phone": edit_row.phone if edit_row else "",
        "title": edit_row.title if edit_row else "",
        "start_date": edit_row.start_date.isoformat() if edit_row and edit_row.start_date else "",
        "note": edit_row.note if edit_row else "",
        "status": edit_row.status if edit_row else "active",
    }

    return render_template(
        "web/staff.html",
        rows=pager.items,
        pager=pager,
        branch=db.session.get(Branch, selected_branch_id) if selected_branch_id else None,
        branch_options=branch_options,
        selected_branch_id=selected_branch_id,
        q=q,
        title=title,
        status=status,
        title_options=title_options,
        edit_mode=bool(edit_row),
        form_data=form_data,
        is_super_admin=user.is_super_admin,
    )


@web_bp.post("/staff/save")
@roles_required("super_admin", "branch_manager")
def staff_save():
    scope_ids = getattr(g, "scope_branch_ids", [])
    active_branch_id = getattr(g, "active_branch_id", None)

    staff_id = parse_int(request.form.get("staff_id"))
    full_name = parse_text(request.form.get("full_name"))
    phone = parse_text(request.form.get("phone"))
    title = parse_optional_text(request.form.get("title"))
    start_date = parse_date(request.form.get("start_date"))
    status = normalize_choice(request.form.get("status"), {"active", "inactive"}, "active")

    if g.web_user.is_super_admin:
        selected_branch_id = parse_int(request.form.get("branch_id"))
        if selected_branch_id not in scope_ids:
            flash("Chi nhánh không hợp lệ.", "error")
            return redirect(url_for("web.staff"))
        branch_id = selected_branch_id
    else:
        branch_id = active_branch_id

    if not branch_id:
        flash("Tài khoản không có phạm vi chi nhánh hợp lệ.", "error")
        return redirect(url_for("web.staff"))

    if not full_name:
        flash("Tên nhân sự không được để trống.", "error")
        return redirect(url_for("web.staff"))
    if not phone:
        flash("Số điện thoại nhân sự không được để trống.", "error")
        return redirect(url_for("web.staff"))
    if not phone.isdigit() or len(phone) < 8 or len(phone) > 15:
        flash("Số điện thoại nhân sự không hợp lệ.", "error")
        return redirect(url_for("web.staff"))

    if staff_id:
        row = Staff.query.filter(Staff.id == staff_id, Staff.branch_id.in_(scope_ids)).first()
        if row is None:
            flash("Không tìm thấy nhân sự.", "error")
            return redirect(url_for("web.staff"))
    else:
        row = Staff(branch_id=branch_id)
        db.session.add(row)

    row.branch_id = branch_id
    row.full_name = full_name
    row.phone = phone
    row.title = title
    row.status = status
    row.start_date = start_date
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Số điện thoại đã tồn tại trong hệ thống.", "error")
        return redirect(url_for("web.staff"))

    flash("Đã lưu nhân sự.", "success")
    return redirect(url_for("web.staff", branch_id=branch_id))


@web_bp.post("/staff/delete")
@roles_required("super_admin", "branch_manager")
def staff_delete():
    scope_ids = getattr(g, "scope_branch_ids", [])
    active_branch_id = getattr(g, "active_branch_id", None)

    staff_id = parse_int(request.form.get("staff_id"))
    row = Staff.query.filter(Staff.id == staff_id, Staff.branch_id.in_(scope_ids)).first() if staff_id else None
    if row is None:
        flash("Không tìm thấy nhân sự.", "error")
        return redirect(url_for("web.staff"))

    if not g.web_user.is_super_admin and row.branch_id != active_branch_id:
        flash("Bạn không có quyền xóa nhân sự của chi nhánh này.", "error")
        return redirect(url_for("web.staff", branch_id=active_branch_id))

    q = parse_text(request.form.get("q"))
    title = parse_text(request.form.get("title"))
    status = normalize_choice(request.form.get("status"), {"active", "inactive"}, "")
    selected_branch_id = parse_int(request.form.get("branch_id"))
    page = parse_page(request.form.get("page"), default=1)

    has_invoice_ref = (
        Invoice.query.filter(Invoice.staff_id == row.id).with_entities(Invoice.id).first() is not None
    )

    if has_invoice_ref:
        if row.status != "inactive":
            row.status = "inactive"
            db.session.commit()
            flash("Nhân sự đã phát sinh hóa đơn, không thể xóa. Hệ thống chuyển sang ngừng hoạt động.", "success")
        else:
            flash("Nhân sự đã phát sinh hóa đơn nên không thể xóa.", "error")
    else:
        try:
            db.session.delete(row)
            db.session.commit()
            flash("Đã xóa nhân sự (chưa phát sinh nghiệp vụ)", "success")
        except IntegrityError:
            db.session.rollback()
            flash("Không thể xóa nhân sự vì đang có dữ liệu liên quan.", "error")

    return redirect(
        url_for(
            "web.staff",
            page=page,
            q=q,
            title=title,
            status=status,
            branch_id=selected_branch_id,
        )
    )


@web_bp.post("/staff/toggle")
@roles_required("super_admin", "branch_manager")
def staff_toggle():
    scope_ids = getattr(g, "scope_branch_ids", [])
    staff_id = parse_int(request.form.get("staff_id"))
    row = Staff.query.filter(Staff.id == staff_id, Staff.branch_id.in_(scope_ids)).first() if staff_id else None
    if row is None:
        flash("Không tìm thấy nhân sự.", "error")
        return redirect(url_for("web.staff"))

    row.status = "inactive" if row.status == "active" else "active"
    db.session.commit()
    flash("Đã cập nhật trạng thái nhân sự.", "success")
    return redirect(url_for("web.staff"))
