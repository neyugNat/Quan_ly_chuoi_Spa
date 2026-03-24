# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false

from decimal import Decimal

from backend.extensions import db
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


def _auth_header(token, branch_id=None):
    headers = {"Authorization": f"Bearer {token}"}
    if branch_id is not None:
        headers["X-Branch-Id"] = str(branch_id)
    return headers


def _seed_payment_base(app):
    with app.app_context():
        branch_one = Branch.query.first()
        assert branch_one is not None

        branch_two = Branch(name="Chi nhanh 2", address="Demo 2", status="active")
        db.session.add(branch_two)
        db.session.commit()

        user = _create_user("payment_reception", "pass-123", "reception", [branch_one, branch_two])

        invoice = Invoice(
            branch_id=branch_one.id,
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
        db.session.add(invoice)
        db.session.commit()

        return {
            "username": user.username,
            "branch_one_id": branch_one.id,
            "branch_two_id": branch_two.id,
            "invoice_id": invoice.id,
        }


def test_multi_method_payments_accumulate_and_invoice_status_transitions(client, app):
    data = _seed_payment_base(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_one_id"])

    first_payment = client.post(
        "/api/payments",
        json={"invoice_id": data["invoice_id"], "amount": 100000, "method": "cash"},
        headers=headers,
    )
    assert first_payment.status_code == 201
    first_body = first_payment.get_json()
    assert first_body["method"] == "cash"
    assert first_body["amount"] == 100000.0
    assert first_body["status"] == "posted"

    invoice_after_first = client.get(f"/api/invoices/{data['invoice_id']}", headers=headers)
    assert invoice_after_first.status_code == 200
    first_invoice_body = invoice_after_first.get_json()
    assert first_invoice_body["paid_amount"] == 100000.0
    assert first_invoice_body["balance_amount"] == 200000.0
    assert first_invoice_body["status"] == "partial"

    second_payment = client.post(
        "/api/payments",
        json={"invoice_id": data["invoice_id"], "amount": 200000, "method": "card"},
        headers=headers,
    )
    assert second_payment.status_code == 201
    second_body = second_payment.get_json()
    assert second_body["method"] == "card"
    assert second_body["amount"] == 200000.0

    payments_list = client.get(f"/api/invoices/{data['invoice_id']}/payments", headers=headers)
    assert payments_list.status_code == 200
    items = payments_list.get_json()["items"]
    assert len(items) == 2
    assert {item["method"] for item in items} == {"cash", "card"}

    invoice_after_second = client.get(f"/api/invoices/{data['invoice_id']}", headers=headers)
    assert invoice_after_second.status_code == 200
    second_invoice_body = invoice_after_second.get_json()
    assert second_invoice_body["paid_amount"] == 300000.0
    assert second_invoice_body["balance_amount"] == 0.0
    assert second_invoice_body["status"] == "paid"


def test_payment_create_returns_not_found_for_wrong_branch_invoice(client, app):
    data = _seed_payment_base(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    wrong_branch_headers = _auth_header(token, data["branch_two_id"])

    resp = client.post(
        "/api/payments",
        json={"invoice_id": data["invoice_id"], "amount": 1000, "method": "cash"},
        headers=wrong_branch_headers,
    )
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "not_found"
