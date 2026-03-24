# pyright: reportMissingImports=false

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from backend.api import api_bp
from backend.decorators.rbac import require_roles
from backend.extensions import db
from backend.models.audit_log import AuditLog
from backend.models.branch import Branch
from backend.models.staff import Staff
from backend.models.user import Role, User


def _audit(user_id, action, entity=None, before=None, after=None):
    db.session.add(
        AuditLog(
            user_id=user_id,
            branch_id=None,
            action=action,
            entity=entity,
            before_json=AuditLog.dumps(before),
            after_json=AuditLog.dumps(after),
        )
    )


def _parse_required_text(value):
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _parse_optional_bool(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    return None


def _parse_role_names(value):
    if value is None:
        return []
    if isinstance(value, list):
        result = []
        for item in value:
            if not isinstance(item, str):
                return None
            name = item.strip()
            if name:
                result.append(name)
        return result
    if isinstance(value, str):
        names = [v.strip() for v in value.split(",")]
        return [n for n in names if n]
    return None


def _parse_branch_ids(value):
    if value is None:
        return []
    if isinstance(value, list):
        result = []
        for item in value:
            try:
                parsed = int(item)
            except (TypeError, ValueError):
                return None
            result.append(parsed)
        return result
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        parts = [p.strip() for p in text.split(",")]
        result = []
        for part in parts:
            if not part:
                continue
            try:
                result.append(int(part))
            except ValueError:
                return None
        return result
    return None


@api_bp.get("/roles")
@jwt_required()
@require_roles("super_admin")
def list_roles():
    items = Role.query.order_by(Role.name.asc()).all()
    return jsonify({"items": [item.to_dict() for item in items]})


@api_bp.get("/users")
@jwt_required()
@require_roles("super_admin")
def list_users():
    q = (request.args.get("q") or "").strip().lower()
    query = User.query
    if q:
        query = query.filter(User.username.ilike(f"%{q}%"))
    items = query.order_by(User.id.desc()).limit(500).all()
    return jsonify({"items": [item.to_dict() for item in items]})


@api_bp.post("/users")
@jwt_required()
@require_roles("super_admin")
def create_user():
    payload = request.get_json(silent=True) or {}
    username = _parse_required_text(payload.get("username"))
    password = payload.get("password") or ""
    if not username or not isinstance(password, str) or not password:
        return jsonify({"error": "missing_fields"}), 400

    role_names = _parse_role_names(payload.get("role_names"))
    if role_names is None or not role_names:
        return jsonify({"error": "missing_fields"}), 400

    branch_ids = _parse_branch_ids(payload.get("branch_ids"))
    if branch_ids is None:
        return jsonify({"error": "missing_fields"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "username_taken"}), 400

    roles = Role.query.filter(Role.name.in_(role_names)).all()
    if len(roles) != len(set(role_names)):
        return jsonify({"error": "invalid_role"}), 400

    branches = []
    if branch_ids:
        branches = Branch.query.filter(Branch.id.in_(branch_ids)).all()
        if len(branches) != len(set(branch_ids)):
            return jsonify({"error": "invalid_branch"}), 400

    is_active = _parse_optional_bool(payload.get("is_active"))

    user = User(username=username, is_active=True if is_active is None else bool(is_active))
    user.set_password(password)
    user.roles = roles
    user.branches = branches
    db.session.add(user)
    db.session.flush()

    actor_user_id = int(get_jwt_identity())
    _audit(actor_user_id, "user.create", entity="User", after=user.to_dict())
    db.session.commit()
    return jsonify(user.to_dict()), 201


@api_bp.get("/users/<int:user_id>")
@jwt_required()
@require_roles("super_admin")
def get_user(user_id: int):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "not_found"}), 404
    return jsonify(user.to_dict())


@api_bp.put("/users/<int:user_id>")
@jwt_required()
@require_roles("super_admin")
def update_user(user_id: int):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "not_found"}), 404

    payload = request.get_json(silent=True) or {}
    before_state = user.to_dict()

    if "username" in payload:
        username = _parse_required_text(payload.get("username"))
        if not username:
            return jsonify({"error": "missing_fields"}), 400
        existing = User.query.filter_by(username=username).first()
        if existing and existing.id != user.id:
            return jsonify({"error": "username_taken"}), 400
        user.username = username

    if "is_active" in payload:
        is_active = _parse_optional_bool(payload.get("is_active"))
        if is_active is None:
            return jsonify({"error": "missing_fields"}), 400
        user.is_active = bool(is_active)

    if "role_names" in payload:
        role_names = _parse_role_names(payload.get("role_names"))
        if role_names is None or not role_names:
            return jsonify({"error": "missing_fields"}), 400
        roles = Role.query.filter(Role.name.in_(role_names)).all()
        if len(roles) != len(set(role_names)):
            return jsonify({"error": "invalid_role"}), 400
        user.roles = roles

    if "branch_ids" in payload:
        branch_ids = _parse_branch_ids(payload.get("branch_ids"))
        if branch_ids is None:
            return jsonify({"error": "missing_fields"}), 400
        branches = []
        if branch_ids:
            branches = Branch.query.filter(Branch.id.in_(branch_ids)).all()
            if len(branches) != len(set(branch_ids)):
                return jsonify({"error": "invalid_branch"}), 400
        user.branches = branches

    actor_user_id = int(get_jwt_identity())
    _audit(
        actor_user_id,
        "user.update",
        entity="User",
        before=before_state,
        after=user.to_dict(),
    )
    db.session.commit()
    return jsonify(user.to_dict())


@api_bp.post("/users/<int:user_id>/set-password")
@jwt_required()
@require_roles("super_admin")
def set_user_password(user_id: int):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "not_found"}), 404

    payload = request.get_json(silent=True) or {}
    new_password = payload.get("new_password") or ""
    if not isinstance(new_password, str) or not new_password:
        return jsonify({"error": "missing_fields"}), 400

    user.set_password(new_password)
    user.reset_password_token = None
    user.reset_password_expires_at = None

    actor_user_id = int(get_jwt_identity())
    _audit(
        actor_user_id,
        "user.set_password",
        entity="User",
        before={"target_user_id": user.id},
        after={"target_user_id": user.id},
    )
    db.session.commit()
    return jsonify({"status": "ok", "user": user.to_dict()})


@api_bp.delete("/users/<int:user_id>")
@jwt_required()
@require_roles("super_admin")
def delete_user(user_id: int):
    actor_user_id = int(get_jwt_identity())
    if actor_user_id == user_id:
        return jsonify({"error": "cannot_delete_self"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "not_found"}), 404

    if user.username == "admin":
        return jsonify({"error": "protected_user"}), 400

    before_state = user.to_dict()

    Staff.query.filter(Staff.user_id == user.id).update({"user_id": None})
    user.roles = []
    user.branches = []
    db.session.flush()
    db.session.delete(user)

    _audit(actor_user_id, "user.delete", entity="User", before=before_state)
    db.session.commit()
    return jsonify({"status": "ok"})
