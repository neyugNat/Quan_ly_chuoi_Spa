from flask import jsonify, request
from flask_jwt_extended import jwt_required

from backend.api import api_bp
from backend.decorators.rbac import require_roles
from backend.extensions import db
from backend.models.resource import Resource
from backend.utils.scoping import get_current_branch_id


def _normalize_status(value):
    if value is None:
        return None
    status = (value or "").strip()
    if status not in {"active", "inactive"}:
        return None
    return status


@api_bp.get("/resources")
@jwt_required()
@require_roles("super_admin", "branch_manager", "reception")
def list_resources():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    items = (
        Resource.query.filter(Resource.branch_id == branch_id)
        .order_by(Resource.id.desc())
        .limit(200)
        .all()
    )
    return jsonify({"items": [item.to_dict() for item in items]})


@api_bp.post("/resources")
@jwt_required()
@require_roles("super_admin", "branch_manager")
def create_resource():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    resource_type = (payload.get("resource_type") or "").strip()
    if not name or not resource_type:
        return jsonify({"error": "missing_fields"}), 400

    normalized_status = _normalize_status(payload.get("status"))
    if payload.get("status") is not None and normalized_status is None:
        return jsonify({"error": "invalid_status"}), 400

    resource = Resource(
        branch_id=branch_id,
        name=name,
        resource_type=resource_type,
        code=(payload.get("code") or "").strip() or None,
        maintenance_flag=bool(payload.get("maintenance_flag", False)),
        status=normalized_status or "active",
        note=(payload.get("note") or None),
    )
    db.session.add(resource)
    db.session.commit()
    return jsonify(resource.to_dict()), 201


@api_bp.get("/resources/<int:resource_id>")
@jwt_required()
@require_roles("super_admin", "branch_manager", "reception")
def get_resource(resource_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    resource = Resource.query.filter_by(id=resource_id, branch_id=branch_id).first()
    if not resource:
        return jsonify({"error": "not_found"}), 404
    return jsonify(resource.to_dict())


@api_bp.put("/resources/<int:resource_id>")
@jwt_required()
@require_roles("super_admin", "branch_manager")
def update_resource(resource_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    resource = Resource.query.filter_by(id=resource_id, branch_id=branch_id).first()
    if not resource:
        return jsonify({"error": "not_found"}), 404

    payload = request.get_json(silent=True) or {}

    if "name" in payload:
        name = (payload.get("name") or "").strip()
        if not name:
            return jsonify({"error": "missing_fields"}), 400
        resource.name = name

    if "resource_type" in payload:
        resource_type = (payload.get("resource_type") or "").strip()
        if not resource_type:
            return jsonify({"error": "missing_fields"}), 400
        resource.resource_type = resource_type

    if "status" in payload:
        normalized_status = _normalize_status(payload.get("status"))
        if normalized_status is None:
            return jsonify({"error": "invalid_status"}), 400
        resource.status = normalized_status

    if "code" in payload:
        code = payload.get("code")
        if isinstance(code, str):
            code = code.strip()
        resource.code = code or None

    if "note" in payload:
        resource.note = payload.get("note") or None

    if "maintenance_flag" in payload:
        resource.maintenance_flag = bool(payload.get("maintenance_flag"))

    db.session.commit()
    return jsonify(resource.to_dict())
