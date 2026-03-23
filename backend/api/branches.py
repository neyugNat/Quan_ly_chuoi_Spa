from flask import jsonify, request
from flask_jwt_extended import jwt_required

from backend.api import api_bp
from backend.decorators.rbac import require_roles
from backend.extensions import db
from backend.models.branch import Branch


def _normalize_status(value):
    if value is None:
        return None
    status = (value or "").strip()
    if status not in {"active", "inactive"}:
        return None
    return status


@api_bp.get("/branches")
@jwt_required()
@require_roles("super_admin")
def list_branches():
    items = Branch.query.order_by(Branch.id.desc()).all()
    return jsonify({"items": [item.to_dict() for item in items]})


@api_bp.post("/branches")
@jwt_required()
@require_roles("super_admin")
def create_branch():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    if not name:
        return jsonify({"error": "missing_fields"}), 400

    status = _normalize_status(payload.get("status"))
    if payload.get("status") is not None and status is None:
        return jsonify({"error": "invalid_status"}), 400

    branch = Branch(
        name=name,
        address=(payload.get("address") or "").strip() or None,
        status=status or "active",
        working_hours_json=payload.get("working_hours_json"),
    )
    db.session.add(branch)
    db.session.commit()
    return jsonify(branch.to_dict()), 201


@api_bp.get("/branches/<int:branch_id>")
@jwt_required()
@require_roles("super_admin")
def get_branch(branch_id: int):
    branch = Branch.query.get(branch_id)
    if not branch:
        return jsonify({"error": "not_found"}), 404
    return jsonify(branch.to_dict())


@api_bp.put("/branches/<int:branch_id>")
@jwt_required()
@require_roles("super_admin")
def update_branch(branch_id: int):
    branch = Branch.query.get(branch_id)
    if not branch:
        return jsonify({"error": "not_found"}), 404

    payload = request.get_json(silent=True) or {}

    if "name" in payload:
        name = (payload.get("name") or "").strip()
        if not name:
            return jsonify({"error": "missing_fields"}), 400
        branch.name = name

    if "address" in payload:
        address = payload.get("address")
        if isinstance(address, str):
            address = address.strip()
        branch.address = address or None

    if "status" in payload:
        status = _normalize_status(payload.get("status"))
        if status is None:
            return jsonify({"error": "invalid_status"}), 400
        branch.status = status

    if "working_hours_json" in payload:
        branch.working_hours_json = payload.get("working_hours_json")

    db.session.commit()
    return jsonify(branch.to_dict())
