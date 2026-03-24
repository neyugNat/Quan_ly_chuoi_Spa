# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false

from backend.extensions import db
from backend.models.appointment import Appointment
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
    user = User(username=username, is_active=True)
    user.set_password(password)
    user.roles = [role]
    user.branches = branches
    db.session.add(user)
    db.session.commit()
    return user


def _seed_completion_data(app, *, stock_qty, sessions_remaining, sessions_used):
    with app.app_context():
        branch = Branch.query.first()
        assert branch is not None

        user = _create_user("appointments_checkout_reception", "pass-123", "reception", [branch])

        customer = Customer(branch_id=branch.id, full_name="Customer Checkout", phone="0911000001")
        service = Service(
            branch_id=branch.id,
            name="Detox Facial",
            price=250000,
            duration_minutes=60,
            consumable_recipe_json='{"consumables": [{"sku": "MASK-A", "qty": 2}]}',
            status="active",
        )
        inventory_item = InventoryItem(
            branch_id=branch.id,
            name="Mask A",
            sku="MASK-A",
            unit="unit",
            min_stock=0,
            expiry_tracking=False,
            status="active",
        )
        package = Package(
            branch_id=branch.id,
            name="Facial Package",
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
            delta_qty=stock_qty,
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
            "inventory_item_id": inventory_item.id,
            "sessions_used": sessions_used,
        }


def _create_in_service_appointment(client, app, headers, data):
    create_resp = client.post(
        "/api/appointments",
        json={
            "customer_id": data["customer_id"],
            "service_id": data["service_id"],
            "start_time": "2026-01-01T10:00:00",
            "end_time": "2026-01-01T11:00:00",
            "status": "booked",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    appointment_id = create_resp.get_json()["id"]

    with app.app_context():
        appointment = Appointment.query.get(appointment_id)
        assert appointment is not None
        appointment.customer_package_id = data["customer_package_id"]
        appointment.sessions_used = data["sessions_used"]
        db.session.commit()

    check_in_resp = client.post(f"/api/appointments/{appointment_id}/check-in", headers=headers)
    assert check_in_resp.status_code == 200
    return appointment_id


def test_checkout_successfully_deducts_sessions_and_stock(client, app):
    data = _seed_completion_data(app, stock_qty=10, sessions_remaining=5, sessions_used=2)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_id"])
    appointment_id = _create_in_service_appointment(client, app, headers, data)

    check_out_resp = client.post(f"/api/appointments/{appointment_id}/check-out", headers=headers)
    assert check_out_resp.status_code == 200
    payload = check_out_resp.get_json()
    assert payload["status"] == "completed"

    with app.app_context():
        package = CustomerPackage.query.get(data["customer_package_id"])
        assert package is not None
        assert package.sessions_remaining == 3

        total_stock = (
            db.session.query(db.func.sum(StockTransaction.delta_qty))
            .filter(
                StockTransaction.branch_id == data["branch_id"],
                StockTransaction.inventory_item_id == data["inventory_item_id"],
            )
            .scalar()
        )
        assert float(total_stock) == 8.0


def test_insufficient_stock_prevents_completion_and_keeps_in_service(client, app):
    data = _seed_completion_data(app, stock_qty=1, sessions_remaining=5, sessions_used=1)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_id"])
    appointment_id = _create_in_service_appointment(client, app, headers, data)

    check_out_resp = client.post(f"/api/appointments/{appointment_id}/check-out", headers=headers)
    assert check_out_resp.status_code == 400
    assert check_out_resp.get_json()["error"] == "insufficient_stock"

    with app.app_context():
        appointment = Appointment.query.get(appointment_id)
        assert appointment is not None
        assert appointment.status == "in_service"
        assert appointment.service_completed_at is None

        out_count = (
            StockTransaction.query.filter_by(
                branch_id=data["branch_id"],
                source_type="appointment",
                source_id=appointment_id,
                transaction_type="out",
            ).count()
        )
        assert out_count == 0


def test_insufficient_sessions_prevents_completion(client, app):
    data = _seed_completion_data(app, stock_qty=10, sessions_remaining=0, sessions_used=1)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_id"])
    appointment_id = _create_in_service_appointment(client, app, headers, data)

    check_out_resp = client.post(f"/api/appointments/{appointment_id}/check-out", headers=headers)
    assert check_out_resp.status_code == 400
    assert check_out_resp.get_json()["error"] == "insufficient_sessions"

    with app.app_context():
        appointment = Appointment.query.get(appointment_id)
        assert appointment is not None
        assert appointment.status == "in_service"

        package = CustomerPackage.query.get(data["customer_package_id"])
        assert package is not None
        assert package.sessions_remaining == 0
