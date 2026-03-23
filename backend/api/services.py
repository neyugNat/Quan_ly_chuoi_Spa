# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUntypedFunctionDecorator=false, reportUnknownArgumentType=false

from decimal import Decimal, InvalidOperation

from flask import jsonify, request
from flask_jwt_extended import jwt_required

from backend.api import api_bp
from backend.decorators.rbac import require_roles
from backend.extensions import db
from backend.models.service import Service
from backend.utils.scoping import get_current_branch_id


def _normalize_status(value):
    if value is None:
        return None
    status = (value or "").strip()
    if status not in {"active", "inactive"}:
        return None
    return status


def _parse_price(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
    try:
        price = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if price < 0:
        return None
    return price


def _parse_duration_minutes(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
    try:
        duration = int(value)
    except (ValueError, TypeError):
        return None
    if duration <= 0:
        return None
    return duration


@api_bp.get("/services")
@jwt_required()
@require_roles("super_admin", "branch_manager")
def list_services():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    items = (
        Service.query.filter(Service.branch_id == branch_id)
        .order_by(Service.id.desc())
        .limit(200)
        .all()
    )
    return jsonify({"items": [item.to_dict() for item in items]})


@api_bp.post("/services")
@jwt_required()
@require_roles("super_admin", "branch_manager")
def create_service():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    price = _parse_price(payload.get("price"))
    duration_minutes = _parse_duration_minutes(payload.get("duration_minutes"))
    if not name or price is None or duration_minutes is None:
        return jsonify({"error": "missing_fields"}), 400

    normalized_status = _normalize_status(payload.get("status"))
    if payload.get("status") is not None and normalized_status is None:
        return jsonify({"error": "invalid_status"}), 400

    service = Service(
        branch_id=branch_id,
        name=name,
        price=price,
        duration_minutes=duration_minutes,
        requirement_json=payload.get("requirement_json") or None,
        consumable_recipe_json=payload.get("consumable_recipe_json") or None,
        status=normalized_status or "active",
    )
    db.session.add(service)
    db.session.commit()
    return jsonify(service.to_dict()), 201


@api_bp.get("/services/<int:service_id>")
@jwt_required()
@require_roles("super_admin", "branch_manager")
def get_service(service_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    service = Service.query.filter_by(id=service_id, branch_id=branch_id).first()
    if not service:
        return jsonify({"error": "not_found"}), 404
    return jsonify(service.to_dict())


@api_bp.put("/services/<int:service_id>")
@jwt_required()
@require_roles("super_admin", "branch_manager")
def update_service(service_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    service = Service.query.filter_by(id=service_id, branch_id=branch_id).first()
    if not service:
        return jsonify({"error": "not_found"}), 404

    payload = request.get_json(silent=True) or {}

    if "name" in payload:
        name = (payload.get("name") or "").strip()
        if not name:
            return jsonify({"error": "missing_fields"}), 400
        service.name = name

    if "price" in payload:
        price = _parse_price(payload.get("price"))
        if price is None:
            return jsonify({"error": "missing_fields"}), 400
        service.price = price

    if "duration_minutes" in payload:
        duration_minutes = _parse_duration_minutes(payload.get("duration_minutes"))
        if duration_minutes is None:
            return jsonify({"error": "missing_fields"}), 400
        service.duration_minutes = duration_minutes

    if "status" in payload:
        normalized_status = _normalize_status(payload.get("status"))
        if normalized_status is None:
            return jsonify({"error": "invalid_status"}), 400
        service.status = normalized_status

    if "requirement_json" in payload:
        service.requirement_json = payload.get("requirement_json") or None

    if "consumable_recipe_json" in payload:
        service.consumable_recipe_json = payload.get("consumable_recipe_json") or None

    db.session.commit()
    return jsonify(service.to_dict())
