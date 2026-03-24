# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false

import json
from decimal import Decimal
from typing import cast

from backend.extensions import db
from backend.models.audit_log import AuditLog
from backend.models.branch import Branch
from backend.models.invoice import Invoice
from backend.models.user import Role, User


def _login(client, username, password):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def _create_user(username, password, role_name, branches):
    role = Role.query.filter_by(name=role_name).first()
    user = User(username=username, is_active=True)
    user.set_password(password)
    user.roles = [role]
    user.branches = branches
    db.session.add(user)
    db.session.commit()
    return user


def _auth_header(token, branch_id):
    return {"Authorization": f"Bearer {token}", "X-Branch-Id": str(branch_id)}


def _seed_invoice_refund_void_base(app):
    with app.app_context():
        branch = Branch.query.first()
        assert branch is not None

        manager = _create_user("invoice_manager", "pass-123", "branch_manager", [branch])
        reception = _create_user("invoice_reception_refund", "pass-123", "reception", [branch])

        unpaid_invoice = Invoice(
            branch_id=branch.id,
            customer_id=None,
            appointment_id=None,
            subtotal_amount=Decimal("300000"),
            discount_amount=Decimal("0"),
            tax_amount=Decimal("0"),
            total_amount=Decimal("300000"),
            paid_amount=Decimal("0"),
            balance_amount=Decimal("300000"),
            status="unpaid",
            line_items_json="[]",
        )
        paid_invoice = Invoice(
            branch_id=branch.id,
            customer_id=None,
            appointment_id=None,
            subtotal_amount=Decimal("300000"),
            discount_amount=Decimal("0"),
            tax_amount=Decimal("0"),
            total_amount=Decimal("300000"),
            paid_amount=Decimal("300000"),
            balance_amount=Decimal("0"),
            status="paid",
            line_items_json="[]",
        )
        db.session.add_all([unpaid_invoice, paid_invoice])
        db.session.commit()

        return {
            "branch_id": branch.id,
            "manager_username": manager.username,
            "reception_username": reception.username,
            "unpaid_invoice_id": unpaid_invoice.id,
            "paid_invoice_id": paid_invoice.id,
        }


def test_void_invoice_enforces_rbac_and_writes_audit_log(client, app):
    data = _seed_invoice_refund_void_base(app)

    reception_token = _login(client, data["reception_username"], "pass-123").get_json()["token"]
    manager_token = _login(client, data["manager_username"], "pass-123").get_json()["token"]

    forbidden_resp = client.post(
        f"/api/invoices/{data['unpaid_invoice_id']}/void",
        headers=_auth_header(reception_token, data["branch_id"]),
    )
    assert forbidden_resp.status_code == 403
    assert forbidden_resp.get_json()["error"] == "forbidden"

    void_resp = client.post(
        f"/api/invoices/{data['unpaid_invoice_id']}/void",
        headers=_auth_header(manager_token, data["branch_id"]),
    )
    assert void_resp.status_code == 200
    void_body = void_resp.get_json()
    assert void_body["status"] == "voided"
    assert void_body["paid_amount"] == 0.0
    assert void_body["balance_amount"] == 0.0

    with app.app_context():
        audit = (
            AuditLog.query.filter_by(action="invoice.void", branch_id=data["branch_id"])
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert audit is not None
        assert audit.before_json is not None
        assert audit.after_json is not None
        before = cast(dict[str, object], json.loads(audit.before_json))
        after = cast(dict[str, object], json.loads(audit.after_json))
        assert before["status"] == "unpaid"
        assert after["status"] == "voided"


def test_refund_invoice_enforces_rbac_and_updates_state_and_audit(client, app):
    data = _seed_invoice_refund_void_base(app)

    manager_token = _login(client, data["manager_username"], "pass-123").get_json()["token"]
    admin_token = _login(client, "admin", "admin123").get_json()["token"]

    forbidden_resp = client.post(
        f"/api/invoices/{data['paid_invoice_id']}/refund",
        json={"amount": 100000, "method": "cash"},
        headers=_auth_header(manager_token, data["branch_id"]),
    )
    assert forbidden_resp.status_code == 403
    assert forbidden_resp.get_json()["error"] == "forbidden"

    partial_refund_resp = client.post(
        f"/api/invoices/{data['paid_invoice_id']}/refund",
        json={"amount": 100000, "method": "bank_transfer"},
        headers=_auth_header(admin_token, data["branch_id"]),
    )
    assert partial_refund_resp.status_code == 201
    partial_refund_body = partial_refund_resp.get_json()
    assert partial_refund_body["status"] == "refunded"
    assert partial_refund_body["amount"] == 100000.0

    invoice_after_partial = client.get(
        f"/api/invoices/{data['paid_invoice_id']}", headers=_auth_header(admin_token, data["branch_id"])
    )
    assert invoice_after_partial.status_code == 200
    partial_invoice_body = invoice_after_partial.get_json()
    assert partial_invoice_body["paid_amount"] == 200000.0
    assert partial_invoice_body["balance_amount"] == 100000.0
    assert partial_invoice_body["status"] == "partial"

    full_refund_resp = client.post(
        f"/api/invoices/{data['paid_invoice_id']}/refund",
        json={"amount": 200000, "method": "bank_transfer"},
        headers=_auth_header(admin_token, data["branch_id"]),
    )
    assert full_refund_resp.status_code == 201

    invoice_after_full = client.get(
        f"/api/invoices/{data['paid_invoice_id']}", headers=_auth_header(admin_token, data["branch_id"])
    )
    assert invoice_after_full.status_code == 200
    full_invoice_body = invoice_after_full.get_json()
    assert full_invoice_body["paid_amount"] == 0.0
    assert full_invoice_body["balance_amount"] == 300000.0
    assert full_invoice_body["status"] == "unpaid"

    with app.app_context():
        audit = (
            AuditLog.query.filter_by(action="invoice.refund", branch_id=data["branch_id"])
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert audit is not None
        assert audit.before_json is not None
        assert audit.after_json is not None


def test_voided_invoice_blocks_refund_and_new_payment(client, app):
    data = _seed_invoice_refund_void_base(app)

    manager_token = _login(client, data["manager_username"], "pass-123").get_json()["token"]
    admin_token = _login(client, "admin", "admin123").get_json()["token"]

    void_resp = client.post(
        f"/api/invoices/{data['unpaid_invoice_id']}/void",
        headers=_auth_header(manager_token, data["branch_id"]),
    )
    assert void_resp.status_code == 200

    refund_resp = client.post(
        f"/api/invoices/{data['unpaid_invoice_id']}/refund",
        json={"amount": 1000, "method": "cash"},
        headers=_auth_header(admin_token, data["branch_id"]),
    )
    assert refund_resp.status_code == 400
    assert refund_resp.get_json()["error"] == "invoice_voided"

    payment_resp = client.post(
        "/api/payments",
        json={"invoice_id": data["unpaid_invoice_id"], "amount": 1000, "method": "cash"},
        headers=_auth_header(manager_token, data["branch_id"]),
    )
    assert payment_resp.status_code == 400
    assert payment_resp.get_json()["error"] == "invoice_voided"
