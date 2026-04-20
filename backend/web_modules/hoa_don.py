import csv
import io
from datetime import datetime
from decimal import Decimal

from flask import Response, g, flash, redirect, render_template, request, url_for
from sqlalchemy import func, or_

from backend.extensions import db
from backend.logs import write_log
from backend.models import (
    Appointment,
    Branch,
    Invoice,
    InvoiceItem,
    InvoicePayment,
    Service,
    Staff,
    User,
    consume_inventory_for_invoice,
    recalc_invoice,
    reverse_inventory_for_invoice,
    sync_customer_stats,
    upsert_customer,
)
from backend.web import (
    INVOICE_STATUS_LABELS,
    get_current_branch_scope,
    is_valid_phone,
    normalize_phone_digits,
    normalize_choice,
    paginate,
    parse_date,
    parse_int,
    parse_money,
    parse_optional_text,
    parse_page,
    parse_qty,
    parse_text,
    resolve_selected_branch_id,
    roles_required,
    web_bp,
)

INVOICE_STAFF_TITLE_KEYWORDS = ("quan ly chi nhanh", "thu ngan", "le tan")


def invoices_error(message: str):
    flash(message, "error")
    return redirect(url_for("web.invoices"))


def normalize_staff_title(value: str | None) -> str:
    return parse_text(value).lower().replace("đ", "d")


def is_invoice_staff_title(value: str | None) -> bool:
    title = normalize_staff_title(value)
    return any(keyword in title for keyword in INVOICE_STAFF_TITLE_KEYWORDS)


def normalize_phone(value: str | None) -> str:
    return normalize_phone_digits(value)


def resolve_operator_staff(branch_id: int | None) -> Staff | None:
    staff_id = getattr(g.web_user, "staff_id", None)
    if not branch_id or not staff_id:
        return None
    return Staff.query.filter_by(id=staff_id, branch_id=branch_id, status="active").first()


def list_staff_candidates_for_invoice(branch_id: int, operator_staff: Staff | None) -> list[Staff]:
    rows = Staff.query.filter_by(branch_id=branch_id, status="active").order_by(Staff.full_name.asc()).all()
    if not rows:
        return [operator_staff] if operator_staff else []

    role_staff_rows = (
        User.query.with_entities(User.staff_id)
        .filter(
            User.branch_id == branch_id,
            User.is_active.is_(True),
            User.role.in_(("branch_manager", "receptionist")),
            User.staff_id.isnot(None),
        )
        .all()
    )
    role_staff_ids = {int(staff_id) for (staff_id,) in role_staff_rows if staff_id}

    selected_ids: set[int] = set()
    candidates: list[Staff] = []
    for row in rows:
        if (row.id in role_staff_ids or is_invoice_staff_title(row.title)) and row.id not in selected_ids:
            candidates.append(row)
            selected_ids.add(row.id)

    if operator_staff and operator_staff.id not in selected_ids:
        candidates.insert(0, operator_staff)

    return candidates


def build_invoice_filters(scope_ids):
    q = parse_text(request.args.get("q"))
    status = normalize_choice(request.args.get("status"), set(INVOICE_STATUS_LABELS), "")
    from_date = parse_date(request.args.get("from_date"))
    to_date = parse_date(request.args.get("to_date"))
    view_id = parse_int(request.args.get("view_id"))
    page = parse_page(request.args.get("page"), default=1)

    selected_branch_id = resolve_selected_branch_id(scope_ids, parse_int(request.args.get("branch_id")))

    return {
        "q": q,
        "status": status,
        "from_date": from_date,
        "to_date": to_date,
        "selected_branch_id": selected_branch_id,
        "view_id": view_id,
        "page": page,
    }


def apply_invoice_filters(query, filters):
    if filters["selected_branch_id"]:
        query = query.filter(Invoice.branch_id == filters["selected_branch_id"])
    if filters["q"]:
        keyword = f"%{filters['q']}%"
        query = query.filter(
            or_(
                Invoice.code.ilike(keyword),
                Invoice.customer_name.ilike(keyword),
                Invoice.customer_phone.ilike(keyword),
            )
        )
    if filters["status"]:
        if filters["status"] == "paid":
            query = query.filter(Invoice.status != "canceled")
        elif filters["status"] == "canceled":
            query = query.filter(Invoice.status == "canceled")
    if filters["from_date"]:
        query = query.filter(func.date(Invoice.created_at) >= filters["from_date"].isoformat())
    if filters["to_date"]:
        query = query.filter(func.date(Invoice.created_at) <= filters["to_date"].isoformat())
    return query


def calc_kpi(filtered_query):
    total_count = filtered_query.count()
    canceled_count = filtered_query.filter(Invoice.status == "canceled").count()
    paid_count = filtered_query.filter(Invoice.status != "canceled").count()

    collected_value = (
        filtered_query.filter(Invoice.status != "canceled")
        .with_entities(func.coalesce(func.sum(Invoice.paid_amount), 0))
        .scalar()
    )
    paid_ratio = round((paid_count * 100.0 / total_count), 1) if total_count else 0.0
    canceled_ratio = round((canceled_count * 100.0 / total_count), 1) if total_count else 0.0

    return {
        "total_count": total_count,
        "paid_count": paid_count,
        "completed_value": collected_value,
        "canceled_count": canceled_count,
        "paid_ratio": paid_ratio,
        "canceled_ratio": canceled_ratio,
    }


@web_bp.get("/invoices")
@roles_required("super_admin", "branch_manager", "receptionist")
def invoices():
    scope_ids = get_current_branch_scope()
    if not scope_ids:
        return redirect(url_for("web.dashboard"))

    filters = build_invoice_filters(scope_ids)
    base_query = Invoice.query.filter(Invoice.branch_id.in_(scope_ids))
    filtered_query = apply_invoice_filters(base_query, filters)

    kpi = calc_kpi(filtered_query)
    pager = paginate(
        filtered_query.order_by(Invoice.id.asc()),
        page=filters["page"],
        per_page=10,
    )

    branch_options = Branch.query.filter(Branch.id.in_(scope_ids)).order_by(Branch.name.asc()).all()
    branch_map = {row.id: row.name for row in branch_options}
    if filters["selected_branch_id"]:
        scope_label = branch_map.get(filters["selected_branch_id"], "Chi nhánh")
    else:
        scope_label = "Tất cả chi nhánh" if g.web_user.is_super_admin else branch_map.get(g.active_branch_id, "Chi nhánh")

    selected_invoice = None
    if filters["view_id"]:
        selected_invoice = Invoice.query.filter(
            Invoice.id == filters["view_id"],
            Invoice.branch_id.in_(scope_ids),
        ).first()

    source_appointment = None
    source_appointment_id = parse_int(request.args.get("appointment_id"))
    if source_appointment_id:
        source_appointment = Appointment.query.filter(
            Appointment.id == source_appointment_id,
            Appointment.branch_id.in_(scope_ids),
        ).first()
        if source_appointment and source_appointment.invoice:
            return redirect(url_for("web.invoices", view_id=source_appointment.invoice.id))
        if source_appointment and source_appointment.status == "cancelled":
            flash("Không thể tạo hóa đơn từ lịch hẹn đã hủy.", "error")
            source_appointment = None

    operator_branch_id = g.active_branch_id if g.active_branch_id in scope_ids else scope_ids[0]
    if source_appointment and source_appointment.branch_id in scope_ids:
        operator_branch_id = source_appointment.branch_id
    operator_staff = resolve_operator_staff(operator_branch_id)
    service_rows = (
        Service.query.filter_by(branch_id=operator_branch_id, status="active").order_by(Service.name.asc()).all()
        if operator_branch_id
        else []
    )
    can_select_staff = False
    if operator_branch_id and can_select_staff:
        staff_rows = list_staff_candidates_for_invoice(operator_branch_id, operator_staff)
    elif operator_staff:
        staff_rows = [operator_staff]
    else:
        staff_rows = []

    can_export_csv = g.web_user.role in {"super_admin", "branch_manager"}
    can_create_invoice = g.web_user.role == "receptionist"
    can_void_invoice = g.web_user.role == "branch_manager"
    if g.web_user.role == "receptionist" and operator_staff is None:
        can_create_invoice = False

    operator_staff_label = "Chưa liên kết nhân sự"
    if operator_staff:
        display_name = parse_text(operator_staff.full_name) or g.web_user.username
        operator_staff_label = f"{display_name} - NV{operator_staff.id}"

    return render_template(
        "web/invoices.html",
        invoice_rows=pager.items,
        pager=pager,
        branch_options=branch_options,
        selected_invoice=selected_invoice,
        scope_label=scope_label,
        filters=filters,
        kpi=kpi,
        is_super_admin=g.web_user.is_super_admin,
        can_export_csv=can_export_csv,
        can_create_invoice=can_create_invoice,
        can_void_invoice=can_void_invoice,
        source_appointment=source_appointment,
        service_rows=service_rows,
        staff_rows=staff_rows,
        can_select_staff=can_select_staff,
        operator_staff=operator_staff,
        operator_staff_label=operator_staff_label,
    )


@web_bp.get("/invoices/export-csv")
@roles_required("super_admin", "branch_manager")
def invoices_export_csv():
    scope_ids = get_current_branch_scope()
    if not scope_ids:
        return invoices_error("Không có dữ liệu để xuất.")

    filters = build_invoice_filters(scope_ids)
    query = Invoice.query.filter(Invoice.branch_id.in_(scope_ids))
    query = apply_invoice_filters(query, filters)
    rows = query.order_by(Invoice.id.asc()).all()
    exported_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    branch_map = {
        row.id: row.name for row in Branch.query.filter(Branch.id.in_(scope_ids)).all()
    }
    selected_branch_label = (
        branch_map.get(filters["selected_branch_id"], "Tất cả chi nhánh")
        if filters["selected_branch_id"]
        else "Tất cả chi nhánh"
    )
    selected_status_label = (
        INVOICE_STATUS_LABELS.get(filters["status"], "Tất cả trạng thái")
        if filters["status"]
        else "Tất cả trạng thái"
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Xuất lúc", exported_at])
    writer.writerow(["Từ ngày", filters["from_date"].isoformat() if filters["from_date"] else ""])
    writer.writerow(["Đến ngày", filters["to_date"].isoformat() if filters["to_date"] else ""])
    writer.writerow(["Chi nhánh lọc", selected_branch_label])
    writer.writerow(["Trạng thái lọc", selected_status_label])
    writer.writerow(["Từ khóa", filters["q"] or ""])
    writer.writerow([])
    writer.writerow([
        "ID",
        "Mã hóa đơn",
        "Chi nhánh",
        "Tên khách",
        "SĐT",
        "Tổng tiền",
        "Đã hoàn",
        "Phương thức",
        "Trạng thái",
        "Nhân sự",
        "Ghi chú",
        "Người thao tác cuối",
        "Tạo lúc",
        "Hủy lúc",
        "Lý do hủy",
    ])
    for row in rows:
        writer.writerow(
            [
                row.id,
                row.code,
                row.branch.name if row.branch else "",
                row.customer_name or "",
                row.customer_phone or "",
                int(float(row.total_amount or 0)),
                int(float(row.refund_amount or 0)),
                row.payment_method or "",
                INVOICE_STATUS_LABELS.get("canceled" if row.status == "canceled" else "paid"),
                row.staff.full_name if row.staff else "",
                row.note or "",
                row.last_action_by or "",
                row.created_at.strftime("%Y-%m-%d %H:%M") if row.created_at else "",
                row.canceled_at.strftime("%Y-%m-%d %H:%M") if row.canceled_at else "",
                row.canceled_reason or "",
            ]
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    csv_data = "\ufeff" + output.getvalue()

    return Response(
        csv_data,
        content_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=invoices_{timestamp}.csv"},
    )


@web_bp.post("/invoices/create")
@roles_required("receptionist")
def invoices_create():
    scope_ids = get_current_branch_scope()
    branch_id = g.active_branch_id
    if not scope_ids:
        return invoices_error("Tài khoản không có phạm vi chi nhánh hợp lệ.")

    appointment_id = parse_int(request.form.get("appointment_id"))
    appointment = None
    if appointment_id:
        appointment = Appointment.query.filter(
            Appointment.id == appointment_id,
            Appointment.branch_id.in_(scope_ids),
        ).first()
        if appointment is None:
            return invoices_error("Lịch hẹn không hợp lệ hoặc không thuộc chi nhánh của bạn.")
        if appointment.invoice:
            return redirect(url_for("web.invoices", view_id=appointment.invoice.id))
        if appointment.status == "cancelled":
            return invoices_error("Không thể tạo hóa đơn từ lịch hẹn đã hủy.")
        branch_id = appointment.branch_id

    if not branch_id or branch_id not in scope_ids:
        return invoices_error("Tài khoản không có phạm vi chi nhánh hợp lệ.")

    customer_name = parse_text(request.form.get("customer_name"))
    customer_phone = normalize_phone(request.form.get("customer_phone"))
    submitted_staff_id = parse_int(request.form.get("staff_id"))
    note = parse_optional_text(request.form.get("note"))
    raw_payment_method = parse_text(request.form.get("payment_method")).lower()
    if raw_payment_method == "debt":
        return invoices_error("Không còn hỗ trợ ghi công nợ khi tạo hóa đơn. Vui lòng thu đủ hóa đơn.")
    if parse_text(request.form.get("paid_amount")):
        return invoices_error("Không còn hỗ trợ thanh toán một phần. Vui lòng thu đủ hóa đơn.")
    payment_method = normalize_choice(raw_payment_method, {"cash", "card", "transfer", "wallet"}, "cash")

    if appointment:
        customer_name = appointment.customer_name
        customer_phone = normalize_phone(appointment.customer_phone)
        if not note:
            note = f"Thanh toán từ lịch hẹn #{appointment.id}"

    if not customer_name:
        return invoices_error("Vui lòng nhập tên khách.")
    if not customer_phone:
        return invoices_error("Vui lòng nhập SĐT khách.")
    if not is_valid_phone(customer_phone):
        return invoices_error("SĐT khách phải gồm 8-15 chữ số.")

    service_ids = request.form.getlist("service_id[]")
    qty_values = request.form.getlist("qty[]")
    lines = []
    if appointment:
        service_items = appointment.service_items or []
        if service_items:
            for service_item in service_items:
                if service_item.service and service_item.service.status == "active":
                    lines.append((service_item.service, Decimal("1.00")))
        elif appointment.service:
            lines.append((appointment.service, Decimal("1.00")))
    else:
        for idx, raw_service_id in enumerate(service_ids):
            service_id = parse_int(raw_service_id)
            qty = parse_qty(qty_values[idx] if idx < len(qty_values) else "1", default=Decimal("1.00"))
            if not service_id:
                continue
            service = Service.query.filter_by(id=service_id, branch_id=branch_id, status="active").first()
            if service is not None:
                lines.append((service, qty))

    if not lines:
        return invoices_error("Cần ít nhất một dòng dịch vụ hợp lệ.")

    operator_staff = resolve_operator_staff(branch_id)
    if g.web_user.role in {"super_admin", "branch_manager"}:
        candidate_rows = list_staff_candidates_for_invoice(branch_id, operator_staff)
        candidate_ids = {row.id for row in candidate_rows}
        if not submitted_staff_id:
            return invoices_error("Vui lòng chọn nhân sự phụ trách.")
        if submitted_staff_id not in candidate_ids:
            return invoices_error("Nhân sự phụ trách phải là quản lý hoặc thu ngân thuộc chi nhánh.")

        staff = Staff.query.filter_by(id=submitted_staff_id, branch_id=branch_id, status="active").first()
        if staff is None:
            return invoices_error("Nhân sự phụ trách không hợp lệ.")
    else:
        if operator_staff is None:
            return invoices_error("Tài khoản hiện tại chưa liên kết nhân sự đang làm việc.")
        staff = operator_staff

    customer = upsert_customer(branch_id, customer_name, customer_phone, note)
    db.session.flush()

    invoice = Invoice(
        code="TMP",
        branch_id=branch_id,
        staff_id=staff.id,
        customer_id=customer.id,
        appointment_id=appointment.id if appointment else None,
        customer_name=customer_name,
        customer_phone=customer_phone,
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        status="paid",
        payment_status="paid",
        payment_method=payment_method,
        note=note,
        last_action_by=g.web_user.username,
    )
    db.session.add(invoice)
    db.session.flush()
    invoice.code = f"HD{invoice.id:06d}"

    for service, qty in lines:
        invoice.items.append(
            InvoiceItem(
                invoice_id=invoice.id,
                service_id=service.id,
                service_name=service.name,
                qty=qty,
                unit_price=service.price,
            )
        )

    recalc_invoice(invoice)
    if Decimal(str(invoice.total_amount or 0)) <= 0:
        db.session.rollback()
        return invoices_error("Tổng tiền hóa đơn phải lớn hơn 0.")

    paid_amount = Decimal(str(invoice.total_amount or 0))
    invoice.payments.append(
        InvoicePayment(
            invoice_id=invoice.id,
            payment_type="payment",
            method=payment_method,
            amount=paid_amount,
            note="Thanh toán khi tạo hóa đơn",
            created_by=g.web_user.username,
        )
    )

    recalc_invoice(invoice)
    consume_inventory_for_invoice(invoice)
    if appointment:
        appointment.status = "completed"
        appointment.customer_id = customer.id

    sync_customer_stats(customer)

    write_log(
        "create_invoice",
        branch_id=branch_id,
        entity_type="invoice",
        entity_id=invoice.id,
        message=f"Tạo hóa đơn {invoice.code}",
        details={"appointment_id": appointment.id if appointment else None, "payment_method": payment_method},
    )

    db.session.commit()
    flash("Đã tạo hóa đơn.", "success")
    return redirect(url_for("web.invoices", view_id=invoice.id))


@web_bp.post("/invoices/payment")
@roles_required("receptionist")
def invoices_add_payment():
    return invoices_error("Chức năng thanh toán một phần đã được tắt. Vui lòng tạo hóa đơn thu đủ tiền.")


@web_bp.post("/invoices/refund")
@roles_required("branch_manager")
def invoices_refund():
    branch_id = g.active_branch_id
    invoice_id = parse_int(request.form.get("invoice_id"))
    amount = parse_money(request.form.get("amount"), default=Decimal("0.00"))
    method = normalize_choice(request.form.get("method"), {"cash", "card", "transfer", "wallet"}, "cash")
    note = parse_optional_text(request.form.get("note"))

    invoice = Invoice.query.filter_by(id=invoice_id, branch_id=branch_id).first() if invoice_id else None
    if invoice is None:
        return invoices_error("Không tìm thấy hóa đơn trong chi nhánh của bạn.")
    if invoice.status == "canceled":
        return invoices_error("Không thể hoàn tiền cho hóa đơn đã hủy.")
    if amount <= 0:
        return invoices_error("Số tiền hoàn phải lớn hơn 0.")
    if amount > Decimal(str(invoice.paid_amount or 0)):
        return invoices_error("Số tiền hoàn vượt số tiền đã thu.")

    invoice.payments.append(
        InvoicePayment(
            invoice_id=invoice.id,
            payment_type="refund",
            method=method,
            amount=amount,
            note=note,
            created_by=g.web_user.username,
        )
    )
    invoice.last_action_by = g.web_user.username
    recalc_invoice(invoice)
    sync_customer_stats(invoice.customer)
    write_log(
        "refund_invoice",
        branch_id=branch_id,
        entity_type="invoice",
        entity_id=invoice.id,
        message=f"Hoàn tiền hóa đơn {invoice.code}",
        details={"amount": str(amount), "method": method},
    )
    db.session.commit()
    flash("Đã ghi nhận hoàn tiền.", "success")
    return redirect(url_for("web.invoices", view_id=invoice.id))


@web_bp.post("/invoices/void")
@roles_required("branch_manager")
def invoices_void():
    branch_id = g.active_branch_id
    if not branch_id:
        return invoices_error("Tài khoản không có phạm vi chi nhánh hợp lệ.")

    invoice_id = parse_int(request.form.get("invoice_id"))
    cancel_reason = parse_text(request.form.get("cancel_reason"))
    if not cancel_reason:
        return invoices_error("Vui lòng nhập lý do hủy hóa đơn.")

    invoice = Invoice.query.filter_by(id=invoice_id, branch_id=branch_id).first()
    if invoice is None:
        return invoices_error("Không tìm thấy hóa đơn trong chi nhánh của bạn.")
    if invoice.status == "canceled":
        return invoices_error("Hóa đơn đã hủy trước đó.")

    reverse_inventory_for_invoice(invoice)
    invoice.status = "canceled"
    invoice.payment_status = "canceled"
    invoice.canceled_reason = cancel_reason
    invoice.canceled_at = datetime.utcnow()
    invoice.balance_amount = Decimal("0.00")
    invoice.last_action_by = g.web_user.username
    sync_customer_stats(invoice.customer)

    write_log(
        "cancel_invoice",
        branch_id=branch_id,
        entity_type="invoice",
        entity_id=invoice.id,
        message=f"Hủy hóa đơn {invoice.code}",
        details={"reason": cancel_reason},
    )

    db.session.commit()
    flash("Đã hủy hóa đơn.", "success")
    return redirect(url_for("web.invoices", view_id=invoice.id))
