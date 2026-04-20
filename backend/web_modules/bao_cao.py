import csv
import io
from datetime import date, datetime

from flask import Response, g, flash, redirect, render_template, request, url_for
from sqlalchemy import and_, case, func

from backend.extensions import db
from backend.models import Branch, InventoryItem, InventoryStock, Invoice, InvoiceItem
from backend.web import (
    INVOICE_STATUS_LABELS,
    get_current_branch_scope,
    list_scope_branches,
    parse_date,
    parse_int,
    resolve_selected_branch_id,
    roles_required,
    web_bp,
)


def recent_month_keys(size=6):
    today = date.today()
    y = today.year
    m = today.month
    keys = []
    for _ in range(size):
        keys.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    keys.reverse()
    return keys


def resolve_report_filters():
    scope_ids = get_current_branch_scope()
    from_date = parse_date(request.args.get("from_date"))
    to_date = parse_date(request.args.get("to_date"))
    selected_branch_id = resolve_selected_branch_id(scope_ids, parse_int(request.args.get("branch_id")))

    return {
        "scope_ids": scope_ids,
        "from_date": from_date,
        "to_date": to_date,
        "selected_branch_id": selected_branch_id,
    }


def apply_invoice_date_filters(query, from_date, to_date):
    if from_date:
        query = query.filter(func.date(Invoice.created_at) >= from_date.isoformat())
    if to_date:
        query = query.filter(func.date(Invoice.created_at) <= to_date.isoformat())
    return query


def build_invoice_base(report_scope, from_date, to_date):
    invoice_base = Invoice.query.filter(Invoice.branch_id.in_(report_scope))
    return apply_invoice_date_filters(invoice_base, from_date, to_date)


def summarize_invoices(invoice_base):
    non_canceled_base = invoice_base.filter(Invoice.status != "canceled")
    canceled_base = invoice_base.filter(Invoice.status == "canceled")
    return {
        "total_invoice_value": non_canceled_base.with_entities(func.coalesce(func.sum(Invoice.total_amount), 0)).scalar(),
        "paid_count": non_canceled_base.with_entities(func.count(Invoice.id)).scalar(),
        "canceled_count": invoice_base.filter(Invoice.status == "canceled").with_entities(func.count(Invoice.id)).scalar(),
        "collected_amount": non_canceled_base
        .with_entities(func.coalesce(func.sum(Invoice.paid_amount), 0))
        .scalar(),
        "canceled_value": canceled_base
        .with_entities(func.coalesce(func.sum(Invoice.total_amount), 0))
        .scalar(),
        "total_invoices": invoice_base.with_entities(func.count(Invoice.id)).scalar(),
    }


def query_status_rows(invoice_base):
    status_expr = case((Invoice.status == "canceled", "canceled"), else_="paid")
    return (
        invoice_base.with_entities(status_expr.label("status"), func.count(Invoice.id))
        .group_by(status_expr)
        .order_by(status_expr.asc())
        .all()
    )


def branch_join_conditions(from_date, to_date, *, exclude_canceled=False):
    conditions = [Invoice.branch_id == Branch.id]
    if exclude_canceled:
        conditions.append(Invoice.status != "canceled")
    if from_date:
        conditions.append(func.date(Invoice.created_at) >= from_date.isoformat())
    if to_date:
        conditions.append(func.date(Invoice.created_at) <= to_date.isoformat())
    return conditions


def query_branch_rows_for_report(report_scope, from_date, to_date):
    return (
        db.session.query(
            Branch.id,
            Branch.name,
            func.coalesce(func.sum(case((Invoice.status != "canceled", Invoice.paid_amount), else_=0)), 0).label("revenue"),
            func.count(Invoice.id).label("invoice_count"),
        )
        .filter(Branch.id.in_(report_scope))
        .outerjoin(Invoice, and_(*branch_join_conditions(from_date, to_date, exclude_canceled=True)))
        .group_by(Branch.id, Branch.name)
        .order_by(Branch.name.asc())
        .all()
    )


def query_branch_rows_for_export(report_scope, from_date, to_date):
    return (
        db.session.query(
            Branch.name,
            func.count(Invoice.id).label("invoice_count"),
            func.coalesce(func.sum(case((Invoice.status == "canceled", 1), else_=0)), 0).label("canceled_count"),
            func.coalesce(func.sum(case((Invoice.status != "canceled", Invoice.total_amount), else_=0)), 0).label("total_value"),
            func.coalesce(func.sum(case((Invoice.status != "canceled", Invoice.paid_amount), else_=0)), 0).label("collected"),
            func.coalesce(func.sum(case((Invoice.status == "canceled", Invoice.total_amount), else_=0)), 0).label("canceled_value"),
        )
        .filter(Branch.id.in_(report_scope))
        .outerjoin(Invoice, and_(*branch_join_conditions(from_date, to_date)))
        .group_by(Branch.id, Branch.name)
        .order_by(Branch.name.asc())
        .all()
    )


def query_top_service_rows(report_scope, from_date, to_date, limit):
    top_service_rows = (
        db.session.query(
            InvoiceItem.service_name,
            func.coalesce(func.sum(InvoiceItem.qty), 0).label("qty"),
        )
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .filter(Invoice.branch_id.in_(report_scope), Invoice.status != "canceled")
    )
    top_service_rows = apply_invoice_date_filters(top_service_rows, from_date, to_date)
    return (
        top_service_rows.group_by(InvoiceItem.service_name)
        .order_by(func.coalesce(func.sum(InvoiceItem.qty), 0).desc())
        .limit(limit)
        .all()
    )


def query_low_stock_rows(report_scope, limit):
    return (
        db.session.query(
            Branch.name,
            InventoryItem.name,
            InventoryStock.quantity,
            InventoryItem.min_stock,
        )
        .join(InventoryStock, InventoryStock.branch_id == Branch.id)
        .join(InventoryItem, InventoryItem.id == InventoryStock.item_id)
        .filter(
            Branch.id.in_(report_scope),
            InventoryItem.status == "active",
            InventoryStock.quantity <= InventoryItem.min_stock,
        )
        .order_by(Branch.name.asc(), InventoryStock.quantity.asc())
        .limit(limit)
        .all()
    )


@web_bp.get("/reports")
@roles_required("super_admin", "branch_manager")
def reports():
    filters = resolve_report_filters()
    scope_ids = filters["scope_ids"]
    selected_branch_id = filters["selected_branch_id"]
    from_date = filters["from_date"]
    to_date = filters["to_date"]

    if not scope_ids:
        flash("Không có chi nhánh để thống kê.", "error")
        return redirect(url_for("web.dashboard"))

    report_scope = [selected_branch_id] if selected_branch_id else scope_ids

    invoice_base = build_invoice_base(report_scope, from_date, to_date)
    invoice_summary = summarize_invoices(invoice_base)

    status_rows = query_status_rows(invoice_base)
    status_items = [{"status": status, "count": count} for status, count in status_rows]

    month_rows = (
        db.session.query(
            func.strftime("%Y-%m", Invoice.created_at).label("month_key"),
            func.coalesce(func.sum(Invoice.paid_amount), 0).label("revenue"),
        )
        .filter(Invoice.branch_id.in_(report_scope), Invoice.status != "canceled")
        .group_by(func.strftime("%Y-%m", Invoice.created_at))
        .all()
    )
    month_map = {str(key): float(total or 0) for key, total in month_rows if key}
    month_keys = recent_month_keys(6)
    month_items = [{"month": key, "revenue": month_map.get(key, 0)} for key in month_keys]

    branch_rows = query_branch_rows_for_report(report_scope, from_date, to_date)
    branch_items = [
        {
            "id": branch_id,
            "name": name,
            "revenue": float(revenue or 0),
            "invoice_count": int(invoice_count or 0),
        }
        for branch_id, name, revenue, invoice_count in branch_rows
    ]

    top_service_rows = query_top_service_rows(report_scope, from_date, to_date, limit=5)
    low_stock_rows = query_low_stock_rows(report_scope, limit=20)

    best_branch = max(branch_items, key=lambda x: x["revenue"], default=None)
    weak_branch = min(branch_items, key=lambda x: x["revenue"], default=None)
    branch_options = list_scope_branches(scope_ids, order_by="name")

    return render_template(
        "web/reports.html",
        from_date=from_date,
        to_date=to_date,
        selected_branch_id=selected_branch_id,
        branch_options=branch_options,
        month_items=month_items,
        branch_items=branch_items,
        total_invoice_value=invoice_summary["total_invoice_value"],
        paid_count=invoice_summary["paid_count"],
        canceled_count=invoice_summary["canceled_count"],
        collected_amount=invoice_summary["collected_amount"],
        canceled_value=invoice_summary["canceled_value"],
        total_invoices=invoice_summary["total_invoices"],
        status_items=status_items,
        top_service_rows=top_service_rows,
        low_stock_rows=low_stock_rows,
        best_branch=best_branch,
        weak_branch=weak_branch,
        is_super_admin=g.web_user.is_super_admin,
    )


@web_bp.get("/reports/export-csv")
@roles_required("super_admin", "branch_manager")
def reports_export_csv():
    filters = resolve_report_filters()
    scope_ids = filters["scope_ids"]
    selected_branch_id = filters["selected_branch_id"]
    from_date = filters["from_date"]
    to_date = filters["to_date"]

    if not scope_ids:
        flash("Không có dữ liệu để xuất.", "error")
        return redirect(url_for("web.reports"))

    report_scope = [selected_branch_id] if selected_branch_id else scope_ids
    invoice_base = build_invoice_base(report_scope, from_date, to_date)
    invoice_summary = summarize_invoices(invoice_base)

    branch_rows = query_branch_rows_for_export(report_scope, from_date, to_date)
    status_rows = query_status_rows(invoice_base)
    top_service_rows = query_top_service_rows(report_scope, from_date, to_date, limit=20)

    exported_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    branch_map = {
        row.id: row.name for row in Branch.query.filter(Branch.id.in_(scope_ids)).all()
    }
    selected_branch_label = (
        branch_map.get(selected_branch_id, "Tất cả chi nhánh")
        if selected_branch_id
        else "Tất cả chi nhánh"
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Xuất lúc", exported_at])
    writer.writerow(["Từ ngày", from_date.isoformat() if from_date else ""])
    writer.writerow(["Đến ngày", to_date.isoformat() if to_date else ""])
    writer.writerow(["Chi nhánh lọc", selected_branch_label])
    writer.writerow([])
    writer.writerow(["Chỉ số", "Giá trị"])
    writer.writerow(["Tổng hóa đơn", int(invoice_summary["total_invoices"] or 0)])
    writer.writerow(["Hóa đơn hủy", int(invoice_summary["canceled_count"] or 0)])
    writer.writerow(["Tổng giá trị hóa đơn hợp lệ", int(float(invoice_summary["total_invoice_value"] or 0))])
    writer.writerow(["Đã thu", int(float(invoice_summary["collected_amount"] or 0))])
    writer.writerow(["Giá trị hóa đơn hủy", int(float(invoice_summary["canceled_value"] or 0))])
    writer.writerow([])
    writer.writerow([
        "Chi nhánh",
        "Tổng hóa đơn",
        "Hóa đơn hủy",
        "Hóa đơn hợp lệ",
        "Tổng giá trị hóa đơn hợp lệ",
        "Đã thu",
        "Giá trị hóa đơn hủy",
    ])
    for row in branch_rows:
        writer.writerow(
            [
                row.name,
                int(row.invoice_count or 0),
                int(row.canceled_count or 0),
                int((row.invoice_count or 0) - (row.canceled_count or 0)),
                int(float(row.total_value or 0)),
                int(float(row.collected or 0)),
                int(float(row.canceled_value or 0)),
            ]
        )

    writer.writerow([])
    writer.writerow(["Trạng thái hóa đơn", "Số lượng"])
    for status, count in status_rows:
        writer.writerow([INVOICE_STATUS_LABELS.get(status, status), int(count or 0)])

    writer.writerow([])
    writer.writerow(["Top dịch vụ", "Số lượng"])
    for service_name, qty in top_service_rows:
        writer.writerow([service_name, int(float(qty or 0))])

    csv_data = "\ufeff" + buffer.getvalue()
    filename = f"bao_cao_doanh_thu_{timestamp}.csv"
    return Response(
        csv_data,
        content_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
