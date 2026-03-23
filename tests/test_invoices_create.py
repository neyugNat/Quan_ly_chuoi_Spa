# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false, reportCallIssue=false, reportAttributeAccessIssue=false

from datetime import datetime
import json
from typing import cast

from backend.extensions import db
from backend.models.appointment import Appointment
from backend.models.branch import Branch
from backend.models.customer import Customer
from backend.models.service import Service
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


def _seed_invoice_base(app):
    with app.app_context():
        branch_one = Branch.query.first()
        assert branch_one is not None
        branch_two = Branch(name="Chi nhanh 2", address="Demo 2", status="active")
        db.session.add(branch_two)
        db.session.commit()

        user = _create_user("invoice_reception", "pass-123", "reception", [branch_one, branch_two])

        customer_one = Customer(branch_id=branch_one.id, full_name="Khach B1", phone="0901000001")
        customer_two = Customer(branch_id=branch_two.id, full_name="Khach B2", phone="0902000002")
        service_one = Service(
            branch_id=branch_one.id,
            name="Goi dau",
            price=150000,
            duration_minutes=45,
            status="active",
        )
        db.session.add_all([customer_one, customer_two, service_one])
        db.session.commit()

        appointment = Appointment(
            branch_id=branch_one.id,
            customer_id=customer_one.id,
            service_id=service_one.id,
            start_time=datetime(2026, 1, 1, 9, 0, 0),
            end_time=datetime(2026, 1, 1, 9, 45, 0),
            status="completed",
        )
        db.session.add(appointment)
        db.session.commit()

        return {
            "username": user.username,
            "branch_one_id": branch_one.id,
            "branch_two_id": branch_two.id,
            "customer_one_id": customer_one.id,
            "customer_two_id": customer_two.id,
            "service_one_id": service_one.id,
            "appointment_id": appointment.id,
        }


def test_create_invoice_from_completed_appointment_computes_totals(client, app):
    data = _seed_invoice_base(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_one_id"])

    resp = client.post(
        "/api/invoices",
        json={"appointment_id": data["appointment_id"]},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.get_json()

    assert body["branch_id"] == data["branch_one_id"]
    assert body["appointment_id"] == data["appointment_id"]
    assert body["customer_id"] == data["customer_one_id"]
    assert body["subtotal_amount"] == 150000.0
    assert body["total_amount"] == 150000.0
    assert body["discount_amount"] == 0.0
    assert body["tax_amount"] == 0.0
    assert body["paid_amount"] == 0.0
    assert body["balance_amount"] == 150000.0
    assert body["status"] == "unpaid"

    line_items = cast(list[dict[str, object]], json.loads(body["line_items_json"]))
    assert line_items == [
        {
            "type": "service",
            "service_id": data["service_one_id"],
            "qty": 1,
            "unit_price": 150000.0,
            "amount": 150000.0,
        }
    ]


def test_create_retail_invoice_requires_line_items_and_total(client, app):
    data = _seed_invoice_base(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_one_id"])

    missing_items_resp = client.post(
        "/api/invoices",
        json={"total_amount": 250000},
        headers=headers,
    )
    assert missing_items_resp.status_code == 400
    assert missing_items_resp.get_json()["error"] == "missing_fields"

    missing_total_resp = client.post(
        "/api/invoices",
        json={"line_items_json": [{"type": "retail", "sku": "SP001", "qty": 1, "amount": 250000}]},
        headers=headers,
    )
    assert missing_total_resp.status_code == 400
    assert missing_total_resp.get_json()["error"] == "missing_fields"

    create_resp = client.post(
        "/api/invoices",
        json={
            "customer_id": data["customer_one_id"],
            "line_items_json": [{"type": "retail", "sku": "SP001", "qty": 1, "amount": 250000}],
            "total_amount": 250000,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    body = create_resp.get_json()
    assert body["customer_id"] == data["customer_one_id"]
    assert body["subtotal_amount"] == 250000.0
    assert body["total_amount"] == 250000.0
    assert body["discount_amount"] == 0.0
    assert body["tax_amount"] == 0.0
    assert body["paid_amount"] == 0.0
    assert body["balance_amount"] == 250000.0
    assert body["status"] == "unpaid"


def test_invoice_branch_scoping_enforced(client, app):
    data = _seed_invoice_base(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    branch_one_headers = _auth_header(token, data["branch_one_id"])
    branch_two_headers = _auth_header(token, data["branch_two_id"])

    create_resp = client.post(
        "/api/invoices",
        json={
            "line_items_json": [{"type": "retail", "sku": "SP001", "qty": 1, "amount": 100000}],
            "total_amount": 100000,
        },
        headers=branch_one_headers,
    )
    assert create_resp.status_code == 201
    invoice_id = create_resp.get_json()["id"]

    get_wrong_branch = client.get(f"/api/invoices/{invoice_id}", headers=branch_two_headers)
    assert get_wrong_branch.status_code == 404
    assert get_wrong_branch.get_json()["error"] == "not_found"

    list_wrong_branch = client.get("/api/invoices", headers=branch_two_headers)
    assert list_wrong_branch.status_code == 200
    assert all(item["id"] != invoice_id for item in list_wrong_branch.get_json()["items"])

    create_from_other_branch_appointment = client.post(
        "/api/invoices",
        json={"appointment_id": data["appointment_id"]},
        headers=branch_two_headers,
    )
    assert create_from_other_branch_appointment.status_code == 404
    assert create_from_other_branch_appointment.get_json()["error"] == "not_found"
