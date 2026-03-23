# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUntypedFunctionDecorator=false, reportUnknownArgumentType=false

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
import json
from typing import cast

from flask import jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from sqlalchemy import func, or_

from backend.api import api_bp
from backend.decorators.rbac import require_roles
from backend.extensions import db
from backend.models.appointment import Appointment
from backend.models.audit_log import AuditLog
from backend.models.customer import Customer
from backend.models.customer_package import CustomerPackage
from backend.models.inventory_item import InventoryItem
from backend.models.resource import Resource
from backend.models.service import Service
from backend.models.staff import Staff
from backend.models.stock_transaction import StockTransaction
from backend.models.treatment_note import TreatmentNote
from backend.utils.scoping import get_current_branch_id

ALLOWED_STATUS = {
    "booked",
    "confirmed",
    "arrived",
    "in_service",
    "completed",
    "paid",
    "cancelled",
    "no_show",
}

CONFLICT_CHECK_STATUSES = {"booked", "confirmed", "arrived", "in_service"}

STATUS_TRANSITIONS = {
    "booked": {"confirmed", "cancelled", "no_show"},
    "confirmed": {"arrived", "cancelled", "no_show"},
    "arrived": {"in_service", "cancelled"},
    "in_service": {"completed"},
    "completed": {"paid"},
    "paid": set(),
    "cancelled": set(),
    "no_show": set(),
}


def _audit(user_id, branch_id, action, entity=None, before=None, after=None):
    log = AuditLog(
        user_id=user_id,
        branch_id=branch_id,
        action=action,
        entity=entity,
        before_json=AuditLog.dumps(before),
        after_json=AuditLog.dumps(after),
    )
    db.session.add(log)


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


def _parse_positive_int(value):
    parsed = _parse_non_negative_int(value)
    if parsed is None:
        return None
    if parsed <= 0:
        return None
    return parsed


def _parse_status(value):
    if value is None:
        return None
    status = (value or "").strip()
    if status not in ALLOWED_STATUS:
        return None
    return status


def _validate_time_range(start_time, end_time):
    return start_time is not None and end_time is not None and end_time > start_time


def _validate_branch_fk(model, ref_id, branch_id):
    row = model.query.filter_by(id=ref_id).first()
    if not row:
        return False, "not_found"
    if row.branch_id != branch_id:
        return False, "forbidden_branch"
    return True, None


def _effective_window(start_time, end_time, buffer_before_minutes, buffer_after_minutes):
    buffer_before = timedelta(minutes=buffer_before_minutes or 0)
    buffer_after = timedelta(minutes=buffer_after_minutes or 0)
    return start_time - buffer_before, end_time + buffer_after


def _detect_conflicts(
    *,
    branch_id,
    start_time,
    end_time,
    buffer_before_minutes,
    buffer_after_minutes,
    staff_id,
    resource_id,
    exclude_appointment_id=None,
):
    if staff_id is None and resource_id is None:
        return []

    query = Appointment.query.filter(
        Appointment.branch_id == branch_id,
        Appointment.status.in_(CONFLICT_CHECK_STATUSES),
    )
    if exclude_appointment_id is not None:
        query = query.filter(Appointment.id != exclude_appointment_id)

    matches = []
    if staff_id is not None:
        matches.append(Appointment.staff_id == staff_id)
    if resource_id is not None:
        matches.append(Appointment.resource_id == resource_id)

    query = query.filter(or_(*matches)).order_by(Appointment.id.asc())

    new_effective_start, new_effective_end = _effective_window(
        start_time,
        end_time,
        buffer_before_minutes,
        buffer_after_minutes,
    )

    conflicts = []
    for existing in query.all():
        existing_effective_start, existing_effective_end = _effective_window(
            existing.start_time,
            existing.end_time,
            existing.buffer_before_minutes,
            existing.buffer_after_minutes,
        )
        if not (
            existing_effective_start < new_effective_end
            and existing_effective_end > new_effective_start
        ):
            continue

        if staff_id is not None and existing.staff_id == staff_id:
            conflicts.append({"appointment_id": existing.id, "kind": "staff"})
        if resource_id is not None and existing.resource_id == resource_id:
            conflicts.append({"appointment_id": existing.id, "kind": "resource"})

    return conflicts


def _current_user_id():
    identity = cast(str | int, get_jwt_identity())
    return int(identity)


def _current_roles():
    claims = get_jwt() or {}
    roles = claims.get("roles") or []
    if not isinstance(roles, list):
        return []
    return [str(r) for r in roles]


def _is_technician_only():
    roles = _current_roles()
    if "technician" not in roles:
        return False
    return not any(r in roles for r in ("super_admin", "branch_manager", "reception"))


def _technician_staff(branch_id: int):
    user_id = _current_user_id()
    return Staff.query.filter_by(branch_id=branch_id, user_id=user_id).first()


def _enforce_technician_scope(appointment: Appointment, branch_id: int):
    if not _is_technician_only():
        return None
    staff = _technician_staff(branch_id)
    if staff is None or appointment.staff_id != staff.id:
        return {"error": "forbidden"}, 403
    return None


def _parse_decimal_qty(value):
    if isinstance(value, bool):
        return None
    try:
        qty = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if qty <= Decimal("0"):
        return None
    return qty


def _parse_consumable_recipe(recipe_json):
    if recipe_json is None:
        return []
    if not isinstance(recipe_json, str):
        return None
    raw = recipe_json.strip()
    if not raw:
        return []
    try:
        parsed_raw = cast(object, json.loads(raw))
    except json.JSONDecodeError:
        return None

    items = parsed_raw
    if isinstance(parsed_raw, dict):
        parsed_object = cast(dict[str, object], parsed_raw)
        items = parsed_object.get("consumables", [])

    if not isinstance(items, list):
        return None

    normalized = []
    for item in items:
        if not isinstance(item, dict):
            return None
        sku = item.get("sku")
        qty = _parse_decimal_qty(item.get("qty"))
        if not isinstance(sku, str) or not sku.strip() or qty is None:
            return None
        normalized.append({"sku": sku.strip(), "qty": qty})

    return normalized


@api_bp.get("/appointments")
@jwt_required()
@require_roles("super_admin", "branch_manager", "reception", "technician")
def list_appointments():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    query = Appointment.query.filter(Appointment.branch_id == branch_id)
    if _is_technician_only():
        staff = _technician_staff(branch_id)
        if staff is None:
            return jsonify({"items": []})
        query = query.filter(Appointment.staff_id == staff.id)

    items = (
        query
        .order_by(Appointment.start_time.desc())
        .limit(200)
        .all()
    )
    return jsonify({"items": [item.to_dict() for item in items]})


@api_bp.post("/appointments")
@jwt_required()
@require_roles("super_admin", "branch_manager", "reception")
def create_appointment():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    payload = request.get_json(silent=True) or {}

    customer_id = payload.get("customer_id")
    start_time = _parse_datetime(payload.get("start_time"))
    end_time = _parse_datetime(payload.get("end_time"))
    if customer_id is None or start_time is None or end_time is None:
        return jsonify({"error": "missing_fields"}), 400
    if not _validate_time_range(start_time, end_time):
        return jsonify({"error": "invalid_time_range"}), 400

    customer_ok, customer_error = _validate_branch_fk(Customer, customer_id, branch_id)
    if not customer_ok:
        if customer_error == "forbidden_branch":
            return jsonify({"error": "forbidden_branch"}), 403
        return jsonify({"error": "not_found"}), 404

    sessions_used = 1
    if "sessions_used" in payload:
        parsed_sessions_used = _parse_positive_int(payload.get("sessions_used"))
        if parsed_sessions_used is None:
            return jsonify({"error": "invalid_sessions_used"}), 400
        sessions_used = parsed_sessions_used

    customer_package_id = None
    if "customer_package_id" in payload:
        raw_customer_package_id = payload.get("customer_package_id")
        if raw_customer_package_id is None:
            customer_package_id = None
        else:
            try:
                parsed_customer_package_id = int(raw_customer_package_id)
            except (TypeError, ValueError):
                return jsonify({"error": "missing_fields"}), 400
            customer_package = CustomerPackage.query.filter_by(
                id=parsed_customer_package_id,
                branch_id=branch_id,
            ).first()
            if not customer_package or customer_package.customer_id != customer_id:
                return jsonify({"error": "not_found"}), 404
            if customer_package.status != "active":
                return jsonify({"error": "inactive_package"}), 400
            if customer_package.expires_at is not None and customer_package.expires_at <= datetime.now():
                return jsonify({"error": "package_expired"}), 400
            if customer_package.sessions_remaining is None or customer_package.sessions_remaining < sessions_used:
                return jsonify({"error": "insufficient_sessions"}), 400
            customer_package_id = customer_package.id

    for field_name, model in (("service_id", Service), ("staff_id", Staff), ("resource_id", Resource)):
        if field_name not in payload:
            continue
        ref_id = payload.get(field_name)
        if ref_id is None:
            continue
        ok, fk_error = _validate_branch_fk(model, ref_id, branch_id)
        if not ok:
            if fk_error == "forbidden_branch":
                return jsonify({"error": "forbidden_branch"}), 403
            return jsonify({"error": "not_found"}), 404

    buffer_before = 0
    if "buffer_before_minutes" in payload:
        buffer_before = _parse_non_negative_int(payload.get("buffer_before_minutes"))
        if buffer_before is None:
            return jsonify({"error": "invalid_buffer"}), 400

    buffer_after = 0
    if "buffer_after_minutes" in payload:
        buffer_after = _parse_non_negative_int(payload.get("buffer_after_minutes"))
        if buffer_after is None:
            return jsonify({"error": "invalid_buffer"}), 400

    normalized_status = _parse_status(payload.get("status"))
    if "status" in payload and normalized_status is None:
        return jsonify({"error": "invalid_status"}), 400

    conflicts = _detect_conflicts(
        branch_id=branch_id,
        start_time=start_time,
        end_time=end_time,
        buffer_before_minutes=buffer_before,
        buffer_after_minutes=buffer_after,
        staff_id=payload.get("staff_id"),
        resource_id=payload.get("resource_id"),
    )
    if conflicts:
        return jsonify({"error": "conflict", "conflicts": conflicts}), 409

    appointment = Appointment(
        branch_id=branch_id,
        customer_id=customer_id,
        customer_package_id=customer_package_id,
        service_id=payload.get("service_id"),
        staff_id=payload.get("staff_id"),
        resource_id=payload.get("resource_id"),
        start_time=start_time,
        end_time=end_time,
        buffer_before_minutes=buffer_before,
        buffer_after_minutes=buffer_after,
        status=normalized_status or "booked",
        sessions_used=sessions_used,
        note=payload.get("note") or None,
    )
    db.session.add(appointment)
    db.session.flush()

    user_id = _current_user_id()
    _audit(user_id, branch_id, "appointment.create", entity="Appointment", after=appointment.to_dict())
    db.session.commit()
    return jsonify(appointment.to_dict()), 201


@api_bp.get("/appointments/<int:appointment_id>")
@jwt_required()
@require_roles("super_admin", "branch_manager", "reception", "technician")
def get_appointment(appointment_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    appointment = Appointment.query.filter_by(id=appointment_id, branch_id=branch_id).first()
    if not appointment:
        return jsonify({"error": "not_found"}), 404
    scope = _enforce_technician_scope(appointment, branch_id)
    if scope is not None:
        err, st = scope
        return jsonify(err), st
    return jsonify(appointment.to_dict())


@api_bp.post("/appointments/<int:appointment_id>/check-in")
@jwt_required()
@require_roles("super_admin", "branch_manager", "reception", "technician")
def check_in_appointment(appointment_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    appointment = Appointment.query.filter_by(id=appointment_id, branch_id=branch_id).first()
    if not appointment:
        return jsonify({"error": "not_found"}), 404

    scope = _enforce_technician_scope(appointment, branch_id)
    if scope is not None:
        err, st = scope
        return jsonify(err), st

    if appointment.status not in {"booked", "confirmed", "arrived"}:
        return jsonify({"error": "invalid_status_transition"}), 400

    before = {
        "id": appointment.id,
        "status": appointment.status,
        "service_started_at": appointment.service_started_at.isoformat()
        if appointment.service_started_at
        else None,
    }

    appointment.status = "in_service"
    if appointment.service_started_at is None:
        appointment.service_started_at = datetime.now()

    user_id = _current_user_id()
    _audit(
        user_id,
        branch_id,
        "appointment.check_in",
        entity="Appointment",
        before=before,
        after={
            "id": appointment.id,
            "status": appointment.status,
            "service_started_at": appointment.service_started_at.isoformat()
            if appointment.service_started_at
            else None,
        },
    )
    db.session.commit()
    return jsonify(appointment.to_dict())


@api_bp.post("/appointments/<int:appointment_id>/check-out")
@jwt_required()
@require_roles("super_admin", "branch_manager", "reception", "technician")
def check_out_appointment(appointment_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    appointment = Appointment.query.filter_by(id=appointment_id, branch_id=branch_id).first()
    if not appointment:
        return jsonify({"error": "not_found"}), 404

    scope = _enforce_technician_scope(appointment, branch_id)
    if scope is not None:
        err, st = scope
        return jsonify(err), st

    if appointment.status == "completed" and appointment.service_completed_at is not None:
        return jsonify({"error": "already_completed"}), 400

    if appointment.status != "in_service":
        return jsonify({"error": "invalid_status_transition"}), 400

    sessions_used = appointment.sessions_used if appointment.sessions_used is not None else 1
    customer_package = None
    if appointment.customer_package_id is not None:
        if sessions_used <= 0:
            return jsonify({"error": "insufficient_sessions"}), 400
        customer_package = CustomerPackage.query.filter_by(
            id=appointment.customer_package_id,
            branch_id=branch_id,
        ).first()
        if (
            customer_package is None
            or customer_package.sessions_remaining is None
            or customer_package.sessions_remaining < sessions_used
        ):
            return jsonify({"error": "insufficient_sessions"}), 400

    inventory_deductions = []
    if appointment.service_id is not None:
        service = Service.query.filter_by(id=appointment.service_id, branch_id=branch_id).first()
        recipe_items = _parse_consumable_recipe(
            service.consumable_recipe_json if service else None
        )
        if recipe_items is None:
            return jsonify({"error": "invalid_consumable_recipe"}), 400

        for recipe_item in recipe_items:
            inventory_item = InventoryItem.query.filter_by(
                branch_id=branch_id,
                sku=recipe_item["sku"],
            ).first()
            if inventory_item is None:
                return jsonify({"error": "unknown_sku"}), 400
            current_stock = db.session.query(
                func.coalesce(func.sum(StockTransaction.delta_qty), Decimal("0"))
            ).filter(
                StockTransaction.branch_id == branch_id,
                StockTransaction.inventory_item_id == inventory_item.id,
            ).scalar()
            current_stock = current_stock if current_stock is not None else Decimal("0")
            delta_qty = -recipe_item["qty"]
            if current_stock + delta_qty < Decimal("0"):
                return jsonify({"error": "insufficient_stock"}), 400
            inventory_deductions.append((inventory_item, delta_qty))

    before = {
        "id": appointment.id,
        "status": appointment.status,
        "service_completed_at": appointment.service_completed_at.isoformat()
        if appointment.service_completed_at
        else None,
    }

    appointment.status = "completed"
    if appointment.service_completed_at is None:
        appointment.service_completed_at = datetime.now()

    if customer_package is not None:
        customer_package.sessions_remaining -= sessions_used

    for inventory_item, delta_qty in inventory_deductions:
        db.session.add(
            StockTransaction(
                branch_id=branch_id,
                inventory_item_id=inventory_item.id,
                transaction_type="out",
                delta_qty=delta_qty,
                source_type="appointment",
                source_id=appointment.id,
            )
        )

    user_id = _current_user_id()
    _audit(
        user_id,
        branch_id,
        "appointment.check_out",
        entity="Appointment",
        before=before,
        after={
            "id": appointment.id,
            "status": appointment.status,
            "service_completed_at": appointment.service_completed_at.isoformat()
            if appointment.service_completed_at
            else None,
        },
    )
    db.session.commit()
    return jsonify(appointment.to_dict())


@api_bp.get("/appointments/<int:appointment_id>/treatment-note")
@jwt_required()
@require_roles("super_admin", "branch_manager", "reception", "technician")
def get_treatment_note(appointment_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    appointment = Appointment.query.filter_by(id=appointment_id, branch_id=branch_id).first()
    if not appointment:
        return jsonify({"error": "not_found"}), 404

    scope = _enforce_technician_scope(appointment, branch_id)
    if scope is not None:
        err, st = scope
        return jsonify(err), st

    note = TreatmentNote.query.filter_by(appointment_id=appointment.id).first()
    if not note:
        return jsonify({"error": "not_found"}), 404
    return jsonify(note.to_dict())


@api_bp.put("/appointments/<int:appointment_id>/treatment-note")
@jwt_required()
@require_roles("super_admin", "branch_manager", "reception", "technician")
def upsert_treatment_note(appointment_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    appointment = Appointment.query.filter_by(id=appointment_id, branch_id=branch_id).first()
    if not appointment:
        return jsonify({"error": "not_found"}), 404

    scope = _enforce_technician_scope(appointment, branch_id)
    if scope is not None:
        err, st = scope
        return jsonify(err), st

    payload = request.get_json(silent=True) or {}

    if _is_technician_only():
        staff = _technician_staff(branch_id)
        if staff is None:
            return jsonify({"error": "forbidden"}), 403
        payload = dict(payload)
        payload["staff_id"] = staff.id

    note = TreatmentNote.query.filter_by(appointment_id=appointment.id).first()
    before = note.to_dict() if note else None
    if note is None:
        note = TreatmentNote(appointment_id=appointment.id)
        db.session.add(note)

    if "staff_id" in payload:
        staff_id = payload.get("staff_id")
        if staff_id is None:
            note.staff_id = None
        else:
            ok, fk_error = _validate_branch_fk(Staff, staff_id, branch_id)
            if not ok:
                if fk_error == "forbidden_branch":
                    return jsonify({"error": "forbidden_branch"}), 403
                return jsonify({"error": "not_found"}), 404
            note.staff_id = staff_id

    for field_name in (
        "subjective_note",
        "objective_note",
        "assessment_note",
        "plan_note",
        "attachment_json",
    ):
        if field_name in payload:
            setattr(note, field_name, payload.get(field_name) or None)

    db.session.flush()
    user_id = _current_user_id()
    _audit(
        user_id,
        branch_id,
        "treatment_note.upsert",
        entity="TreatmentNote",
        before=before,
        after=note.to_dict(),
    )
    db.session.commit()
    return jsonify(note.to_dict())


@api_bp.put("/appointments/<int:appointment_id>")
@jwt_required()
@require_roles("super_admin", "branch_manager", "reception")
def update_appointment(appointment_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    appointment = Appointment.query.filter_by(id=appointment_id, branch_id=branch_id).first()
    if not appointment:
        return jsonify({"error": "not_found"}), 404

    payload = request.get_json(silent=True) or {}

    if appointment.status in {"completed", "paid"}:
        if "customer_package_id" in payload or "sessions_used" in payload:
            return jsonify({"error": "already_completed"}), 400
    if "customer_id" in payload:
        customer_id = payload.get("customer_id")
        if customer_id is None:
            return jsonify({"error": "missing_fields"}), 400
        ok, fk_error = _validate_branch_fk(Customer, customer_id, branch_id)
        if not ok:
            if fk_error == "forbidden_branch":
                return jsonify({"error": "forbidden_branch"}), 403
            return jsonify({"error": "not_found"}), 404
        appointment.customer_id = customer_id

    sessions_used = appointment.sessions_used if appointment.sessions_used is not None else 1
    if "sessions_used" in payload:
        parsed_sessions_used = _parse_positive_int(payload.get("sessions_used"))
        if parsed_sessions_used is None:
            return jsonify({"error": "invalid_sessions_used"}), 400
        sessions_used = parsed_sessions_used
        appointment.sessions_used = sessions_used

    if "customer_package_id" in payload:
        raw_customer_package_id = payload.get("customer_package_id")
        if raw_customer_package_id is None:
            appointment.customer_package_id = None
        else:
            try:
                parsed_customer_package_id = int(raw_customer_package_id)
            except (TypeError, ValueError):
                return jsonify({"error": "missing_fields"}), 400
            customer_package = CustomerPackage.query.filter_by(
                id=parsed_customer_package_id,
                branch_id=branch_id,
            ).first()
            if not customer_package or customer_package.customer_id != appointment.customer_id:
                return jsonify({"error": "not_found"}), 404
            if customer_package.status != "active":
                return jsonify({"error": "inactive_package"}), 400
            if customer_package.expires_at is not None and customer_package.expires_at <= datetime.now():
                return jsonify({"error": "package_expired"}), 400
            if customer_package.sessions_remaining is None or customer_package.sessions_remaining < sessions_used:
                return jsonify({"error": "insufficient_sessions"}), 400
            appointment.customer_package_id = customer_package.id

    if appointment.customer_package_id is not None:
        customer_package = CustomerPackage.query.filter_by(
            id=appointment.customer_package_id,
            branch_id=branch_id,
        ).first()
        if not customer_package or customer_package.customer_id != appointment.customer_id:
            return jsonify({"error": "not_found"}), 404
        if customer_package.sessions_remaining is None or customer_package.sessions_remaining < sessions_used:
            return jsonify({"error": "insufficient_sessions"}), 400

    for field_name, model in (("service_id", Service), ("staff_id", Staff), ("resource_id", Resource)):
        if field_name not in payload:
            continue
        ref_id = payload.get(field_name)
        if ref_id is None:
            setattr(appointment, field_name, None)
            continue
        ok, fk_error = _validate_branch_fk(model, ref_id, branch_id)
        if not ok:
            if fk_error == "forbidden_branch":
                return jsonify({"error": "forbidden_branch"}), 403
            return jsonify({"error": "not_found"}), 404
        setattr(appointment, field_name, ref_id)

    if "start_time" in payload:
        start_time = _parse_datetime(payload.get("start_time"))
        if start_time is None:
            return jsonify({"error": "missing_fields"}), 400
        appointment.start_time = start_time

    if "end_time" in payload:
        end_time = _parse_datetime(payload.get("end_time"))
        if end_time is None:
            return jsonify({"error": "missing_fields"}), 400
        appointment.end_time = end_time

    if not _validate_time_range(appointment.start_time, appointment.end_time):
        return jsonify({"error": "invalid_time_range"}), 400

    if "buffer_before_minutes" in payload:
        buffer_before = _parse_non_negative_int(payload.get("buffer_before_minutes"))
        if buffer_before is None:
            return jsonify({"error": "invalid_buffer"}), 400
        appointment.buffer_before_minutes = buffer_before

    if "buffer_after_minutes" in payload:
        buffer_after = _parse_non_negative_int(payload.get("buffer_after_minutes"))
        if buffer_after is None:
            return jsonify({"error": "invalid_buffer"}), 400
        appointment.buffer_after_minutes = buffer_after

    status_changed = False
    previous_status = appointment.status
    if "status" in payload:
        normalized_status = _parse_status(payload.get("status"))
        if normalized_status is None:
            return jsonify({"error": "invalid_status"}), 400
        if normalized_status != appointment.status:
            allowed_next = STATUS_TRANSITIONS.get(appointment.status, set())
            if normalized_status not in allowed_next:
                return jsonify({"error": "invalid_status_transition"}), 400
            appointment.status = normalized_status
            status_changed = True

    if "note" in payload:
        appointment.note = payload.get("note") or None

    conflicts = _detect_conflicts(
        branch_id=branch_id,
        start_time=appointment.start_time,
        end_time=appointment.end_time,
        buffer_before_minutes=appointment.buffer_before_minutes,
        buffer_after_minutes=appointment.buffer_after_minutes,
        staff_id=appointment.staff_id,
        resource_id=appointment.resource_id,
        exclude_appointment_id=appointment.id,
    )
    if conflicts:
        return jsonify({"error": "conflict", "conflicts": conflicts}), 409

    if status_changed:
        user_id = _current_user_id()
        after = appointment.to_dict()
        _audit(
            user_id,
            branch_id,
            "appointment.status_change",
            entity="Appointment",
            before={"id": appointment.id, "status": previous_status},
            after={"id": appointment.id, "status": after["status"]},
        )

    db.session.commit()
    return jsonify(appointment.to_dict())
