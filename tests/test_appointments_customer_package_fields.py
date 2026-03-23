# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false

from backend.extensions import db
from backend.models.branch import Branch
from backend.models.customer import Customer
from backend.models.customer_package import CustomerPackage
from backend.models.inventory_item import InventoryItem
from backend.models.package import Package
from backend.models.service import Service
from backend.models.stock_transaction import StockTransaction
from backend.models.user import Role, User


def _login(client, username, password):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def _auth_header(token, branch_id):
    return {
        "Authorization": f"Bearer {token}",
        "X-Branch-Id": str(branch_id),
    }


def _create_user(username, password, role_name, branches):
    role = Role.query.filter_by(name=role_name).first()
    assert role is not None
    user = User(username=username, is_active=True)
    user.set_password(password)
    user.roles = [role]
    user.branches = branches
    db.session.add(user)
    db.session.commit()
    return user


def _seed(app, *, sessions_remaining):
    with app.app_context():
        branch = Branch.query.first()
        assert branch is not None

        user = _create_user("reception_pkg_fields", "pass-123", "reception", [branch])

        customer = Customer(branch_id=branch.id, full_name="Pkg Customer", phone="0911222333")
        service = Service(
            branch_id=branch.id,
            name="Pkg Service",
            price=250000,
            duration_minutes=60,
            consumable_recipe_json='{"consumables": [{"sku": "PKG-ITEM", "qty": 1}]}',
            status="active",
        )
        inventory_item = InventoryItem(
            branch_id=branch.id,
            name="Pkg Item",
            sku="PKG-ITEM",
            unit="unit",
            min_stock=0,
            expiry_tracking=False,
            status="active",
        )
        package = Package(
            branch_id=branch.id,
            name="Pkg Plan",
            sessions_total=10,
            validity_days=30,
            shareable=False,
            status="active",
        )
        db.session.add_all([customer, service, inventory_item, package])
        db.session.commit()

        customer_package = CustomerPackage(
            branch_id=branch.id,
            customer_id=customer.id,
            package_id=package.id,
            sessions_total=10,
            sessions_remaining=sessions_remaining,
            status="active",
        )
        opening_stock = StockTransaction(
            branch_id=branch.id,
            inventory_item_id=inventory_item.id,
            transaction_type="in",
            delta_qty=10,
            source_type="seed",
        )
        db.session.add_all([customer_package, opening_stock])
        db.session.commit()

        return {
            "username": user.username,
            "branch_id": branch.id,
            "customer_id": customer.id,
            "service_id": service.id,
            "customer_package_id": customer_package.id,
        }


def test_create_appointment_with_customer_package_and_sessions_used(client, app):
    data = _seed(app, sessions_remaining=5)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_id"])

    create_resp = client.post(
        "/api/appointments",
        json={
            "customer_id": data["customer_id"],
            "customer_package_id": data["customer_package_id"],
            "sessions_used": 2,
            "service_id": data["service_id"],
            "start_time": "2026-01-01T10:00:00",
            "end_time": "2026-01-01T11:00:00",
            "status": "booked",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    appointment_id = create_resp.get_json()["id"]
    assert create_resp.get_json()["sessions_used"] == 2
    assert create_resp.get_json()["customer_package_id"] == data["customer_package_id"]

    check_in_resp = client.post(f"/api/appointments/{appointment_id}/check-in", headers=headers)
    assert check_in_resp.status_code == 200

    check_out_resp = client.post(f"/api/appointments/{appointment_id}/check-out", headers=headers)
    assert check_out_resp.status_code == 200

    with app.app_context():
        package = CustomerPackage.query.filter_by(id=data["customer_package_id"]).first()
        assert package is not None
        assert package.sessions_remaining == 3


def test_create_appointment_rejects_insufficient_sessions(client, app):
    data = _seed(app, sessions_remaining=1)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_id"])

    create_resp = client.post(
        "/api/appointments",
        json={
            "customer_id": data["customer_id"],
            "customer_package_id": data["customer_package_id"],
            "sessions_used": 2,
            "start_time": "2026-01-01T10:00:00",
            "end_time": "2026-01-01T11:00:00",
        },
        headers=headers,
    )
    assert create_resp.status_code == 400
    assert create_resp.get_json()["error"] == "insufficient_sessions"
