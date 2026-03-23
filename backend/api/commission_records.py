# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUntypedFunctionDecorator=false, reportUnknownArgumentType=false

from decimal import Decimal, InvalidOperation
import json

from flask import jsonify, request
from flask_jwt_extended import jwt_required

from backend.api import api_bp
from backend.decorators.rbac import require_roles
from backend.extensions import db
from backend.models.commission_record import CommissionRecord
from backend.models.invoice import Invoice
from backend.models.staff import Staff
from backend.utils.scoping import get_current_branch_id

_ALLOWED_SOURCE_TYPES = {"service", "product", "package"}
_ALLOWED_STATUS = {"pending", "paid", "cancelled"}
_TWO_DP = Decimal("0.01")


def _parse_non_negative_decimal(value):
    if isinstance(value, bool):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if parsed < Decimal("0"):
        return None
    return parsed


def _normalize_optional_json(value):
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=True, separators=(",", ":"))
    return None


def _parse_optional_int(value):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _compute_commission_amount(base_amount, rate_percent):
    commission = (base_amount * rate_percent / Decimal("100")).quantize(_TWO_DP)
    return commission


def _validate_source_type(value):
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if normalized not in _ALLOWED_SOURCE_TYPES:
        return None
    return normalized


def _validate_status(value):
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if normalized not in _ALLOWED_STATUS:
        return None
    return normalized


def _get_record_in_scope(record_id, branch_id):
    return CommissionRecord.query.filter_by(id=record_id, branch_id=branch_id).first()


@api_bp.get("/commission-records")
@jwt_required()
@require_roles("super_admin", "branch_manager")
def list_commission_records():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    query = CommissionRecord.query.filter(CommissionRecord.branch_id == branch_id)

    staff_id = _parse_optional_int(request.args.get("staff_id"))
    if request.args.get("staff_id") is not None and staff_id is None:
        return jsonify({"error": "missing_fields"}), 400
    if staff_id is not None:
        query = query.filter(CommissionRecord.staff_id == staff_id)

    invoice_id = _parse_optional_int(request.args.get("invoice_id"))
    if request.args.get("invoice_id") is not None and invoice_id is None:
        return jsonify({"error": "missing_fields"}), 400
    if invoice_id is not None:
        query = query.filter(CommissionRecord.invoice_id == invoice_id)

    status_filter = request.args.get("status")
    if status_filter is not None:
        normalized_status = _validate_status(status_filter)
        if normalized_status is None:
            return jsonify({"error": "invalid_status"}), 400
        query = query.filter(CommissionRecord.status == normalized_status)

    items = query.order_by(CommissionRecord.id.desc()).limit(200).all()
    return jsonify({"items": [item.to_dict() for item in items]})


@api_bp.post("/commission-records")
@jwt_required()
@require_roles("super_admin", "branch_manager")
def create_commission_record():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    payload = request.get_json(silent=True) or {}

    staff_id = _parse_optional_int(payload.get("staff_id"))
    source_type = _validate_source_type(payload.get("source_type"))
    base_amount = _parse_non_negative_decimal(payload.get("base_amount"))
    rate_percent = _parse_non_negative_decimal(payload.get("rate_percent"))

    if staff_id is None or source_type is None or base_amount is None or rate_percent is None:
        if payload.get("source_type") is not None and source_type is None:
            return jsonify({"error": "invalid_source_type"}), 400
        return jsonify({"error": "missing_fields"}), 400

    staff = Staff.query.filter_by(id=staff_id, branch_id=branch_id).first()
    if not staff:
        return jsonify({"error": "not_found"}), 404

    invoice_id = _parse_optional_int(payload.get("invoice_id"))
    if payload.get("invoice_id") is not None and invoice_id is None:
        return jsonify({"error": "missing_fields"}), 400
    if invoice_id is not None:
        invoice = Invoice.query.filter_by(id=invoice_id, branch_id=branch_id).first()
        if not invoice:
            return jsonify({"error": "not_found"}), 404

    source_id = _parse_optional_int(payload.get("source_id"))
    if payload.get("source_id") is not None and source_id is None:
        return jsonify({"error": "missing_fields"}), 400

    normalized_status = _validate_status(payload.get("status"))
    if payload.get("status") is not None and normalized_status is None:
        return jsonify({"error": "invalid_status"}), 400

    payload_json = _normalize_optional_json(payload.get("payload_json"))
    if payload.get("payload_json") is not None and payload_json is None:
        return jsonify({"error": "missing_fields"}), 400

    record = CommissionRecord(
        branch_id=branch_id,
        staff_id=staff_id,
        invoice_id=invoice_id,
        source_type=source_type,
        source_id=source_id,
        base_amount=base_amount.quantize(_TWO_DP),
        rate_percent=rate_percent.quantize(_TWO_DP),
        commission_amount=_compute_commission_amount(base_amount, rate_percent),
        status=normalized_status or "pending",
        payload_json=payload_json,
    )
    db.session.add(record)
    db.session.commit()
    return jsonify(record.to_dict()), 201


@api_bp.get("/commission-records/<int:record_id>")
@jwt_required()
@require_roles("super_admin", "branch_manager")
def get_commission_record(record_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    record = _get_record_in_scope(record_id, branch_id)
    if not record:
        return jsonify({"error": "not_found"}), 404
    return jsonify(record.to_dict())


@api_bp.put("/commission-records/<int:record_id>")
@jwt_required()
@require_roles("super_admin", "branch_manager")
def update_commission_record(record_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    record = _get_record_in_scope(record_id, branch_id)
    if not record:
        return jsonify({"error": "not_found"}), 404

    payload = request.get_json(silent=True) or {}
    should_recompute = False

    if "staff_id" in payload:
        staff_id = _parse_optional_int(payload.get("staff_id"))
        if staff_id is None:
            return jsonify({"error": "missing_fields"}), 400
        staff = Staff.query.filter_by(id=staff_id, branch_id=branch_id).first()
        if not staff:
            return jsonify({"error": "not_found"}), 404
        record.staff_id = staff_id

    if "source_type" in payload:
        source_type = _validate_source_type(payload.get("source_type"))
        if source_type is None:
            return jsonify({"error": "invalid_source_type"}), 400
        record.source_type = source_type

    if "source_id" in payload:
        source_id = _parse_optional_int(payload.get("source_id"))
        if payload.get("source_id") is not None and source_id is None:
            return jsonify({"error": "missing_fields"}), 400
        record.source_id = source_id

    if "invoice_id" in payload:
        invoice_id = _parse_optional_int(payload.get("invoice_id"))
        if payload.get("invoice_id") is not None and invoice_id is None:
            return jsonify({"error": "missing_fields"}), 400
        if invoice_id is not None:
            invoice = Invoice.query.filter_by(id=invoice_id, branch_id=branch_id).first()
            if not invoice:
                return jsonify({"error": "not_found"}), 404
        record.invoice_id = invoice_id

    if "status" in payload:
        normalized_status = _validate_status(payload.get("status"))
        if normalized_status is None:
            return jsonify({"error": "invalid_status"}), 400
        record.status = normalized_status

    if "payload_json" in payload:
        payload_json = _normalize_optional_json(payload.get("payload_json"))
        if payload.get("payload_json") is not None and payload_json is None:
            return jsonify({"error": "missing_fields"}), 400
        record.payload_json = payload_json

    if "base_amount" in payload:
        base_amount = _parse_non_negative_decimal(payload.get("base_amount"))
        if base_amount is None:
            return jsonify({"error": "missing_fields"}), 400
        record.base_amount = base_amount.quantize(_TWO_DP)
        should_recompute = True

    if "rate_percent" in payload:
        rate_percent = _parse_non_negative_decimal(payload.get("rate_percent"))
        if rate_percent is None:
            return jsonify({"error": "missing_fields"}), 400
        record.rate_percent = rate_percent.quantize(_TWO_DP)
        should_recompute = True

    if should_recompute:
        record.commission_amount = _compute_commission_amount(record.base_amount, record.rate_percent)

    db.session.commit()
    return jsonify(record.to_dict())
