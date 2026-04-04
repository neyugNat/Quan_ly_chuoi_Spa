from flask import g, flash, redirect, render_template, request, url_for
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.models import Branch
from backend.web import normalize_choice, paginate, parse_int, parse_page, roles_required, web_bp


@web_bp.get("/branches")
@roles_required("super_admin", "branch_manager")
def branches():
    user = g.web_user
    q = (request.args.get("q") or "").strip()
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
                Branch.name.ilike(keyword),
                Branch.phone.ilike(keyword),
                Branch.address.ilike(keyword),
            )
        )
    if status:
        query = query.filter(Branch.status == status)

    pager = paginate(query.order_by(Branch.id.asc()), page=page, per_page=8)

    edit_row = None
    if user.is_super_admin and edit_id:
        edit_row = db.session.get(Branch, edit_id)
        if edit_row is None:
            flash("Không tìm thấy chi nhánh.", "error")
            return redirect(url_for("web.branches", page=page, q=q, status=status))

    form_data = {
        "branch_id": edit_row.id if edit_row else None,
        "name": edit_row.name if edit_row else "",
        "address": edit_row.address if edit_row else "",
        "phone": edit_row.phone if edit_row else "",
        "manager_name": edit_row.manager_name if edit_row else "",
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
        can_edit=user.is_super_admin,
    )


@web_bp.post("/branches/save")
@roles_required("super_admin")
def branches_save():
    branch_id = parse_int(request.form.get("branch_id"))
    if branch_id is not None and branch_id < 1:
        flash("ID chi nhánh phải lớn hơn hoặc bằng 1.", "error")
        return redirect(url_for("web.branches"))

    name = (request.form.get("name") or "").strip()
    address = (request.form.get("address") or "").strip() or None
    phone = (request.form.get("phone") or "").strip() or None
    manager_name = (request.form.get("manager_name") or "").strip() or None
    status = normalize_choice(request.form.get("status"), {"active", "inactive"}, "active")
    if not name:
        flash("Tên chi nhánh không được để trống.", "error")
        return redirect(url_for("web.branches"))
    if phone and (not phone.isdigit() or len(phone) < 8 or len(phone) > 15):
        flash("Số điện thoại chi nhánh không hợp lệ.", "error")
        return redirect(url_for("web.branches"))

    if branch_id:
        row = db.session.get(Branch, branch_id)
        if row is None:
            flash("Không tìm thấy chi nhánh.", "error")
            return redirect(url_for("web.branches"))
    else:
        row = Branch()
        db.session.add(row)

    row.name = name
    row.address = address
    row.phone = phone
    row.manager_name = manager_name
    row.status = status
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Tên hoặc số điện thoại chi nhánh đã tồn tại.", "error")
        return redirect(url_for("web.branches"))

    flash("Đã lưu chi nhánh.", "success")
    return redirect(url_for("web.branches"))


@web_bp.post("/branches/toggle")
@roles_required("super_admin")
def branches_toggle():
    branch_id = parse_int(request.form.get("branch_id"))
    row = db.session.get(Branch, branch_id) if branch_id else None
    if row is None:
        flash("Không tìm thấy chi nhánh.", "error")
        return redirect(url_for("web.branches"))

    row.status = "inactive" if row.status == "active" else "active"
    db.session.commit()
    flash("Đã cập nhật trạng thái chi nhánh.", "success")
    return redirect(url_for("web.branches"))
