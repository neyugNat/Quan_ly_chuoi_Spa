from flask import g, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.logs import write_log
from backend.models import Appointment, InvoiceItem, Service, ServiceInventoryUsage
from backend.web import (
    collect_non_empty_text,
    list_scope_branches,
    normalize_choice,
    paginate,
    parse_int,
    parse_optional_text,
    parse_money,
    parse_page,
    parse_text,
    resolve_selected_branch_id,
    roles_required,
    web_bp,
)


def format_money_input(value):
    if value is None:
        return ""
    text = str(value)
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def services_redirect(page=1, q="", group_name="", status="", selected_branch_id=None):
    return redirect(url_for("web.services", page=page, q=q, group=group_name, status=status, branch_id=selected_branch_id))


def services_error(message: str, page=1, q="", group_name="", status="", selected_branch_id=None):
    flash(message, "error")
    return services_redirect(
        page=page,
        q=q,
        group_name=group_name,
        status=status,
        selected_branch_id=selected_branch_id,
    )


@web_bp.get("/services")
@roles_required("super_admin", "branch_manager", "receptionist")
def services():
    user = g.web_user
    scope_ids = getattr(g, "scope_branch_ids", [])

    q = parse_text(request.args.get("q"))
    group_name = parse_text(request.args.get("group"))
    status = normalize_choice(request.args.get("status"), {"active", "inactive"}, "")
    selected_branch_id = resolve_selected_branch_id(scope_ids, parse_int(request.args.get("branch_id")))
    edit_id = parse_int(request.args.get("edit_id"))
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

    pager = paginate(query.order_by(Service.id.asc()), page=page, per_page=10)
    branch_options = list_scope_branches(scope_ids, order_by="name")

    edit_row = None
    if edit_id:
        edit_row = Service.query.filter(Service.id == edit_id, Service.branch_id.in_(scope_ids)).first()
        if edit_row is None:
            return services_error(
                "Không tìm thấy dịch vụ.",
                page=page,
                q=q,
                group_name=group_name,
                status=status,
                selected_branch_id=selected_branch_id,
            )

    form_branch_id = edit_row.branch_id if edit_row else selected_branch_id
    if form_branch_id is None and scope_ids:
        if user.is_super_admin:
            form_branch_id = scope_ids[0]
        else:
            form_branch_id = getattr(g, "active_branch_id", None) or scope_ids[0]

    form_data = {
        "service_id": edit_row.id if edit_row else None,
        "branch_id": form_branch_id,
        "name": edit_row.name if edit_row else "",
        "group_name": edit_row.group_name if edit_row else "",
        "price": format_money_input(edit_row.price) if edit_row else "",
        "duration_minutes": edit_row.duration_minutes if edit_row else 60,
        "status": edit_row.status if edit_row else "active",
    }

    group_rows = (
        db.session.query(Service.group_name)
        .filter(
            Service.branch_id.in_(scope_ids),
            Service.group_name.isnot(None),
            Service.group_name != "",
        )
        .distinct()
        .order_by(Service.group_name.asc())
        .all()
    )
    group_options = sorted(set(collect_non_empty_text(group_rows)))

    return render_template(
        "web/services.html",
        rows=pager.items,
        pager=pager,
        branch_options=branch_options,
        selected_branch_id=selected_branch_id,
        q=q,
        group_name=group_name,
        status=status,
        group_options=group_options,
        is_super_admin=user.is_super_admin,
        edit_mode=bool(edit_row),
        form_data=form_data,
    )


@web_bp.post("/services/save")
@roles_required("super_admin", "branch_manager")
def services_save():
    scope_ids = getattr(g, "scope_branch_ids", [])
    active_branch_id = getattr(g, "active_branch_id", None)

    service_id = parse_int(request.form.get("service_id"))
    selected_branch_id = parse_int(request.form.get("branch_id"))
    name = parse_text(request.form.get("name"))
    group_choice = parse_text(request.form.get("group_name"))
    new_group_name = parse_optional_text(request.form.get("new_group_name"))
    price = parse_money(request.form.get("price"))
    duration_minutes = parse_int(request.form.get("duration_minutes")) or 60
    status = normalize_choice(request.form.get("status"), {"active", "inactive"}, "active")

    if group_choice == "__new__":
        if not new_group_name:
            return services_error("Vui lòng nhập tên nhóm mới hoặc chọn nhóm có sẵn.")
        group_name = new_group_name
    else:
        group_name = parse_optional_text(group_choice)

    if g.web_user.is_super_admin:
        if selected_branch_id not in scope_ids:
            return services_error("Chi nhánh không hợp lệ.")
        branch_id = selected_branch_id
    else:
        branch_id = active_branch_id

    if not branch_id:
        return services_error("Tài khoản không có phạm vi chi nhánh hợp lệ.")

    if not name:
        return services_error("Tên dịch vụ không được để trống.")

    if service_id:
        row = Service.query.filter(Service.id == service_id, Service.branch_id.in_(scope_ids)).first()
        if row is None:
            return services_error("Không tìm thấy dịch vụ.")
    else:
        row = Service(branch_id=branch_id)
        db.session.add(row)

    action_label = "Cập nhật dịch vụ" if service_id else "Tạo dịch vụ"
    row.branch_id = branch_id
    row.name = name
    row.group_name = group_name
    row.price = price
    row.duration_minutes = max(duration_minutes, 1)
    row.status = status
    db.session.flush()
    write_log(
        "save_service",
        branch_id=row.branch_id,
        entity_type="service",
        entity_id=row.id,
        message=f"{action_label} {row.name}",
        details={"price": str(row.price), "duration": row.duration_minutes, "status": row.status},
    )
    db.session.commit()
    flash("Đã lưu dịch vụ.", "success")
    return redirect(url_for("web.services"))


@web_bp.post("/services/delete")
@roles_required("super_admin", "branch_manager")
def services_delete():
    scope_ids = getattr(g, "scope_branch_ids", [])
    service_id = parse_int(request.form.get("service_id"))
    row = Service.query.filter(Service.id == service_id, Service.branch_id.in_(scope_ids)).first() if service_id else None
    if row is None:
        return services_error("Không tìm thấy dịch vụ.")

    q = parse_text(request.form.get("q"))
    group_name = parse_text(request.form.get("group"))
    status = normalize_choice(request.form.get("status"), {"active", "inactive"}, "")
    selected_branch_id = parse_int(request.form.get("branch_id"))
    page = parse_page(request.form.get("page"), default=1)

    has_appointment_ref = (
        Appointment.query.filter(Appointment.service_id == row.id).with_entities(Appointment.id).first() is not None
    )
    if has_appointment_ref:
        return services_error(
            "Không thể xóa dịch vụ vì đang nằm trong lịch hẹn.",
            page=page,
            q=q,
            group_name=group_name,
            status=status,
            selected_branch_id=selected_branch_id,
        )

    try:
        write_log(
            "delete_service",
            branch_id=row.branch_id,
            entity_type="service",
            entity_id=row.id,
            message=f"Xóa dịch vụ {row.name}",
        )
        InvoiceItem.query.filter(InvoiceItem.service_id == row.id).update(
            {InvoiceItem.service_id: None},
            synchronize_session=False,
        )
        ServiceInventoryUsage.query.filter(ServiceInventoryUsage.service_id == row.id).delete(synchronize_session=False)
        db.session.delete(row)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return services_error(
            "Không thể xóa dịch vụ vì đang có dữ liệu liên quan.",
            page=page,
            q=q,
            group_name=group_name,
            status=status,
            selected_branch_id=selected_branch_id,
        )

    flash("Đã xóa dịch vụ.", "success")
    return services_redirect(
        page=page,
        q=q,
        group_name=group_name,
        status=status,
        selected_branch_id=selected_branch_id,
    )


@web_bp.post("/services/toggle")
@roles_required("super_admin", "branch_manager")
def services_toggle():
    scope_ids = getattr(g, "scope_branch_ids", [])
    service_id = parse_int(request.form.get("service_id"))
    row = Service.query.filter(Service.id == service_id, Service.branch_id.in_(scope_ids)).first() if service_id else None
    if row is None:
        return services_error("Không tìm thấy dịch vụ.")

    row.status = "inactive" if row.status == "active" else "active"
    db.session.commit()
    flash("Đã cập nhật trạng thái dịch vụ.", "success")
    return redirect(url_for("web.services"))
