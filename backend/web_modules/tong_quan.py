from datetime import date

from flask import g, redirect, render_template, request, url_for
from sqlalchemy import func

from backend.extensions import db
from backend.models import Branch, InventoryItem, InventoryStock, Invoice, InvoiceItem, Service, Staff
from backend.web import get_current_branch_scope, list_scope_branches, parse_int, parse_text, roles_required, web_bp


def query_branch_revenue_by_month(data_scope, month_key, desc: bool = True):
    query = (
        db.session.query(
            Branch.name,
            func.coalesce(func.sum(Invoice.total_amount), 0).label("revenue"),
        )
        .join(Invoice, Invoice.branch_id == Branch.id)
        .filter(
            Branch.id.in_(data_scope),
            Invoice.status == "paid",
            func.strftime("%Y-%m", Invoice.created_at) == month_key,
        )
        .group_by(Branch.id, Branch.name)
    )
    order_expr = func.coalesce(func.sum(Invoice.total_amount), 0)
    query = query.order_by(order_expr.desc() if desc else order_expr.asc())
    return query.first()


@web_bp.get("/dashboard")
@roles_required("super_admin", "branch_manager")
def dashboard():
    scope_ids = get_current_branch_scope()
    if not scope_ids:
        return redirect(url_for("web.login"))

    user = g.web_user
    view_mode = parse_text(request.args.get("view")).lower()
    selected_branch_id = parse_int(request.args.get("branch_id"))

    if user.is_super_admin and selected_branch_id is None and view_mode == "branch":
        selected_branch_id = g.active_branch_id if g.active_branch_id in scope_ids else None

    branch_options = []
    if user.is_super_admin:
        branch_options = list_scope_branches(scope_ids, order_by="name")
        if selected_branch_id in scope_ids:
            data_scope = [selected_branch_id]
            active_branch = next((row for row in branch_options if row.id == selected_branch_id), None)
            scope_title = active_branch.name if active_branch else "Chi nhánh"
        else:
            selected_branch_id = None
            data_scope = scope_ids
            scope_title = "Toàn chuỗi"
    else:
        active_id = g.active_branch_id if g.active_branch_id in scope_ids else scope_ids[0]
        selected_branch_id = active_id
        data_scope = [active_id]
        active_branch = db.session.get(Branch, active_id)
        scope_title = active_branch.name if active_branch else "Chi nhánh"

    branch_count = (
        Branch.query.filter(Branch.id.in_(data_scope), Branch.status == "active").count() if data_scope else 0
    )
    staff_count = (
        Staff.query.filter(Staff.branch_id.in_(data_scope), Staff.status == "active").count() if data_scope else 0
    )
    service_count = (
        Service.query.filter(Service.branch_id.in_(data_scope), Service.status == "active").count()
        if data_scope
        else 0
    )
    low_stock_count = (
        db.session.query(func.count(InventoryStock.id))
        .join(InventoryItem, InventoryStock.item_id == InventoryItem.id)
        .filter(
            InventoryStock.branch_id.in_(data_scope),
            InventoryItem.status == "active",
            InventoryStock.quantity <= InventoryItem.min_stock,
        )
        .scalar()
    )

    today = date.today()
    weekday_names = [
        "Thứ Hai",
        "Thứ Ba",
        "Thứ Tư",
        "Thứ Năm",
        "Thứ Sáu",
        "Thứ Bảy",
        "Chủ Nhật",
    ]
    today_label_vi = f"{weekday_names[today.weekday()]}, {today.day} tháng {today.month}, {today.year}"
    month_key = f"{today.year:04d}-{today.month:02d}"
    today_invoice_count = (
        Invoice.query.filter(
            Invoice.branch_id.in_(data_scope),
            Invoice.status != "canceled",
            func.date(Invoice.created_at) == today.isoformat(),
        ).count()
    )
    month_invoice_count = (
        Invoice.query.filter(
            Invoice.branch_id.in_(data_scope),
            Invoice.status != "canceled",
            func.strftime("%Y-%m", Invoice.created_at) == month_key,
        ).count()
    )
    month_revenue = (
        db.session.query(func.coalesce(func.sum(Invoice.total_amount), 0))
        .filter(
            Invoice.branch_id.in_(data_scope),
            Invoice.status == "paid",
            func.strftime("%Y-%m", Invoice.created_at) == month_key,
        )
        .scalar()
    )
    today_revenue = (
        db.session.query(func.coalesce(func.sum(Invoice.total_amount), 0))
        .filter(
            Invoice.branch_id.in_(data_scope),
            Invoice.status == "paid",
            func.date(Invoice.created_at) == today.isoformat(),
        )
        .scalar()
    )

    top_branch_row = query_branch_revenue_by_month(data_scope, month_key, desc=True)
    weak_branch_row = query_branch_revenue_by_month(data_scope, month_key, desc=False)

    recent_invoices = (
        Invoice.query.filter(Invoice.branch_id.in_(data_scope))
        .order_by(Invoice.created_at.desc())
        .limit(6)
        .all()
    )

    low_stock_rows = (
        db.session.query(Branch.name, InventoryItem.name, InventoryStock.quantity, InventoryItem.min_stock)
        .join(InventoryStock, InventoryStock.branch_id == Branch.id)
        .join(InventoryItem, InventoryItem.id == InventoryStock.item_id)
        .filter(
            Branch.id.in_(data_scope),
            InventoryItem.status == "active",
            InventoryStock.quantity <= InventoryItem.min_stock,
        )
        .order_by(Branch.name.asc(), InventoryStock.quantity.asc())
        .limit(8)
        .all()
    )

    top_service_rows = (
        db.session.query(
            InvoiceItem.service_name,
            func.coalesce(func.sum(InvoiceItem.qty), 0).label("qty"),
        )
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .filter(
            Invoice.branch_id.in_(data_scope),
            Invoice.status != "canceled",
            func.strftime("%Y-%m", Invoice.created_at) == month_key,
        )
        .group_by(InvoiceItem.service_name)
        .order_by(func.coalesce(func.sum(InvoiceItem.qty), 0).desc())
        .limit(5)
        .all()
    )

    return render_template(
        "web/dashboard.html",
        scope_title=scope_title,
        today_label_vi=today_label_vi,
        branch_options=branch_options,
        selected_branch_id=selected_branch_id,
        branch_count=branch_count,
        staff_count=staff_count,
        service_count=service_count,
        low_stock_count=int(low_stock_count or 0),
        today_invoice_count=today_invoice_count,
        month_invoice_count=month_invoice_count,
        month_revenue=month_revenue,
        today_revenue=today_revenue,
        top_branch_name=top_branch_row[0] if top_branch_row else "-",
        weak_branch_name=weak_branch_row[0] if weak_branch_row else "-",
        recent_invoices=recent_invoices,
        low_stock_rows=low_stock_rows,
        top_service_rows=top_service_rows,
    )
