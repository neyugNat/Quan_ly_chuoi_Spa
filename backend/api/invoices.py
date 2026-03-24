# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false, reportUntypedFunctionDecorator=false

from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
import json
from typing import cast

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from backend.api import api_bp
from backend.decorators.rbac import require_roles
from backend.extensions import db
from backend.models.appointment import Appointment
from backend.models.audit_log import AuditLog
from backend.models.customer import Customer
from backend.models.invoice import Invoice
from backend.models.payment import Payment
from backend.models.service import Service
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


def _parse_non_negative_decimal(value):
    if isinstance(value, bool):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if parsed < Decimal("0"):
        return None
    return parsed


def _normalize_line_items_json(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=True, separators=(",", ":"))
    return None


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


def _recompute_invoice_payment_state(invoice: Invoice):
    total_amount = Decimal(str(invoice.total_amount or 0))
    paid_amount = Decimal(str(invoice.paid_amount or 0))
    balance_amount = total_amount - paid_amount
    if balance_amount < Decimal("0"):
        balance_amount = Decimal("0")

    invoice.balance_amount = balance_amount
    if paid_amount == Decimal("0"):
        invoice.status = "unpaid"
    elif paid_amount < total_amount:
        invoice.status = "partial"
    else:
        invoice.status = "paid"


@api_bp.get("/invoices")
@jwt_required()
@require_roles("super_admin", "branch_manager", "reception", "cashier")
def list_invoices():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    items = (
        Invoice.query.filter(Invoice.branch_id == branch_id)
        .order_by(Invoice.id.desc())
        .limit(200)
        .all()
    )
    return jsonify({"items": [item.to_dict() for item in items]})


@api_bp.post("/invoices")
@jwt_required()
@require_roles("super_admin", "branch_manager", "reception", "cashier")
def create_invoice():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    payload = request.get_json(silent=True) or {}
    appointment_id = payload.get("appointment_id")

    invoice = None

    if appointment_id is not None:
        appointment = Appointment.query.filter_by(id=appointment_id, branch_id=branch_id).first()
        if not appointment:
            return jsonify({"error": "not_found"}), 404
        if appointment.status not in {"completed", "paid"}:
            return jsonify({"error": "invalid_appointment_status"}), 400

        total_amount = Decimal("0")
        line_items_json = "[]"
        if appointment.service_id is not None:
            service = Service.query.filter_by(
                id=appointment.service_id,
                branch_id=branch_id,
            ).first()
            if service:
                unit_price = Decimal(str(service.price))
                amount = unit_price
                total_amount = amount
                line_items_json = json.dumps(
                    [
                        {
                            "type": "service",
                            "service_id": service.id,
                            "qty": 1,
                            "unit_price": float(unit_price),
                            "amount": float(amount),
                        }
                    ],
                    ensure_ascii=True,
                    separators=(",", ":"),
                )

        invoice = Invoice(
            branch_id=branch_id,
            customer_id=appointment.customer_id,
            appointment_id=appointment.id,
            subtotal_amount=total_amount,
            discount_amount=Decimal("0"),
            tax_amount=Decimal("0"),
            total_amount=total_amount,
            paid_amount=Decimal("0"),
            balance_amount=total_amount,
            status="unpaid",
            line_items_json=line_items_json,
        )
    else:
        if "line_items_json" not in payload or "total_amount" not in payload:
            return jsonify({"error": "missing_fields"}), 400

        total_amount = _parse_non_negative_decimal(payload.get("total_amount"))
        if total_amount is None:
            return jsonify({"error": "invalid_total_amount"}), 400

        line_items_json = _normalize_line_items_json(payload.get("line_items_json"))
        if line_items_json is None:
            return jsonify({"error": "invalid_line_items_json"}), 400

        customer_id = payload.get("customer_id")
        if customer_id is not None:
            customer = Customer.query.filter_by(id=customer_id, branch_id=branch_id).first()
            if not customer:
                return jsonify({"error": "not_found"}), 404

        invoice = Invoice(
            branch_id=branch_id,
            customer_id=customer_id,
            appointment_id=None,
            subtotal_amount=total_amount,
            discount_amount=Decimal("0"),
            tax_amount=Decimal("0"),
            total_amount=total_amount,
            paid_amount=Decimal("0"),
            balance_amount=total_amount,
            status="unpaid",
            line_items_json=line_items_json,
        )

    db.session.add(invoice)
    db.session.flush()

    user_id = _current_user_id()
    _audit(user_id, branch_id, "invoice.create", entity="Invoice", after=invoice.to_dict())
    db.session.commit()
    return jsonify(invoice.to_dict()), 201


@api_bp.get("/invoices/<int:invoice_id>")
@jwt_required()
@require_roles("super_admin", "branch_manager", "reception", "cashier")
def get_invoice(invoice_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    invoice = Invoice.query.filter_by(id=invoice_id, branch_id=branch_id).first()
    if not invoice:
        return jsonify({"error": "not_found"}), 404
    return jsonify(invoice.to_dict())


@api_bp.post("/invoices/<int:invoice_id>/void")
@jwt_required()
@require_roles("super_admin", "branch_manager")
def void_invoice(invoice_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    invoice = Invoice.query.filter_by(id=invoice_id, branch_id=branch_id).first()
    if not invoice:
        return jsonify({"error": "not_found"}), 404
    if invoice.status == "voided":
        return jsonify({"error": "already_voided"}), 400

    paid_amount = Decimal(str(invoice.paid_amount or 0))
    if paid_amount > Decimal("0"):
        return jsonify({"error": "invoice_has_payments"}), 400

    before_state = invoice.to_dict()
    invoice.status = "voided"
    invoice.balance_amount = Decimal("0")

    user_id = _current_user_id()
    _audit(
        user_id,
        branch_id,
        "invoice.void",
        entity="Invoice",
        before=before_state,
        after=invoice.to_dict(),
    )
    db.session.commit()
    return jsonify(invoice.to_dict())


@api_bp.post("/invoices/<int:invoice_id>/refund")
@jwt_required()
@require_roles("super_admin")
def refund_invoice(invoice_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    payload = request.get_json(silent=True) or {}
    if "amount" not in payload or "method" not in payload:
        return jsonify({"error": "missing_fields"}), 400

    amount = _parse_positive_decimal(payload.get("amount"))
    method = _normalize_optional_text(payload.get("method"))
    if amount is None or method is None:
        return jsonify({"error": "missing_fields"}), 400

    metadata_json = _normalize_metadata_json(payload.get("metadata_json"))
    if "metadata_json" in payload and payload.get("metadata_json") is not None and metadata_json is None:
        return jsonify({"error": "invalid_metadata_json"}), 400

    invoice = Invoice.query.filter_by(id=invoice_id, branch_id=branch_id).first()
    if not invoice:
        return jsonify({"error": "not_found"}), 404
    if invoice.status == "voided":
        return jsonify({"error": "invoice_voided"}), 400

    paid_amount = Decimal(str(invoice.paid_amount or 0))
    if paid_amount <= Decimal("0"):
        return jsonify({"error": "no_payments"}), 400
    if amount > paid_amount:
        return jsonify({"error": "refund_exceeds_paid"}), 400

    before_state = invoice.to_dict()

    payment = Payment(
        branch_id=branch_id,
        invoice_id=invoice.id,
        customer_id=invoice.customer_id,
        amount=amount,
        method=method,
        status="refunded",
        paid_at=datetime.now(timezone.utc),
        reference_code=_normalize_optional_text(payload.get("reference_code")),
        metadata_json=metadata_json,
    )
    invoice.paid_amount = paid_amount - amount
    _recompute_invoice_payment_state(invoice)

    db.session.add(payment)
    db.session.flush()

    user_id = _current_user_id()
    _audit(
        user_id,
        branch_id,
        "invoice.refund",
        entity="Invoice",
        before=before_state,
        after=invoice.to_dict(),
    )
    db.session.commit()
    return jsonify(payment.to_dict()), 201
