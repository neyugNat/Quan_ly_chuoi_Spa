# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUntypedFunctionDecorator=false, reportUnknownArgumentType=false

from __future__ import annotations

import json

from flask import jsonify, request
from flask_jwt_extended import jwt_required

from backend.api import api_bp
from backend.decorators.rbac import require_roles
from backend.extensions import db
from backend.models.package import Package
from backend.utils.scoping import get_current_branch_id


def _normalize_status(value):
    if value is None:
        return None
    status = (value or "").strip()
    if status not in {"active", "inactive"}:
        return None
    return status


def _parse_positive_int(value):
    if value is None:
        return None
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
    if parsed <= 0:
        return None
    return parsed


def _normalize_allowed_branches_json(value):
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    try:
        return json.dumps(value, ensure_ascii=True)
    except (TypeError, ValueError):
        return None


@api_bp.get("/packages")
@jwt_required()
@require_roles("super_admin", "branch_manager")
def list_packages():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    items = (
        Package.query.filter(Package.branch_id == branch_id)
        .order_by(Package.id.desc())
        .limit(200)
        .all()
    )
    return jsonify({"items": [item.to_dict() for item in items]})


@api_bp.post("/packages")
@jwt_required()
@require_roles("super_admin", "branch_manager")
def create_package():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    sessions_total = _parse_positive_int(payload.get("sessions_total"))
    if not name or sessions_total is None:
        return jsonify({"error": "missing_fields"}), 400

    normalized_status = _normalize_status(payload.get("status"))
    if payload.get("status") is not None and normalized_status is None:
        return jsonify({"error": "invalid_status"}), 400

    validity_days = None
    if "validity_days" in payload:
        raw_validity_days = payload.get("validity_days")
        if raw_validity_days is None:
            validity_days = None
        else:
            validity_days = _parse_positive_int(raw_validity_days)
            if validity_days is None:
                return jsonify({"error": "missing_fields"}), 400

    allowed_branches_json = _normalize_allowed_branches_json(
        payload.get("allowed_branches_json")
    )
    if "allowed_branches_json" in payload and payload.get("allowed_branches_json") is not None:
        if allowed_branches_json is None:
            return jsonify({"error": "missing_fields"}), 400

    package = Package(
        branch_id=branch_id,
        name=name,
        sessions_total=sessions_total,
        validity_days=validity_days,
        shareable=bool(payload.get("shareable", False)),
        allowed_branches_json=allowed_branches_json,
        status=normalized_status or "active",
    )
    db.session.add(package)
    db.session.commit()
    return jsonify(package.to_dict()), 201


@api_bp.get("/packages/<int:package_id>")
@jwt_required()
@require_roles("super_admin", "branch_manager")
def get_package(package_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    package = Package.query.filter_by(id=package_id, branch_id=branch_id).first()
    if not package:
        return jsonify({"error": "not_found"}), 404
    return jsonify(package.to_dict())


@api_bp.put("/packages/<int:package_id>")
@jwt_required()
@require_roles("super_admin", "branch_manager")
def update_package(package_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    package = Package.query.filter_by(id=package_id, branch_id=branch_id).first()
    if not package:
        return jsonify({"error": "not_found"}), 404

    payload = request.get_json(silent=True) or {}

    if "name" in payload:
        name = (payload.get("name") or "").strip()
        if not name:
            return jsonify({"error": "missing_fields"}), 400
        package.name = name

    if "sessions_total" in payload:
        sessions_total = _parse_positive_int(payload.get("sessions_total"))
        if sessions_total is None:
            return jsonify({"error": "missing_fields"}), 400
        package.sessions_total = sessions_total

    if "validity_days" in payload:
        raw_validity_days = payload.get("validity_days")
        if raw_validity_days is None:
            package.validity_days = None
        else:
            validity_days = _parse_positive_int(raw_validity_days)
            if validity_days is None:
                return jsonify({"error": "missing_fields"}), 400
            package.validity_days = validity_days

    if "shareable" in payload:
        package.shareable = bool(payload.get("shareable"))

    if "allowed_branches_json" in payload:
        normalized = _normalize_allowed_branches_json(payload.get("allowed_branches_json"))
        if payload.get("allowed_branches_json") is not None and normalized is None:
            return jsonify({"error": "missing_fields"}), 400
        package.allowed_branches_json = normalized

    if "status" in payload:
        normalized_status = _normalize_status(payload.get("status"))
        if normalized_status is None:
            return jsonify({"error": "invalid_status"}), 400
        package.status = normalized_status

    db.session.commit()
    return jsonify(package.to_dict())
