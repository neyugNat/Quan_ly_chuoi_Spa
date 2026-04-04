from flask import g, flash, redirect, render_template, request, url_for

from backend.extensions import db
from backend.models import Service
from backend.web import (
    list_scope_branches,
    normalize_choice,
    paginate,
    parse_int,
    parse_money,
    parse_page,
    resolve_selected_branch_id,
    roles_required,
    web_bp,
)


@web_bp.get("/services")
@roles_required("super_admin", "branch_manager")
def services():
    user = g.web_user
    scope_ids = getattr(g, "scope_branch_ids", [])

    q = (request.args.get("q") or "").strip()
    group_name = (request.args.get("group") or "").strip()
    status = normalize_choice(request.args.get("status"), {"active", "inactive"}, "")
    selected_branch_id = resolve_selected_branch_id(scope_ids, parse_int(request.args.get("branch_id")))
    page = parse_page(request.args.get("page"), default=1)

    query = Service.query.filter(Service.branch_id.in_(scope_ids))
    if selected_branch_id:
        query = query.filter(Service.branch_id == selected_branch_id)

    if q:
        query = query.filter(Service.name.ilike(f"%{q}%"))
    if group_name:
        query = query.filter(Service.group_name.ilike(f"%{group_name}%"))
    if status:
        query = query.filter(Service.status == status)

    pager = paginate(query.order_by(Service.id.desc()), page=page, per_page=10)
    branch_options = list_scope_branches(scope_ids, order_by="name")
    return render_template(
        "web/services.html",
        rows=pager.items,
        pager=pager,
        branch_options=branch_options,
        selected_branch_id=selected_branch_id,
        q=q,
        group_name=group_name,
        status=status,
        is_super_admin=user.is_super_admin,
    )


@web_bp.post("/services/save")
@roles_required("super_admin", "branch_manager")
def services_save():
    scope_ids = getattr(g, "scope_branch_ids", [])
    active_branch_id = getattr(g, "active_branch_id", None)

    service_id = parse_int(request.form.get("service_id"))
    selected_branch_id = parse_int(request.form.get("branch_id"))
    name = (request.form.get("name") or "").strip()
    group_name = (request.form.get("group_name") or "").strip() or None
    price = parse_money(request.form.get("price"))
    duration_minutes = parse_int(request.form.get("duration_minutes")) or 60
    status = normalize_choice(request.form.get("status"), {"active", "inactive"}, "active")

    if g.web_user.is_super_admin:
        if selected_branch_id not in scope_ids:
            flash("Chi nhánh không hợp lệ.", "error")
            return redirect(url_for("web.services"))
        branch_id = selected_branch_id
    else:
        branch_id = active_branch_id

    if not branch_id:
        flash("Tài khoản không có phạm vi chi nhánh hợp lệ.", "error")
        return redirect(url_for("web.services"))

    if not name:
        flash("Tên dịch vụ không được để trống.", "error")
        return redirect(url_for("web.services"))

    if service_id:
        row = Service.query.filter(Service.id == service_id, Service.branch_id.in_(scope_ids)).first()
        if row is None:
            flash("Không tìm thấy dịch vụ.", "error")
            return redirect(url_for("web.services"))
    else:
        row = Service(branch_id=branch_id)
        db.session.add(row)

    row.branch_id = branch_id
    row.name = name
    row.group_name = group_name
    row.price = price
    row.duration_minutes = max(duration_minutes, 1)
    row.status = status
    db.session.commit()
    flash("Đã lưu dịch vụ.", "success")
    return redirect(url_for("web.services"))


@web_bp.post("/services/toggle")
@roles_required("super_admin", "branch_manager")
def services_toggle():
    scope_ids = getattr(g, "scope_branch_ids", [])
    service_id = parse_int(request.form.get("service_id"))
    row = Service.query.filter(Service.id == service_id, Service.branch_id.in_(scope_ids)).first() if service_id else None
    if row is None:
        flash("Không tìm thấy dịch vụ.", "error")
        return redirect(url_for("web.services"))

    row.status = "inactive" if row.status == "active" else "active"
    db.session.commit()
    flash("Đã cập nhật trạng thái dịch vụ.", "success")
    return redirect(url_for("web.services"))
