from flask import jsonify, request
from flask_jwt_extended import jwt_required

from backend.api import api_bp
from backend.decorators.rbac import require_roles
from backend.models.audit_log import AuditLog


def _parse_int_arg(name, default=None, minimum=None, maximum=None):
    raw = request.args.get(name)
    if raw is None:
        return default, None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None, {"error": f"invalid_{name}"}

    if minimum is not None and value < minimum:
        return None, {"error": f"invalid_{name}"}
    if maximum is not None and value > maximum:
        return None, {"error": f"invalid_{name}"}
    return value, None


@api_bp.get("/audit-logs")
@jwt_required()
@require_roles("super_admin")
def list_audit_logs():
    limit, err = _parse_int_arg("limit", default=200, minimum=1, maximum=500)
    if err:
        return jsonify(err), 400

    user_id, err = _parse_int_arg("user_id")
    if err:
        return jsonify(err), 400

    branch_id, err = _parse_int_arg("branch_id")
    if err:
        return jsonify(err), 400

    action = (request.args.get("action") or "").strip()

    query = AuditLog.query
    if action:
        query = query.filter(AuditLog.action == action)
    if user_id is not None:
        query = query.filter(AuditLog.user_id == user_id)
    if branch_id is not None:
        query = query.filter(AuditLog.branch_id == branch_id)

    items = query.order_by(AuditLog.id.desc()).limit(limit).all()
    return jsonify({"items": [item.to_dict() for item in items]})
