import csv
import io
from datetime import datetime
from decimal import Decimal

from flask import Response, g, flash, redirect, render_template, request, url_for
from sqlalchemy import func, or_

from backend.extensions import db
from backend.models import Branch, Invoice, InvoiceItem, Service, Staff, recalc_invoice
from backend.web import (
    INVOICE_STATUS_LABELS,
    get_current_branch_scope,
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


def invoices_error(message: str):
    flash(message, "error")
    return redirect(url_for("web.invoices"))


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
        query = query.filter(Invoice.status == filters["status"])
    if filters["from_date"]:
        query = query.filter(func.date(Invoice.created_at) >= filters["from_date"].isoformat())
    if filters["to_date"]:
        query = query.filter(func.date(Invoice.created_at) <= filters["to_date"].isoformat())
    return query


def calc_kpi(filtered_query):
    total_count = filtered_query.count()
    canceled_count = filtered_query.filter(Invoice.status == "canceled").count()
    paid_count = filtered_query.filter(Invoice.status == "paid").count()
    draft_count = filtered_query.filter(Invoice.status == "draft").count()

    completed_value = (
        filtered_query.filter(Invoice.status == "paid")
        .with_entities(func.coalesce(func.sum(Invoice.total_amount), 0))
        .scalar()
    )
    completion_base = paid_count + canceled_count
    completion_ratio = round((paid_count * 100.0 / completion_base), 1) if completion_base else 0.0

    return {
        "total_count": total_count,
        "paid_count": paid_count,
        "completed_value": completed_value,
        "draft_count": draft_count,
        "canceled_count": canceled_count,
        "completion_ratio": completion_ratio,
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
        filtered_query.order_by(Invoice.created_at.desc(), Invoice.id.desc()),
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

    operator_branch_id = g.active_branch_id if g.active_branch_id in scope_ids else scope_ids[0]
    service_rows = (
        Service.query.filter_by(branch_id=operator_branch_id, status="active").order_by(Service.name.asc()).all()
        if operator_branch_id
        else []
    )
    staff_rows = (
        Staff.query.filter_by(branch_id=operator_branch_id, status="active").order_by(Staff.full_name.asc()).all()
        if operator_branch_id
        else []
    )

    can_export_csv = g.web_user.role in {"super_admin", "branch_manager"}
    can_create_invoice = g.web_user.role in {"branch_manager", "receptionist"}
    can_void_invoice = g.web_user.role == "branch_manager"

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
        service_rows=service_rows,
        staff_rows=staff_rows,
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
    rows = query.order_by(Invoice.created_at.desc(), Invoice.id.desc()).all()
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
        "Trạng thái",
        "Nhân sự",
        "Giảm giá",
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
                INVOICE_STATUS_LABELS.get(row.status, row.status),
                row.staff.full_name if row.staff else "",
                int(float(row.discount_amount or 0)),
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
@roles_required("branch_manager", "receptionist")
def invoices_create():
    branch_id = g.active_branch_id
    if not branch_id:
        return invoices_error("Tài khoản không có phạm vi chi nhánh hợp lệ.")

    customer_name = parse_optional_text(request.form.get("customer_name"))
    customer_phone = parse_optional_text(request.form.get("customer_phone"))
    staff_id = parse_int(request.form.get("staff_id"))
    note = parse_optional_text(request.form.get("note"))
    discount_amount = parse_money(request.form.get("discount_amount"), default=Decimal("0.00"))

    service_ids = request.form.getlist("service_id[]")
    qty_values = request.form.getlist("qty[]")
    lines = []
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

    if not staff_id:
        return invoices_error("Vui lòng chọn nhân sự phụ trách.")

    staff = Staff.query.filter_by(id=staff_id, branch_id=branch_id, status="active").first()
    if staff is None:
        return invoices_error("Nhân sự phụ trách không hợp lệ.")

    invoice = Invoice(
        code="TMP",
        branch_id=branch_id,
        staff_id=staff.id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        discount_amount=discount_amount,
        status="paid",
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

    db.session.commit()
    flash("Đã tạo hóa đơn.", "success")
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

    invoice.status = "canceled"
    invoice.canceled_reason = cancel_reason
    invoice.canceled_at = datetime.utcnow()
    invoice.last_action_by = g.web_user.username
    db.session.commit()
    flash("Đã hủy hóa đơn.", "success")
    return redirect(url_for("web.invoices", view_id=invoice.id))
