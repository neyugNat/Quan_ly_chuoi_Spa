# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false, reportCallIssue=false, reportAttributeAccessIssue=false

from decimal import Decimal

from backend.extensions import db
from backend.models.branch import Branch
from backend.models.invoice import Invoice
from backend.models.staff import Staff
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


def _seed_commission_base(app):
    with app.app_context():
        branch_one = Branch.query.first()
        assert branch_one is not None
        branch_two = Branch(name="Chi nhanh 2", address="Demo 2", status="active")
        branch_three = Branch(name="Chi nhanh 3", address="Demo 3", status="active")
        db.session.add_all([branch_two, branch_three])
        db.session.commit()

        manager = _create_user(
            "commission_manager",
            "pass-123",
            "branch_manager",
            [branch_one, branch_two],
        )

        staff_one = Staff(branch_id=branch_one.id, full_name="Staff B1", status="active")
        staff_two = Staff(branch_id=branch_two.id, full_name="Staff B2", status="active")
        db.session.add_all([staff_one, staff_two])
        db.session.flush()

        invoice_one = Invoice(
            branch_id=branch_one.id,
            customer_id=None,
            appointment_id=None,
            subtotal_amount=Decimal("100000"),
            discount_amount=Decimal("0"),
            tax_amount=Decimal("0"),
            total_amount=Decimal("100000"),
            paid_amount=Decimal("0"),
            balance_amount=Decimal("100000"),
            status="unpaid",
            line_items_json="[]",
        )
        invoice_two = Invoice(
            branch_id=branch_two.id,
            customer_id=None,
            appointment_id=None,
            subtotal_amount=Decimal("150000"),
            discount_amount=Decimal("0"),
            tax_amount=Decimal("0"),
            total_amount=Decimal("150000"),
            paid_amount=Decimal("0"),
            balance_amount=Decimal("150000"),
            status="unpaid",
            line_items_json="[]",
        )
        db.session.add_all([invoice_one, invoice_two])
        db.session.commit()

        return {
            "username": manager.username,
            "branch_one_id": branch_one.id,
            "branch_two_id": branch_two.id,
            "branch_three_id": branch_three.id,
            "staff_one_id": staff_one.id,
            "staff_two_id": staff_two.id,
            "invoice_one_id": invoice_one.id,
            "invoice_two_id": invoice_two.id,
        }


def test_multi_branch_user_must_provide_branch_header(client, app):
    data = _seed_commission_base(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]

    resp = client.get("/api/commission-records", headers=_auth_header(token))
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "branch_required"


def test_user_cannot_access_commission_records_outside_branch_scope(client, app):
    data = _seed_commission_base(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]

    resp = client.get(
        "/api/commission-records",
        headers=_auth_header(token, data["branch_three_id"]),
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "forbidden_branch"


def test_commission_records_create_list_get_update_in_scope(client, app):
    data = _seed_commission_base(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_two_id"])

    create_resp = client.post(
        "/api/commission-records",
        json={
            "branch_id": data["branch_one_id"],
            "staff_id": data["staff_two_id"],
            "invoice_id": data["invoice_two_id"],
            "source_type": "service",
            "source_id": 777,
            "base_amount": 100000,
            "rate_percent": 40,
            "payload_json": {"items": [1, 2]},
            "status": "pending",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    created = create_resp.get_json()
    assert created["branch_id"] == data["branch_two_id"]
    assert created["staff_id"] == data["staff_two_id"]
    assert created["invoice_id"] == data["invoice_two_id"]
    assert created["source_type"] == "service"
    assert created["source_id"] == 777
    assert created["base_amount"] == 100000.0
    assert created["rate_percent"] == 40.0
    assert created["commission_amount"] == 40000.0
    assert created["status"] == "pending"
    assert created["payload_json"] == '{"items":[1,2]}'

    record_id = created["id"]

    list_resp = client.get("/api/commission-records?staff_id=" + str(data["staff_two_id"]), headers=headers)
    assert list_resp.status_code == 200
    list_items = list_resp.get_json()["items"]
    assert any(item["id"] == record_id for item in list_items)

    get_resp = client.get(f"/api/commission-records/{record_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.get_json()["id"] == record_id

    wrong_branch_resp = client.get(
        f"/api/commission-records/{record_id}",
        headers=_auth_header(token, data["branch_one_id"]),
    )
    assert wrong_branch_resp.status_code == 404
    assert wrong_branch_resp.get_json()["error"] == "not_found"

    update_resp = client.put(
        f"/api/commission-records/{record_id}",
        json={
            "base_amount": 120000,
            "status": "paid",
            "payload_json": ["a", "b"],
            "source_type": "product",
            "source_id": 778,
            "invoice_id": data["invoice_two_id"],
            "staff_id": data["staff_two_id"],
        },
        headers=headers,
    )
    assert update_resp.status_code == 200
    updated = update_resp.get_json()
    assert updated["base_amount"] == 120000.0
    assert updated["rate_percent"] == 40.0
    assert updated["commission_amount"] == 48000.0
    assert updated["status"] == "paid"
    assert updated["payload_json"] == '["a","b"]'
    assert updated["source_type"] == "product"
    assert updated["source_id"] == 778

    update_rate_resp = client.put(
        f"/api/commission-records/{record_id}",
        json={"rate_percent": 25},
        headers=headers,
    )
    assert update_rate_resp.status_code == 200
    updated_rate = update_rate_resp.get_json()
    assert updated_rate["rate_percent"] == 25.0
    assert updated_rate["commission_amount"] == 30000.0


def test_commission_records_invalid_source_type_and_status_return_400(client, app):
    data = _seed_commission_base(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_two_id"])

    invalid_source_resp = client.post(
        "/api/commission-records",
        json={
            "staff_id": data["staff_two_id"],
            "source_type": "membership",
            "base_amount": 100000,
            "rate_percent": 40,
        },
        headers=headers,
    )
    assert invalid_source_resp.status_code == 400
    assert invalid_source_resp.get_json()["error"] == "invalid_source_type"

    create_resp = client.post(
        "/api/commission-records",
        json={
            "staff_id": data["staff_two_id"],
            "source_type": "package",
            "base_amount": 50000,
            "rate_percent": 10,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    record_id = create_resp.get_json()["id"]

    invalid_status_resp = client.put(
        f"/api/commission-records/{record_id}",
        json={"status": "processing"},
        headers=headers,
    )
    assert invalid_status_resp.status_code == 400
    assert invalid_status_resp.get_json()["error"] == "invalid_status"
