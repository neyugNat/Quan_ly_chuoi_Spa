# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUntypedFunctionDecorator=false, reportUnknownArgumentType=false

from __future__ import annotations

from datetime import datetime, timedelta

from flask import jsonify, request
from flask_jwt_extended import jwt_required

from backend.api import api_bp
from backend.decorators.rbac import require_roles
from backend.extensions import db
from backend.models.customer import Customer
from backend.models.customer_package import CustomerPackage
from backend.models.package import Package
from backend.utils.scoping import get_current_branch_id


def _parse_datetime(value):
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = f"{raw[:-1]}+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _parse_non_negative_int(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return parsed


def _normalize_status(value):
    if value is None:
        return None
    status = (value or "").strip()
    if status not in {"active", "inactive"}:
        return None
    return status


@api_bp.get("/customer-packages")
@jwt_required()
@require_roles("super_admin", "branch_manager", "reception", "cashier")
def list_customer_packages():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    customer_id = request.args.get("customer_id")
    query = CustomerPackage.query.filter(CustomerPackage.branch_id == branch_id)
    if customer_id is not None and str(customer_id).strip():
        try:
            parsed_customer_id = int(str(customer_id).strip())
        except ValueError:
            return jsonify({"error": "invalid_customer_id"}), 400
        query = query.filter(CustomerPackage.customer_id == parsed_customer_id)

    items = query.order_by(CustomerPackage.id.desc()).limit(200).all()
    return jsonify({"items": [item.to_dict() for item in items]})


@api_bp.post("/customer-packages")
@jwt_required()
@require_roles("super_admin", "branch_manager", "reception", "cashier")
def create_customer_package():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    payload = request.get_json(silent=True) or {}
    customer_id = payload.get("customer_id")
    package_id = payload.get("package_id")
    if customer_id is None or package_id is None:
        return jsonify({"error": "missing_fields"}), 400

    customer = Customer.query.filter_by(id=customer_id, branch_id=branch_id).first()
    if not customer:
        return jsonify({"error": "not_found"}), 404

    package = Package.query.filter_by(id=package_id, branch_id=branch_id).first()
    if not package:
        return jsonify({"error": "not_found"}), 404

    sessions_total = int(package.sessions_total)
    expires_at = None
    if package.validity_days is not None:
        try:
            days = int(package.validity_days)
        except (TypeError, ValueError):
            days = None
        if days and days > 0:
            expires_at = datetime.now() + timedelta(days=days)

    normalized_status = _normalize_status(payload.get("status"))
    if payload.get("status") is not None and normalized_status is None:
        return jsonify({"error": "invalid_status"}), 400

    customer_package = CustomerPackage(
        branch_id=branch_id,
        customer_id=customer.id,
        package_id=package.id,
        sessions_total=sessions_total,
        sessions_remaining=sessions_total,
        expires_at=expires_at,
        status=normalized_status or "active",
    )
    db.session.add(customer_package)
    db.session.commit()
    return jsonify(customer_package.to_dict()), 201


@api_bp.get("/customer-packages/<int:customer_package_id>")
@jwt_required()
@require_roles("super_admin", "branch_manager", "reception", "cashier")
def get_customer_package(customer_package_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    row = CustomerPackage.query.filter_by(id=customer_package_id, branch_id=branch_id).first()
    if not row:
        return jsonify({"error": "not_found"}), 404
    return jsonify(row.to_dict())


@api_bp.put("/customer-packages/<int:customer_package_id>")
@jwt_required()
@require_roles("super_admin", "branch_manager")
def update_customer_package(customer_package_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    row = CustomerPackage.query.filter_by(id=customer_package_id, branch_id=branch_id).first()
    if not row:
        return jsonify({"error": "not_found"}), 404

    payload = request.get_json(silent=True) or {}

    if "status" in payload:
        normalized = _normalize_status(payload.get("status"))
        if normalized is None:
            return jsonify({"error": "invalid_status"}), 400
        row.status = normalized

    if "sessions_remaining" in payload:
        parsed = _parse_non_negative_int(payload.get("sessions_remaining"))
        if parsed is None:
            return jsonify({"error": "missing_fields"}), 400
        if parsed > row.sessions_total:
            return jsonify({"error": "invalid_sessions_remaining"}), 400
        row.sessions_remaining = parsed

    if "expires_at" in payload:
        raw = payload.get("expires_at")
        if raw is None:
            row.expires_at = None
        else:
            parsed = _parse_datetime(raw)
            if parsed is None:
                return jsonify({"error": "invalid_expires_at"}), 400
            row.expires_at = parsed

    db.session.commit()
    return jsonify(row.to_dict())
