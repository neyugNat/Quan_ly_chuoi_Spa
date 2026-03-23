# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUntypedFunctionDecorator=false, reportUnknownArgumentType=false

from decimal import Decimal, InvalidOperation

from flask import jsonify, request
from flask_jwt_extended import jwt_required

from backend.api import api_bp
from backend.decorators.rbac import require_roles
from backend.extensions import db
from backend.models.inventory_item import InventoryItem
from backend.utils.scoping import get_current_branch_id


def _normalize_status(value):
    if value is None:
        return None
    status = (value or "").strip()
    if status not in {"active", "inactive"}:
        return None
    return status


def _parse_min_stock(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
    try:
        min_stock = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if min_stock < 0:
        return None
    return min_stock


def _parse_required_text(value):
    if not isinstance(value, str):
        return None
    parsed = value.strip()
    return parsed or None


@api_bp.get("/inventory-items")
@jwt_required()
@require_roles("super_admin", "branch_manager", "warehouse")
def list_inventory_items():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    items = (
        InventoryItem.query.filter(InventoryItem.branch_id == branch_id)
        .order_by(InventoryItem.id.desc())
        .limit(200)
        .all()
    )
    return jsonify({"items": [item.to_dict() for item in items]})


@api_bp.post("/inventory-items")
@jwt_required()
@require_roles("super_admin", "branch_manager", "warehouse")
def create_inventory_item():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    payload = request.get_json(silent=True) or {}
    name = _parse_required_text(payload.get("name"))
    unit = _parse_required_text(payload.get("unit"))
    if not name or not unit:
        return jsonify({"error": "missing_fields"}), 400

    normalized_status = _normalize_status(payload.get("status"))
    if payload.get("status") is not None and normalized_status is None:
        return jsonify({"error": "invalid_status"}), 400

    min_stock = _parse_min_stock(payload.get("min_stock", 0))
    if min_stock is None:
        return jsonify({"error": "missing_fields"}), 400

    expiry_tracking = payload.get("expiry_tracking", False)
    if not isinstance(expiry_tracking, bool):
        return jsonify({"error": "missing_fields"}), 400

    sku = payload.get("sku")
    if sku is not None and not isinstance(sku, str):
        return jsonify({"error": "missing_fields"}), 400

    item = InventoryItem(
        branch_id=branch_id,
        name=name,
        sku=(sku.strip() if isinstance(sku, str) else None) or None,
        unit=unit,
        min_stock=min_stock,
        expiry_tracking=expiry_tracking,
        status=normalized_status or "active",
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@api_bp.get("/inventory-items/<int:item_id>")
@jwt_required()
@require_roles("super_admin", "branch_manager", "warehouse")
def get_inventory_item(item_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    item = InventoryItem.query.filter_by(id=item_id, branch_id=branch_id).first()
    if not item:
        return jsonify({"error": "not_found"}), 404
    return jsonify(item.to_dict())


@api_bp.put("/inventory-items/<int:item_id>")
@jwt_required()
@require_roles("super_admin", "branch_manager", "warehouse")
def update_inventory_item(item_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    item = InventoryItem.query.filter_by(id=item_id, branch_id=branch_id).first()
    if not item:
        return jsonify({"error": "not_found"}), 404

    payload = request.get_json(silent=True) or {}

    if "name" in payload:
        name = _parse_required_text(payload.get("name"))
        if not name:
            return jsonify({"error": "missing_fields"}), 400
        item.name = name

    if "unit" in payload:
        unit = _parse_required_text(payload.get("unit"))
        if not unit:
            return jsonify({"error": "missing_fields"}), 400
        item.unit = unit

    if "status" in payload:
        normalized_status = _normalize_status(payload.get("status"))
        if normalized_status is None:
            return jsonify({"error": "invalid_status"}), 400
        item.status = normalized_status

    if "min_stock" in payload:
        min_stock = _parse_min_stock(payload.get("min_stock"))
        if min_stock is None:
            return jsonify({"error": "missing_fields"}), 400
        item.min_stock = min_stock

    if "expiry_tracking" in payload:
        expiry_tracking = payload.get("expiry_tracking")
        if not isinstance(expiry_tracking, bool):
            return jsonify({"error": "missing_fields"}), 400
        item.expiry_tracking = expiry_tracking

    if "sku" in payload:
        sku = payload.get("sku")
        if sku is not None and not isinstance(sku, str):
            return jsonify({"error": "missing_fields"}), 400
        item.sku = (sku.strip() if isinstance(sku, str) else None) or None

    db.session.commit()
    return jsonify(item.to_dict())
