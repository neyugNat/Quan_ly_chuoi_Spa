# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false, reportUntypedFunctionDecorator=false

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from typing import cast

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from backend.api import api_bp
from backend.decorators.rbac import require_roles
from backend.extensions import db
from backend.models.audit_log import AuditLog
from backend.models.invoice import Invoice
from backend.models.payment import Payment
from backend.utils.scoping import get_current_branch_id


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


def _current_user_id():
    identity = cast(str | int, get_jwt_identity())
    return int(identity)


def _parse_positive_decimal(value):
    if isinstance(value, bool):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if parsed <= Decimal("0"):
        return None
    return parsed


def _normalize_optional_text(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_metadata_json(value):
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=True, separators=(",", ":"))
    return None


def _update_invoice_payment_state(invoice: Invoice, amount: Decimal):
    total_amount = Decimal(str(invoice.total_amount or 0))
    paid_amount = Decimal(str(invoice.paid_amount or 0)) + amount
    balance_amount = total_amount - paid_amount
    if balance_amount < Decimal("0"):
        balance_amount = Decimal("0")

    invoice.paid_amount = paid_amount
    invoice.balance_amount = balance_amount

    if paid_amount == Decimal("0"):
        invoice.status = "unpaid"
    elif paid_amount < total_amount:
        invoice.status = "partial"
    else:
        invoice.status = "paid"


@api_bp.post("/payments")
@jwt_required()
@require_roles("super_admin", "branch_manager", "reception", "cashier")
def create_payment():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    payload = request.get_json(silent=True) or {}

    if "invoice_id" not in payload or "amount" not in payload or "method" not in payload:
        return jsonify({"error": "missing_fields"}), 400

    amount = _parse_positive_decimal(payload.get("amount"))
    method = _normalize_optional_text(payload.get("method"))
    if amount is None or method is None:
        return jsonify({"error": "missing_fields"}), 400

    metadata_json = _normalize_metadata_json(payload.get("metadata_json"))
    if "metadata_json" in payload and payload.get("metadata_json") is not None and metadata_json is None:
        return jsonify({"error": "invalid_metadata_json"}), 400

    invoice = Invoice.query.filter_by(id=payload.get("invoice_id"), branch_id=branch_id).first()
    if not invoice:
        return jsonify({"error": "not_found"}), 404
    if invoice.status == "voided":
        return jsonify({"error": "invoice_voided"}), 400

    payment = Payment(
        branch_id=branch_id,
        invoice_id=invoice.id,
        customer_id=invoice.customer_id,
        amount=amount,
        method=method,
        status="posted",
        paid_at=datetime.now(timezone.utc),
        reference_code=_normalize_optional_text(payload.get("reference_code")),
        metadata_json=metadata_json,
    )
    _update_invoice_payment_state(invoice, amount)

    db.session.add(payment)
    db.session.flush()

    user_id = _current_user_id()
    _audit(user_id, branch_id, "payment.create", entity="Payment", after=payment.to_dict())
    db.session.commit()

    return jsonify(payment.to_dict()), 201


@api_bp.get("/invoices/<int:invoice_id>/payments")
@jwt_required()
@require_roles("super_admin", "branch_manager", "reception", "cashier")
def list_invoice_payments(invoice_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    invoice = Invoice.query.filter_by(id=invoice_id, branch_id=branch_id).first()
    if not invoice:
        return jsonify({"error": "not_found"}), 404

    items = (
        Payment.query.filter(Payment.branch_id == branch_id, Payment.invoice_id == invoice_id)
        .order_by(Payment.id.desc())
        .limit(200)
        .all()
    )
    return jsonify({"items": [item.to_dict() for item in items]})
