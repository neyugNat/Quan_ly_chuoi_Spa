# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUntypedFunctionDecorator=false, reportUnknownArgumentType=false

from flask import jsonify, request
from flask_jwt_extended import jwt_required

from backend.api import api_bp
from backend.decorators.rbac import require_roles
from backend.extensions import db
from backend.models.staff import Staff
from backend.utils.scoping import get_current_branch_id

_INVALID = object()


def _normalize_status(value):
    if value is None:
        return None
    status = (value or "").strip()
    if status not in {"active", "inactive"}:
        return None
    return status


def _parse_required_text(value):
    if not isinstance(value, str):
        return None
    parsed = value.strip()
    return parsed or None


def _parse_optional_text(value):
    if value is None:
        return None
    if not isinstance(value, str):
        return _INVALID
    return value.strip() or None


def _parse_optional_user_id(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        return _INVALID
    return value


@api_bp.get("/staffs")
@jwt_required()
@require_roles("super_admin", "branch_manager", "reception")
def list_staffs():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    items = (
        Staff.query.filter(Staff.branch_id == branch_id)
        .order_by(Staff.id.desc())
        .limit(200)
        .all()
    )
    return jsonify({"items": [item.to_dict() for item in items]})


@api_bp.post("/staffs")
@jwt_required()
@require_roles("super_admin", "branch_manager")
def create_staff():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    payload = request.get_json(silent=True) or {}
    full_name = _parse_required_text(payload.get("full_name"))
    if not full_name:
        return jsonify({"error": "missing_fields"}), 400

    normalized_status = _normalize_status(payload.get("status"))
    if payload.get("status") is not None and normalized_status is None:
        return jsonify({"error": "invalid_status"}), 400

    user_id = _parse_optional_user_id(payload.get("user_id"))
    if user_id is _INVALID:
        return jsonify({"error": "missing_fields"}), 400

    phone = _parse_optional_text(payload.get("phone"))
    if phone is _INVALID:
        return jsonify({"error": "missing_fields"}), 400

    title = _parse_optional_text(payload.get("title"))
    if title is _INVALID:
        return jsonify({"error": "missing_fields"}), 400

    role = _parse_optional_text(payload.get("role"))
    if role is _INVALID:
        return jsonify({"error": "missing_fields"}), 400

    skill_level = _parse_optional_text(payload.get("skill_level"))
    if skill_level is _INVALID:
        return jsonify({"error": "missing_fields"}), 400

    commission_scheme_json = _parse_optional_text(payload.get("commission_scheme_json"))
    if commission_scheme_json is _INVALID:
        return jsonify({"error": "missing_fields"}), 400

    staff = Staff(
        branch_id=branch_id,
        full_name=full_name,
        phone=phone,
        title=title,
        role=role,
        skill_level=skill_level,
        user_id=user_id,
        commission_scheme_json=commission_scheme_json,
        status=normalized_status or "active",
    )
    db.session.add(staff)
    db.session.commit()
    return jsonify(staff.to_dict()), 201


@api_bp.get("/staffs/<int:staff_id>")
@jwt_required()
@require_roles("super_admin", "branch_manager", "reception")
def get_staff(staff_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    staff = Staff.query.filter_by(id=staff_id, branch_id=branch_id).first()
    if not staff:
        return jsonify({"error": "not_found"}), 404
    return jsonify(staff.to_dict())


@api_bp.put("/staffs/<int:staff_id>")
@jwt_required()
@require_roles("super_admin", "branch_manager")
def update_staff(staff_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    staff = Staff.query.filter_by(id=staff_id, branch_id=branch_id).first()
    if not staff:
        return jsonify({"error": "not_found"}), 404

    payload = request.get_json(silent=True) or {}

    if "full_name" in payload:
        full_name = _parse_required_text(payload.get("full_name"))
        if not full_name:
            return jsonify({"error": "missing_fields"}), 400
        staff.full_name = full_name

    if "status" in payload:
        normalized_status = _normalize_status(payload.get("status"))
        if normalized_status is None:
            return jsonify({"error": "invalid_status"}), 400
        staff.status = normalized_status

    if "phone" in payload:
        phone = _parse_optional_text(payload.get("phone"))
        if phone is _INVALID:
            return jsonify({"error": "missing_fields"}), 400
        staff.phone = phone

    if "title" in payload:
        title = _parse_optional_text(payload.get("title"))
        if title is _INVALID:
            return jsonify({"error": "missing_fields"}), 400
        staff.title = title

    if "role" in payload:
        role = _parse_optional_text(payload.get("role"))
        if role is _INVALID:
            return jsonify({"error": "missing_fields"}), 400
        staff.role = role

    if "skill_level" in payload:
        skill_level = _parse_optional_text(payload.get("skill_level"))
        if skill_level is _INVALID:
            return jsonify({"error": "missing_fields"}), 400
        staff.skill_level = skill_level

    if "user_id" in payload:
        user_id = _parse_optional_user_id(payload.get("user_id"))
        if user_id is _INVALID:
            return jsonify({"error": "missing_fields"}), 400
        staff.user_id = user_id

    if "commission_scheme_json" in payload:
        commission_scheme_json = _parse_optional_text(payload.get("commission_scheme_json"))
        if commission_scheme_json is _INVALID:
            return jsonify({"error": "missing_fields"}), 400
        staff.commission_scheme_json = commission_scheme_json

    db.session.commit()
    return jsonify(staff.to_dict())
