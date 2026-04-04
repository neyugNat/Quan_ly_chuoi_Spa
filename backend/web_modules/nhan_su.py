from flask import g, flash, redirect, render_template, request, url_for
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.models import Branch, Staff
from backend.web import (
    list_scope_branches,
    normalize_choice,
    paginate,
    parse_date,
    parse_int,
    parse_page,
    resolve_selected_branch_id,
    roles_required,
    web_bp,
)


@web_bp.get("/staff")
@roles_required("super_admin", "branch_manager")
def staff():
    user = g.web_user
    scope_ids = getattr(g, "scope_branch_ids", [])

    q = (request.args.get("q") or "").strip()
    title = (request.args.get("title") or "").strip()
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
        query = query.filter(Staff.title.ilike(f"%{title}%"))
    if status:
        query = query.filter(Staff.status == status)

    pager = paginate(query.order_by(Staff.id.asc()), page=page, per_page=10)
    branch_options = list_scope_branches(scope_ids, order_by="id")

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
    full_name = (request.form.get("full_name") or "").strip()
    phone = (request.form.get("phone") or "").strip()
    title = (request.form.get("title") or "").strip() or None
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
