import re

from flask import g, flash, redirect, render_template, request, url_for
from sqlalchemy import or_

from backend.extensions import db
from backend.models import Appointment, Service, Staff
from backend.web import (
    get_current_branch_scope,
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


APPOINTMENT_STATUS_LABELS = {
    "pending": "Chờ thực hiện",
    "completed": "Đã hoàn thành",
    "cancelled": "Đã hủy",
}

TIME_PATTERN = re.compile(r"^\d{2}:\d{2}$")


def normalize_time(value: str | None) -> str:
    text = parse_text(value)
    if not TIME_PATTERN.fullmatch(text):
        return ""

    hour, minute = text.split(":", maxsplit=1)
    hour_value = int(hour)
    minute_value = int(minute)
    if hour_value < 0 or hour_value > 23:
        return ""
    if minute_value < 0 or minute_value > 59:
        return ""

    return f"{hour_value:02d}:{minute_value:02d}"


@web_bp.get("/appointments")
@roles_required("super_admin", "branch_manager", "receptionist", "technician")
def appointments():
    scope_ids = get_current_branch_scope()
    if not scope_ids:
        return redirect(url_for("web.login"))

    user = g.web_user
    q = parse_text(request.args.get("q"))
    status = normalize_choice(request.args.get("status"), set(APPOINTMENT_STATUS_LABELS), "")
    from_date = parse_date(request.args.get("from_date"))
    to_date = parse_date(request.args.get("to_date"))
    selected_branch_id = resolve_selected_branch_id(scope_ids, parse_int(request.args.get("branch_id")))
    page = parse_page(request.args.get("page"), default=1)

    query = Appointment.query.filter(Appointment.branch_id.in_(scope_ids))
    if selected_branch_id:
        query = query.filter(Appointment.branch_id == selected_branch_id)
    if q:
        keyword = f"%{q}%"
        query = query.filter(
            or_(
                Appointment.customer_name.ilike(keyword),
                Appointment.customer_phone.ilike(keyword),
            )
        )
    if status:
        query = query.filter(Appointment.status == status)
    if from_date:
        query = query.filter(Appointment.appointment_date >= from_date)
    if to_date:
        query = query.filter(Appointment.appointment_date <= to_date)

    technician_scope_warning = None
    if user.role == "technician":
        if not user.staff_id:
            query = query.filter(Appointment.id == -1)
            technician_scope_warning = "Tài khoản kỹ thuật viên chưa được gán nhân sự, chưa thể hiển thị lịch hẹn."
        else:
            query = query.filter(Appointment.technician_id == user.staff_id)

    pager = paginate(
        query.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.asc(), Appointment.id.desc()),
        page=page,
        per_page=12,
    )

    branch_options = list_scope_branches(scope_ids, order_by="name")
    branch_map = {row.id: row.name for row in branch_options}

    if selected_branch_id:
        scope_label = branch_map.get(selected_branch_id, "Chi nhánh")
    else:
        scope_label = "Tất cả chi nhánh" if user.is_super_admin else branch_map.get(g.active_branch_id, "Chi nhánh")

    can_create_appointment = user.role == "receptionist"
    form_branch_id = g.active_branch_id if g.active_branch_id in scope_ids else selected_branch_id
    if form_branch_id is None and scope_ids:
        form_branch_id = scope_ids[0]

    service_rows = []
    technician_rows = []
    if can_create_appointment and form_branch_id:
        service_rows = Service.query.filter_by(branch_id=form_branch_id, status="active").order_by(Service.name.asc()).all()
        technician_rows = Staff.query.filter_by(branch_id=form_branch_id, status="active").order_by(Staff.full_name.asc()).all()

    return render_template(
        "web/appointments.html",
        rows=pager.items,
        pager=pager,
        q=q,
        status=status,
        from_date=from_date,
        to_date=to_date,
        selected_branch_id=selected_branch_id,
        branch_options=branch_options,
        scope_label=scope_label,
        status_labels=APPOINTMENT_STATUS_LABELS,
        can_create_appointment=can_create_appointment,
        service_rows=service_rows,
        technician_rows=technician_rows,
        technician_scope_warning=technician_scope_warning,
    )


@web_bp.post("/appointments/create")
@roles_required("receptionist")
def appointments_create():
    scope_ids = get_current_branch_scope()
    branch_id = g.active_branch_id
    if branch_id not in scope_ids:
        flash("Tài khoản không có phạm vi chi nhánh hợp lệ.", "error")
        return redirect(url_for("web.appointments"))

    customer_name = parse_text(request.form.get("customer_name"))
    customer_phone = parse_optional_text(request.form.get("customer_phone"))
    service_id = parse_int(request.form.get("service_id"))
    technician_id = parse_int(request.form.get("technician_id"))
    appointment_date = parse_date(request.form.get("appointment_date"))
    appointment_time = normalize_time(request.form.get("appointment_time"))
    status = normalize_choice(request.form.get("status"), set(APPOINTMENT_STATUS_LABELS), "pending")
    note = parse_optional_text(request.form.get("note"))

    if not customer_name:
        flash("Tên khách không được để trống.", "error")
        return redirect(url_for("web.appointments"))
    if appointment_date is None:
        flash("Ngày hẹn không hợp lệ.", "error")
        return redirect(url_for("web.appointments"))
    if not appointment_time:
        flash("Giờ hẹn không hợp lệ (định dạng HH:MM).", "error")
        return redirect(url_for("web.appointments"))

    service = Service.query.filter_by(id=service_id, branch_id=branch_id, status="active").first() if service_id else None
    if service is None:
        flash("Dịch vụ không hợp lệ.", "error")
        return redirect(url_for("web.appointments"))

    technician = (
        Staff.query.filter_by(id=technician_id, branch_id=branch_id, status="active").first() if technician_id else None
    )
    if technician is None:
        flash("Kỹ thuật viên không hợp lệ.", "error")
        return redirect(url_for("web.appointments"))

    db.session.add(
        Appointment(
            branch_id=branch_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            service_id=service.id,
            technician_id=technician.id,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            status=status,
            note=note,
            created_by=g.web_user.username,
        )
    )
    db.session.commit()
    flash("Đã tạo lịch hẹn.", "success")
    return redirect(url_for("web.appointments"))
