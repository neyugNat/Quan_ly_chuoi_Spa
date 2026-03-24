# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUntypedFunctionDecorator=false, reportUnknownArgumentType=false

from decimal import Decimal
from datetime import date

from flask import jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import and_, case, func

from backend.api import api_bp
from backend.decorators.rbac import require_roles
from backend.extensions import db
from backend.models.appointment import Appointment
from backend.models.invoice import Invoice
from backend.models.inventory_item import InventoryItem
from backend.models.payment import Payment
from backend.models.stock_transaction import StockTransaction
from backend.utils.scoping import get_current_branch_id


@api_bp.get("/reports/low-stock")
@jwt_required()
@require_roles("super_admin", "branch_manager")
def get_low_stock_report():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    current_stock_expr = func.coalesce(func.sum(StockTransaction.delta_qty), Decimal("0"))
    deficit_expr = InventoryItem.min_stock - current_stock_expr

    rows = (
        db.session.query(
            InventoryItem,
            current_stock_expr.label("current_stock"),
        )
        .outerjoin(
            StockTransaction,
            and_(
                StockTransaction.branch_id == branch_id,
                StockTransaction.inventory_item_id == InventoryItem.id,
            ),
        )
        .filter(
            InventoryItem.branch_id == branch_id,
            InventoryItem.status == "active",
        )
        .group_by(InventoryItem.id)
        .having(current_stock_expr < InventoryItem.min_stock)
        .order_by(deficit_expr.desc(), InventoryItem.name.asc(), InventoryItem.id.asc())
        .all()
    )

    items = []
    for item, current_stock in rows:
        current_stock_value = current_stock if current_stock is not None else Decimal("0")
        deficit = item.min_stock - current_stock_value
        items.append(
            {
                "id": item.id,
                "name": item.name,
                "sku": item.sku,
                "unit": item.unit,
                "min_stock": float(item.min_stock),
                "current_stock": float(current_stock_value),
                "deficit": float(deficit),
            }
        )

    return jsonify({"items": items})


@api_bp.get("/reports/inventory")
@jwt_required()
@require_roles("super_admin", "branch_manager", "warehouse")
def get_inventory_report():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    current_stock_expr = func.coalesce(func.sum(StockTransaction.delta_qty), Decimal("0"))
    total_in_expr = func.coalesce(
        func.sum(case((StockTransaction.delta_qty > 0, StockTransaction.delta_qty), else_=Decimal("0"))),
        Decimal("0"),
    )
    total_out_expr = func.coalesce(
        func.sum(case((StockTransaction.delta_qty < 0, -StockTransaction.delta_qty), else_=Decimal("0"))),
        Decimal("0"),
    )
    low_stock_order_expr = case((current_stock_expr < InventoryItem.min_stock, 1), else_=0)

    rows = (
        db.session.query(
            InventoryItem,
            current_stock_expr.label("current_stock"),
            total_in_expr.label("total_in"),
            total_out_expr.label("total_out"),
        )
        .outerjoin(
            StockTransaction,
            and_(
                StockTransaction.branch_id == branch_id,
                StockTransaction.inventory_item_id == InventoryItem.id,
            ),
        )
        .filter(
            InventoryItem.branch_id == branch_id,
            InventoryItem.status == "active",
        )
        .group_by(InventoryItem.id)
        .order_by(low_stock_order_expr.desc(), InventoryItem.name.asc(), InventoryItem.id.asc())
        .limit(200)
        .all()
    )

    items = []
    for item, current_stock, total_in, total_out in rows:
        current_stock_value = current_stock if current_stock is not None else Decimal("0")
        total_in_value = total_in if total_in is not None else Decimal("0")
        total_out_value = total_out if total_out is not None else Decimal("0")
        items.append(
            {
                "id": item.id,
                "name": item.name,
                "sku": item.sku,
                "unit": item.unit,
                "min_stock": float(item.min_stock),
                "current_stock": float(current_stock_value),
                "total_in": float(total_in_value),
                "total_out": float(total_out_value),
                "low_stock": current_stock_value < item.min_stock,
            }
        )

    return jsonify({"items": items})


def _parse_optional_int_filter(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def _parse_optional_date_filter(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


@api_bp.get("/reports/appointments")
@jwt_required()
@require_roles("super_admin", "branch_manager")
def get_appointments_report():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    from_arg = request.args.get("from")
    to_arg = request.args.get("to")

    from_date = _parse_optional_date_filter(from_arg)
    if from_arg is not None and from_date is None:
        return jsonify({"error": "missing_fields"}), 400

    to_date = _parse_optional_date_filter(to_arg)
    if to_arg is not None and to_date is None:
        return jsonify({"error": "missing_fields"}), 400

    day_expr = func.strftime("%Y-%m-%d", Appointment.start_time)
    arrived_statuses = ("arrived", "in_service", "completed", "paid")

    query = db.session.query(
        day_expr.label("day"),
        func.count(Appointment.id).label("total"),
        func.sum(case((Appointment.status.in_(arrived_statuses), 1), else_=0)).label("arrived"),
        func.sum(case((Appointment.status == "no_show", 1), else_=0)).label("no_show"),
        func.sum(case((Appointment.status == "cancelled", 1), else_=0)).label("cancelled"),
    ).filter(Appointment.branch_id == branch_id)

    if from_date is not None:
        query = query.filter(func.date(Appointment.start_time) >= from_date.isoformat())
    if to_date is not None:
        query = query.filter(func.date(Appointment.start_time) <= to_date.isoformat())

    rows = query.group_by(day_expr).order_by(day_expr.asc()).limit(200).all()

    items = []
    for day, total, arrived, no_show, cancelled in rows:
        items.append(
            {
                "day": day,
                "total": int(total or 0),
                "arrived": int(arrived or 0),
                "no_show": int(no_show or 0),
                "cancelled": int(cancelled or 0),
            }
        )

    return jsonify({"items": items})


@api_bp.get("/reports/revenue")
@jwt_required()
@require_roles("super_admin", "branch_manager")
def get_revenue_report():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    staff_id_arg = request.args.get("staff_id")
    service_id_arg = request.args.get("service_id")
    from_arg = request.args.get("from")
    to_arg = request.args.get("to")

    staff_id = _parse_optional_int_filter(staff_id_arg)
    if staff_id_arg is not None and staff_id is None:
        return jsonify({"error": "missing_fields"}), 400

    service_id = _parse_optional_int_filter(service_id_arg)
    if service_id_arg is not None and service_id is None:
        return jsonify({"error": "missing_fields"}), 400

    from_date = _parse_optional_date_filter(from_arg)
    if from_arg is not None and from_date is None:
        return jsonify({"error": "missing_fields"}), 400

    to_date = _parse_optional_date_filter(to_arg)
    if to_arg is not None and to_date is None:
        return jsonify({"error": "missing_fields"}), 400

    paid_day_expr = func.strftime("%Y-%m-%d", Payment.paid_at)
    revenue_expr = func.sum(Payment.amount)

    query = (
        db.session.query(
            paid_day_expr.label("day"),
            Appointment.staff_id.label("staff_id"),
            Appointment.service_id.label("service_id"),
            revenue_expr.label("revenue"),
            func.count(Payment.id).label("payments_count"),
        )
        .join(
            Invoice,
            and_(
                Payment.invoice_id == Invoice.id,
                Invoice.branch_id == branch_id,
            ),
        )
        .outerjoin(
            Appointment,
            and_(
                Invoice.appointment_id == Appointment.id,
                Appointment.branch_id == branch_id,
            ),
        )
        .filter(
            Payment.branch_id == branch_id,
            Payment.status == "posted",
            Payment.paid_at.isnot(None),
        )
    )

    if staff_id is not None:
        query = query.filter(Appointment.staff_id == staff_id)
    if service_id is not None:
        query = query.filter(Appointment.service_id == service_id)
    if from_date is not None:
        query = query.filter(func.date(Payment.paid_at) >= from_date.isoformat())
    if to_date is not None:
        query = query.filter(func.date(Payment.paid_at) <= to_date.isoformat())

    rows = (
        query.group_by(
            paid_day_expr,
            Appointment.staff_id,
            Appointment.service_id,
        )
        .order_by(
            paid_day_expr.asc(),
            Appointment.staff_id.is_(None).asc(),
            Appointment.staff_id.asc(),
            Appointment.service_id.is_(None).asc(),
            Appointment.service_id.asc(),
        )
        .all()
    )

    items = []
    for day, grouped_staff_id, grouped_service_id, revenue, payments_count in rows:
        items.append(
            {
                "day": day,
                "staff_id": grouped_staff_id,
                "service_id": grouped_service_id,
                "revenue": float(revenue or 0),
                "payments_count": int(payments_count or 0),
            }
        )

    return jsonify({"items": items})
