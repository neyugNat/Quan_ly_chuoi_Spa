# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUntypedFunctionDecorator=false, reportUnknownArgumentType=false

from datetime import datetime

from flask import jsonify, request
from flask_jwt_extended import jwt_required

from backend.api import api_bp
from backend.decorators.rbac import require_roles
from backend.extensions import db
from backend.models.shift import Shift
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


def _parse_optional_note(value):
    if value is None:
        return None
    if not isinstance(value, str):
        return _INVALID
    return value


def _validate_staff_in_branch(staff_id, branch_id):
    if isinstance(staff_id, bool) or not isinstance(staff_id, int):
        return False
    staff = Staff.query.filter_by(id=staff_id, branch_id=branch_id).first()
    return staff is not None


@api_bp.get("/shifts")
@jwt_required()
@require_roles("super_admin", "branch_manager")
def list_shifts():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    items = (
        Shift.query.filter(Shift.branch_id == branch_id)
        .order_by(Shift.id.desc())
        .limit(200)
        .all()
    )
    return jsonify({"items": [item.to_dict() for item in items]})


@api_bp.post("/shifts")
@jwt_required()
@require_roles("super_admin", "branch_manager")
def create_shift():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    payload = request.get_json(silent=True) or {}

    staff_id = payload.get("staff_id")
    start_time = _parse_datetime(payload.get("start_time"))
    end_time = _parse_datetime(payload.get("end_time"))

    if staff_id is None or start_time is None or end_time is None or end_time <= start_time:
        return jsonify({"error": "missing_fields"}), 400

    if not _validate_staff_in_branch(staff_id, branch_id):
        return jsonify({"error": "not_found"}), 404

    normalized_status = _normalize_status(payload.get("status"))
    if payload.get("status") is not None and normalized_status is None:
        return jsonify({"error": "invalid_status"}), 400

    note = _parse_optional_note(payload.get("note"))
    if note is _INVALID:
        return jsonify({"error": "missing_fields"}), 400

    shift = Shift(
        branch_id=branch_id,
        staff_id=staff_id,
        start_time=start_time,
        end_time=end_time,
        status=normalized_status or "active",
        note=note,
    )
    db.session.add(shift)
    db.session.commit()
    return jsonify(shift.to_dict()), 201


@api_bp.get("/shifts/<int:shift_id>")
@jwt_required()
@require_roles("super_admin", "branch_manager")
def get_shift(shift_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    shift = Shift.query.filter_by(id=shift_id, branch_id=branch_id).first()
    if not shift:
        return jsonify({"error": "not_found"}), 404
    return jsonify(shift.to_dict())


@api_bp.put("/shifts/<int:shift_id>")
@jwt_required()
@require_roles("super_admin", "branch_manager")
def update_shift(shift_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    shift = Shift.query.filter_by(id=shift_id, branch_id=branch_id).first()
    if not shift:
        return jsonify({"error": "not_found"}), 404

    payload = request.get_json(silent=True) or {}

    if "staff_id" in payload:
        staff_id = payload.get("staff_id")
        if not _validate_staff_in_branch(staff_id, branch_id):
            return jsonify({"error": "not_found"}), 404
        shift.staff_id = staff_id

    if "start_time" in payload:
        start_time = _parse_datetime(payload.get("start_time"))
        if start_time is None:
            return jsonify({"error": "missing_fields"}), 400
        shift.start_time = start_time

    if "end_time" in payload:
        end_time = _parse_datetime(payload.get("end_time"))
        if end_time is None:
            return jsonify({"error": "missing_fields"}), 400
        shift.end_time = end_time

    if shift.end_time <= shift.start_time:
        return jsonify({"error": "missing_fields"}), 400

    if "status" in payload:
        normalized_status = _normalize_status(payload.get("status"))
        if normalized_status is None:
            return jsonify({"error": "invalid_status"}), 400
        shift.status = normalized_status

    if "note" in payload:
        note = _parse_optional_note(payload.get("note"))
        if note is _INVALID:
            return jsonify({"error": "missing_fields"}), 400
        shift.note = note

    db.session.commit()
    return jsonify(shift.to_dict())
