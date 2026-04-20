import re
from datetime import datetime, timedelta

from flask import g, flash, redirect, render_template, request, session, url_for
from sqlalchemy import and_, or_

from backend.extensions import db
from backend.logs import write_log
from backend.models import (
    Appointment,
    AppointmentServiceItem,
    Room,
    Service,
    Staff,
    StaffShift,
    add_minutes_to_time,
    upsert_customer,
)
from backend.web import (
    get_current_branch_scope,
    is_valid_phone,
    list_scope_branches,
    normalize_phone_digits,
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
    "overdue": "Quá hạn",
}

TIME_PATTERN = re.compile(r"^\d{2}:\d{2}$")


def normalize_staff_title(value: str | None) -> str:
    return parse_text(value).lower().replace("đ", "d")


def is_technician_title(value: str | None) -> bool:
    title = normalize_staff_title(value)
    return "kỹ thuật viên" in title or "ky thuat vien" in title


def normalize_phone(value: str | None) -> str:
    return normalize_phone_digits(value)


def list_active_technicians(branch_id: int) -> list[Staff]:
    rows = Staff.query.filter_by(branch_id=branch_id, status="active").order_by(Staff.full_name.asc()).all()
    return [row for row in rows if is_technician_title(row.title)]


def normalize_service_ids(values: list[str], fallback_value: str | None) -> list[int]:
    normalized: list[int] = []
    selected_ids = set()

    raw_values = values[:] if values else []
    if not raw_values and fallback_value is not None:
        raw_values = [fallback_value]

    for raw_value in raw_values:
        service_id = parse_int(raw_value)
        if not service_id or service_id in selected_ids:
            continue
        selected_ids.add(service_id)
        normalized.append(service_id)

    return normalized


def build_redirect_args() -> dict:
    return {
        "q": parse_text(request.form.get("q") or request.args.get("q")),
        "status": normalize_choice(request.form.get("status") or request.args.get("status"), set(APPOINTMENT_STATUS_LABELS), ""),
        "branch_id": parse_int(request.form.get("branch_id") or request.args.get("branch_id")),
        "from_date": parse_text(request.form.get("from_date") or request.args.get("from_date")),
        "to_date": parse_text(request.form.get("to_date") or request.args.get("to_date")),
        "page": parse_page(request.form.get("page") or request.args.get("page"), default=1),
    }


def appointments_redirect(message: str, category: str = "error", anchor: str | None = None):
    if message:
        flash(message, category)
    redirect_args = build_redirect_args()
    if anchor:
        redirect_args["_anchor"] = anchor
    return redirect(url_for("web.appointments", **redirect_args))


def collect_appointment_form_data(clear_fields: set[str] | None = None) -> dict:
    clear_fields = clear_fields or set()
    service_ids = [parse_text(value) for value in request.form.getlist("service_id[]") if parse_text(value)]
    form_data = {
        "customer_name": parse_text(request.form.get("customer_name")),
        "customer_phone": normalize_phone(request.form.get("customer_phone")),
        "service_ids": service_ids,
        "technician_id": parse_text(request.form.get("technician_id")),
        "room_id": parse_text(request.form.get("room_id")),
        "appointment_date": parse_text(request.form.get("appointment_date")),
        "appointment_time": parse_text(request.form.get("appointment_time")),
        "note": parse_text(request.form.get("note")),
    }
    for field_name in clear_fields:
        if field_name == "service_ids":
            form_data[field_name] = []
        else:
            form_data[field_name] = ""
    return form_data


def appointments_form_error(message: str, *, clear_fields: set[str] | None = None):
    session["appointment_form_data"] = collect_appointment_form_data(clear_fields=clear_fields)
    return appointments_redirect(message, anchor="appointment-create")


def auto_mark_overdue_appointments(scope_ids: list[int]) -> None:
    overdue_threshold = datetime.now() - timedelta(hours=6)
    pending_rows = (
        Appointment.query.filter(
            Appointment.branch_id.in_(scope_ids),
            Appointment.status == "pending",
            Appointment.appointment_date <= overdue_threshold.date(),
        )
        .order_by(Appointment.appointment_date.asc(), Appointment.appointment_time.asc(), Appointment.id.asc())
        .all()
    )

    affected_rows = 0
    for row in pending_rows:
        if not row.appointment_date:
            continue

        appointment_time_text = parse_text(row.appointment_time)
        if not TIME_PATTERN.fullmatch(appointment_time_text):
            continue

        try:
            appointment_dt = datetime.strptime(
                f"{row.appointment_date.isoformat()} {appointment_time_text}",
                "%Y-%m-%d %H:%M",
            )
        except ValueError:
            continue

        if appointment_dt <= overdue_threshold:
            row.status = "overdue"
            affected_rows += 1

    if affected_rows > 0:
        db.session.commit()


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


def validate_appointment_start(appointment_date, appointment_time: str) -> tuple[str | None, set[str]]:
    try:
        appointment_dt = datetime.strptime(
            f"{appointment_date.isoformat()} {appointment_time}",
            "%Y-%m-%d %H:%M",
        )
    except (AttributeError, ValueError):
        return "Ngày giờ hẹn không hợp lệ.", {"appointment_date", "appointment_time"}

    now_dt = datetime.now().replace(second=0, microsecond=0)
    if appointment_dt >= now_dt:
        return None, set()

    if appointment_date < now_dt.date():
        return (
            "Không thể tạo lịch hẹn ở ngày đã qua. Vui lòng chọn ngày từ hôm nay trở đi.",
            {"appointment_date", "appointment_time"},
        )

    return (
        "Không thể tạo lịch hẹn với giờ đã qua. Vui lòng chọn giờ từ thời điểm hiện tại trở đi.",
        {"appointment_time"},
    )


def load_ordered_services(branch_id: int, service_ids: list[int]) -> list[Service]:
    service_rows = (
        Service.query.filter(Service.id.in_(service_ids), Service.branch_id == branch_id, Service.status == "active")
        .order_by(Service.name.asc())
        .all()
    )
    service_map = {row.id: row for row in service_rows}
    if len(service_map) != len(service_ids):
        return []
    return [service_map[service_id] for service_id in service_ids]


def load_valid_technician(branch_id: int, technician_id: int | None) -> Staff | None:
    technician = Staff.query.filter_by(id=technician_id, branch_id=branch_id, status="active").first() if technician_id else None
    return technician if technician and is_technician_title(technician.title) else None


def calculate_end_time(start_time: str, services: list[Service]) -> str:
    duration_minutes = sum(int(service.duration_minutes or 0) for service in services)
    return add_minutes_to_time(start_time, duration_minutes or 60)


def has_time_overlap(start_a: str, end_a: str | None, start_b: str, end_b: str | None) -> bool:
    if not end_a or not end_b:
        return start_a == start_b
    return start_a < end_b and start_b < end_a


def is_technician_in_shift(technician_id: int, appointment_date, start_time: str, end_time: str) -> bool:
    shift_rows = StaffShift.query.filter_by(
        staff_id=technician_id,
        weekday=appointment_date.weekday(),
        status="active",
    ).all()
    if not shift_rows:
        return True
    return any(row.start_time <= start_time and end_time <= row.end_time for row in shift_rows)


def find_slot_conflict(branch_id: int, appointment_date, start_time: str, end_time: str, technician_id: int, room_id: int | None):
    query = Appointment.query.filter(
        Appointment.branch_id == branch_id,
        Appointment.appointment_date == appointment_date,
        Appointment.status == "pending",
    )
    conflict_rows = query.all()
    for row in conflict_rows:
        if row.technician_id != technician_id and (not room_id or row.room_id != room_id):
            continue
        row_end_time = row.end_time or add_minutes_to_time(row.appointment_time, int(row.service.duration_minutes or 60) if row.service else 60)
        if has_time_overlap(start_time, end_time, row.appointment_time, row_end_time):
            return row
    return None


def describe_slot_conflict(conflict: Appointment, technician_id: int, room_id: int | None) -> tuple[str, set[str]]:
    fields: set[str] = {"appointment_time"}
    parts = []
    if conflict.technician_id == technician_id:
        fields.add("technician_id")
        parts.append("kỹ thuật viên")
    if room_id and conflict.room_id == room_id:
        fields.add("room_id")
        parts.append("phòng/giường")

    conflict_target = " và ".join(parts) if parts else "khung giờ"
    conflict_time = conflict.appointment_time
    if conflict.end_time:
        conflict_time = f"{conflict.appointment_time}-{conflict.end_time}"
    message = f"Trùng {conflict_target} với lịch #{conflict.id} lúc {conflict_time}. Vui lòng sửa phần bị trùng, các thông tin khác đã được giữ lại."
    return message, fields


@web_bp.get("/appointments")
@roles_required("super_admin", "branch_manager", "receptionist", "technician")
def appointments():
    scope_ids = get_current_branch_scope()
    if not scope_ids:
        return redirect(url_for("web.login"))

    auto_mark_overdue_appointments(scope_ids)

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
    if status and user.role != "technician":
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
        query.order_by(Appointment.id.asc()),
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
    can_cancel_appointment = user.role in {"super_admin", "branch_manager", "receptionist"}
    can_invoice_appointment = user.role == "receptionist"
    can_complete_appointment = user.role == "technician"
    form_branch_id = g.active_branch_id if g.active_branch_id in scope_ids else selected_branch_id
    if form_branch_id is None and scope_ids:
        form_branch_id = scope_ids[0]

    service_rows = []
    technician_rows = []
    room_rows = []
    appointment_form_data = session.pop("appointment_form_data", {})
    if can_create_appointment and form_branch_id:
        service_rows = Service.query.filter_by(branch_id=form_branch_id, status="active").order_by(Service.name.asc()).all()
        technician_rows = list_active_technicians(form_branch_id)
        room_rows = Room.query.filter_by(branch_id=form_branch_id, status="active").order_by(Room.name.asc()).all()
    if "service_ids" not in appointment_form_data:
        appointment_form_data["service_ids"] = []

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
        can_cancel_appointment=can_cancel_appointment,
        can_invoice_appointment=can_invoice_appointment,
        can_complete_appointment=can_complete_appointment,
        service_rows=service_rows,
        technician_rows=technician_rows,
        room_rows=room_rows,
        appointment_form_data=appointment_form_data,
        technician_scope_warning=technician_scope_warning,
        min_appointment_date=datetime.now().date().isoformat(),
    )


@web_bp.post("/appointments/create")
@roles_required("receptionist")
def appointments_create():
    scope_ids = get_current_branch_scope()
    branch_id = g.active_branch_id
    if branch_id not in scope_ids:
        return appointments_redirect("Tài khoản không có phạm vi chi nhánh hợp lệ.")

    customer_name = parse_text(request.form.get("customer_name"))
    customer_phone = normalize_phone(request.form.get("customer_phone"))
    service_ids = normalize_service_ids(request.form.getlist("service_id[]"), request.form.get("service_id"))
    technician_id = parse_int(request.form.get("technician_id"))
    room_id = parse_int(request.form.get("room_id"))
    appointment_date = parse_date(request.form.get("appointment_date"))
    appointment_time = normalize_time(request.form.get("appointment_time"))
    note = parse_optional_text(request.form.get("note"))

    if not customer_name:
        return appointments_form_error("Tên khách không được để trống.", clear_fields={"customer_name"})
    if not customer_phone:
        return appointments_form_error("SĐT khách không được để trống.", clear_fields={"customer_phone"})
    if not is_valid_phone(customer_phone):
        return appointments_form_error("SĐT khách phải gồm 8-15 chữ số.", clear_fields={"customer_phone"})
    if not service_ids:
        return appointments_form_error("Vui lòng chọn ít nhất một dịch vụ.")
    if appointment_date is None:
        return appointments_form_error("Ngày hẹn không hợp lệ.", clear_fields={"appointment_date"})
    if not appointment_time:
        return appointments_form_error("Giờ hẹn không hợp lệ (định dạng HH:MM).", clear_fields={"appointment_time"})
    schedule_error, schedule_clear_fields = validate_appointment_start(appointment_date, appointment_time)
    if schedule_error:
        return appointments_form_error(schedule_error, clear_fields=schedule_clear_fields)

    ordered_services = load_ordered_services(branch_id, service_ids)
    if not ordered_services:
        return appointments_form_error("Dịch vụ không hợp lệ.", clear_fields={"service_ids"})

    technician = load_valid_technician(branch_id, technician_id)
    if technician is None:
        return appointments_form_error("Kỹ thuật viên không hợp lệ.", clear_fields={"technician_id"})

    room = Room.query.filter_by(id=room_id, branch_id=branch_id, status="active").first() if room_id else None
    if room is None:
        return appointments_form_error("Phòng/giường không hợp lệ.", clear_fields={"room_id"})

    end_time = calculate_end_time(appointment_time, ordered_services)
    if end_time <= appointment_time:
        return appointments_form_error(
            "Khung giờ hẹn không được kéo dài sang ngày hôm sau. Vui lòng chọn giờ sớm hơn hoặc tách lịch hẹn.",
            clear_fields={"appointment_time"},
        )

    if not is_technician_in_shift(technician.id, appointment_date, appointment_time, end_time):
        return appointments_form_error(
            "Kỹ thuật viên không có ca làm phù hợp với khung giờ này. Các thông tin hợp lệ đã được giữ lại.",
            clear_fields={"technician_id", "appointment_time"},
        )

    conflict = find_slot_conflict(branch_id, appointment_date, appointment_time, end_time, technician.id, room.id)
    if conflict:
        conflict_message, clear_fields = describe_slot_conflict(conflict, technician.id, room.id)
        return appointments_form_error(conflict_message, clear_fields=clear_fields)

    customer = upsert_customer(branch_id, customer_name, customer_phone, note)
    db.session.flush()

    appointment = Appointment(
        branch_id=branch_id,
        customer_id=customer.id,
        room_id=room.id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        service_id=ordered_services[0].id,
        technician_id=technician.id,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        end_time=end_time,
        status="pending",
        note=note,
        created_by=g.web_user.username,
    )
    db.session.add(appointment)
    db.session.flush()

    for service_row in ordered_services:
        appointment.service_items.append(
            AppointmentServiceItem(
                appointment_id=appointment.id,
                service_id=service_row.id,
                service_name=service_row.name,
            )
        )

    write_log(
        "create_appointment",
        branch_id=branch_id,
        entity_type="appointment",
        entity_id=appointment.id,
        message=f"Tạo lịch hẹn cho {customer_name}",
        details={"room_id": room.id, "technician_id": technician.id, "end_time": end_time},
    )

    db.session.commit()
    flash("Đã tạo lịch hẹn.", "success")
    return redirect(url_for("web.appointments"))


@web_bp.post("/appointments/cancel")
@roles_required("super_admin", "branch_manager", "receptionist")
def appointments_cancel():
    scope_ids = get_current_branch_scope()
    if not scope_ids:
        return appointments_redirect("Tài khoản không có phạm vi chi nhánh hợp lệ.")

    appointment_id = parse_int(request.form.get("appointment_id"))
    cancel_action = normalize_choice(request.form.get("cancel_action"), {"cancelled"}, "")
    cancel_note = parse_optional_text(request.form.get("cancel_note"))
    if not appointment_id:
        return appointments_redirect("Lịch hẹn không hợp lệ.")
    if cancel_action != "cancelled":
        return appointments_redirect("Vui lòng chọn thao tác hủy lịch.")
    if not cancel_note:
        return appointments_redirect("Vui lòng nhập ghi chú khi hủy lịch.")

    appointment = Appointment.query.filter(
        Appointment.id == appointment_id,
        Appointment.branch_id.in_(scope_ids),
    ).first()
    if appointment is None:
        return appointments_redirect("Không tìm thấy lịch hẹn trong phạm vi của bạn.")
    if appointment.status == "cancelled":
        return appointments_redirect("Lịch hẹn đã ở trạng thái Đã hủy.", "info")
    if appointment.status != "pending":
        return appointments_redirect("Chỉ có thể hủy lịch khi đang ở trạng thái Chờ thực hiện.")

    if appointment.note:
        appointment.note = f"{appointment.note} | Hủy: {cancel_note}"
    else:
        appointment.note = f"Hủy: {cancel_note}"
    appointment.status = "cancelled"

    write_log(
        "cancel_appointment",
        branch_id=appointment.branch_id,
        entity_type="appointment",
        entity_id=appointment.id,
        message=f"Hủy lịch hẹn #{appointment.id}",
        details={"reason": cancel_note},
    )

    db.session.commit()
    return appointments_redirect("Đã cập nhật lịch hẹn thành Đã hủy.", "success")


@web_bp.post("/appointments/complete")
@roles_required("technician")
def appointments_complete():
    scope_ids = get_current_branch_scope()
    if not scope_ids:
        return appointments_redirect("Tài khoản không có phạm vi chi nhánh hợp lệ.")
    if not g.web_user.staff_id:
        return appointments_redirect("Tài khoản kỹ thuật viên chưa được gán nhân sự.")

    appointment_id = parse_int(request.form.get("appointment_id"))
    if not appointment_id:
        return appointments_redirect("Lịch hẹn không hợp lệ.")

    appointment = Appointment.query.filter(
        Appointment.id == appointment_id,
        Appointment.branch_id.in_(scope_ids),
        Appointment.technician_id == g.web_user.staff_id,
    ).first()
    if appointment is None:
        return appointments_redirect("Không tìm thấy lịch hẹn của bạn.")
    if appointment.status == "completed":
        return appointments_redirect("Lịch hẹn đã ở trạng thái Đã hoàn thành.", "info")
    if appointment.status != "pending":
        return appointments_redirect("Chỉ có thể hoàn thành lịch hẹn đang Chờ thực hiện.")

    appointment.status = "completed"
    write_log(
        "complete_appointment",
        branch_id=appointment.branch_id,
        entity_type="appointment",
        entity_id=appointment.id,
        message=f"Kỹ thuật viên hoàn thành lịch hẹn #{appointment.id}",
        details={"technician_id": g.web_user.staff_id},
    )
    db.session.commit()
    return appointments_redirect("Đã đánh dấu lịch hẹn là Đã hoàn thành.", "success")
