# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUntypedFunctionDecorator=false, reportUnknownArgumentType=false

from datetime import date
from decimal import Decimal, InvalidOperation

from flask import jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func

from backend.api import api_bp
from backend.decorators.rbac import require_roles
from backend.extensions import db
from backend.models.inventory_item import InventoryItem
from backend.models.stock_transaction import StockTransaction
from backend.utils.scoping import get_current_branch_id

ALLOWED_TRANSACTION_TYPES = {"in", "out", "adjust", "transfer"}
THREE_DECIMAL_PLACES = Decimal("0.001")


def _parse_positive_decimal(value):
    if isinstance(value, bool):
        return None
    try:
        qty = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if qty <= Decimal("0"):
        return None
    return qty.quantize(THREE_DECIMAL_PLACES)


def _parse_non_zero_decimal(value):
    if isinstance(value, bool):
        return None
    try:
        qty = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if qty == Decimal("0"):
        return None
    return qty.quantize(THREE_DECIMAL_PLACES)


def _parse_optional_expiry_date(value):
    if value is None:
        return None, True
    if not isinstance(value, str):
        return None, False
    raw_value = value.strip()
    if not raw_value:
        return None, False
    try:
        return date.fromisoformat(raw_value), True
    except ValueError:
        return None, False


@api_bp.get("/stock-transactions")
@jwt_required()
@require_roles("super_admin", "branch_manager", "warehouse")
def list_stock_transactions():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    query = StockTransaction.query.filter(StockTransaction.branch_id == branch_id)
    inventory_item_id = request.args.get("inventory_item_id")
    if inventory_item_id is not None:
        try:
            inventory_item_id_value = int(inventory_item_id)
        except (TypeError, ValueError):
            return jsonify({"error": "missing_fields"}), 400
        query = query.filter(StockTransaction.inventory_item_id == inventory_item_id_value)

    items = query.order_by(StockTransaction.id.desc()).limit(200).all()
    return jsonify({"items": [item.to_dict() for item in items]})


@api_bp.post("/stock-transactions")
@jwt_required()
@require_roles("super_admin", "branch_manager", "warehouse")
def create_stock_transaction():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    payload = request.get_json(silent=True) or {}
    inventory_item_id = payload.get("inventory_item_id")
    transaction_type = (payload.get("transaction_type") or "").strip()
    if inventory_item_id is None or not transaction_type:
        return jsonify({"error": "missing_fields"}), 400

    if isinstance(inventory_item_id, bool):
        return jsonify({"error": "missing_fields"}), 400
    try:
        inventory_item_id = int(inventory_item_id)
    except (TypeError, ValueError):
        return jsonify({"error": "missing_fields"}), 400

    if transaction_type not in ALLOWED_TRANSACTION_TYPES:
        return jsonify({"error": "invalid_transaction_type"}), 400

    inventory_item = InventoryItem.query.filter_by(
        id=inventory_item_id,
        branch_id=branch_id,
    ).first()
    if not inventory_item:
        return jsonify({"error": "not_found"}), 404

    if transaction_type in {"in", "out"}:
        qty = _parse_positive_decimal(payload.get("qty"))
        if qty is None:
            return jsonify({"error": "missing_fields"}), 400
        delta_qty = qty if transaction_type == "in" else -qty
    else:
        delta_qty = _parse_non_zero_decimal(payload.get("delta_qty"))
        if delta_qty is None:
            return jsonify({"error": "missing_fields"}), 400

    expiry_date, valid_expiry_date = _parse_optional_expiry_date(payload.get("expiry_date"))
    if not valid_expiry_date:
        return jsonify({"error": "missing_fields"}), 400

    note = payload.get("note")
    if note is not None and not isinstance(note, str):
        return jsonify({"error": "missing_fields"}), 400

    current_stock = db.session.query(
        func.coalesce(func.sum(StockTransaction.delta_qty), Decimal("0"))
    ).filter(
        StockTransaction.branch_id == branch_id,
        StockTransaction.inventory_item_id == inventory_item.id,
    ).scalar()
    current_stock = current_stock if current_stock is not None else Decimal("0")
    if current_stock + delta_qty < Decimal("0"):
        return jsonify({"error": "insufficient_stock"}), 400

    transaction = StockTransaction(
        branch_id=branch_id,
        inventory_item_id=inventory_item.id,
        transaction_type=transaction_type,
        delta_qty=delta_qty,
        expiry_date=expiry_date,
        note=(note.strip() if isinstance(note, str) else None) or None,
    )
    db.session.add(transaction)
    db.session.commit()
    return jsonify(transaction.to_dict()), 201
