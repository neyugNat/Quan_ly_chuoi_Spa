# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false

from datetime import datetime, timedelta

from backend.extensions import db
from backend.models.branch import Branch
from backend.models.customer import Customer
from backend.models.resource import Resource
from backend.models.service import Service
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


def _seed_reception_with_two_branches_and_refs(app):
    with app.app_context():
        branch_one = Branch.query.first()
        assert branch_one is not None
        branch_two = Branch(name="Chi nhanh 2", address="Demo 2", status="active")
        branch_three = Branch(name="Chi nhanh 3", address="Demo 3", status="active")
        db.session.add_all([branch_two, branch_three])
        db.session.commit()

        user = _create_user("appointment_reception", "pass-123", "reception", [branch_one, branch_two])

        customer_one = Customer(branch_id=branch_one.id, full_name="Customer B1", phone="0901000001")
        customer_two = Customer(branch_id=branch_two.id, full_name="Customer B2", phone="0902000002")
        service_two = Service(
            branch_id=branch_two.id,
            name="Facial",
            price=100000,
            duration_minutes=60,
            status="active",
        )
        staff_two = Staff(branch_id=branch_two.id, full_name="Staff B2", status="active")
        resource_two = Resource(
            branch_id=branch_two.id,
            name="Room B2",
            resource_type="room",
            status="active",
        )
        db.session.add_all([customer_one, customer_two, service_two, staff_two, resource_two])
        db.session.commit()

        return {
            "username": user.username,
            "branch_one_id": branch_one.id,
            "branch_two_id": branch_two.id,
            "branch_three_id": branch_three.id,
            "customer_one_id": customer_one.id,
            "customer_two_id": customer_two.id,
            "service_two_id": service_two.id,
            "staff_two_id": staff_two.id,
            "resource_two_id": resource_two.id,
        }


def _auth_header(token, branch_id=None):
    headers = {"Authorization": f"Bearer {token}"}
    if branch_id is not None:
        headers["X-Branch-Id"] = str(branch_id)
    return headers


def _iso_window(hours_ahead=1):
    start = datetime(2026, 1, 1, 9, 0, 0) + timedelta(hours=hours_ahead)
    end = start + timedelta(hours=1)
    return start.isoformat(), end.isoformat()


def test_multi_branch_user_must_provide_branch_header(client, app):
    data = _seed_reception_with_two_branches_and_refs(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]

    resp = client.get("/api/appointments", headers=_auth_header(token))
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "branch_required"


def test_user_cannot_access_appointments_outside_branch_scope(client, app):
    data = _seed_reception_with_two_branches_and_refs(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]

    resp = client.get(
        "/api/appointments",
        headers=_auth_header(token, data["branch_three_id"]),
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "forbidden_branch"


def test_appointments_create_list_get_update_in_scope(client, app):
    data = _seed_reception_with_two_branches_and_refs(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_two_id"])
    start_time, end_time = _iso_window()

    create_resp = client.post(
        "/api/appointments",
        json={
            "customer_id": data["customer_two_id"],
            "service_id": data["service_two_id"],
            "staff_id": data["staff_two_id"],
            "resource_id": data["resource_two_id"],
            "start_time": start_time,
            "end_time": end_time,
            "buffer_before_minutes": 5,
            "buffer_after_minutes": 10,
            "status": "booked",
            "note": "Khach uu tien",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    created = create_resp.get_json()
    assert created["branch_id"] == data["branch_two_id"]
    assert created["status"] == "booked"
    assert created["buffer_before_minutes"] == 5
    assert created["buffer_after_minutes"] == 10

    appointment_id = created["id"]

    list_resp = client.get("/api/appointments", headers=headers)
    assert list_resp.status_code == 200
    items = list_resp.get_json()["items"]
    assert any(item["id"] == appointment_id for item in items)

    get_resp = client.get(f"/api/appointments/{appointment_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.get_json()["id"] == appointment_id

    updated_end = (datetime.fromisoformat(end_time) + timedelta(minutes=30)).isoformat()
    update_resp = client.put(
        f"/api/appointments/{appointment_id}",
        json={
            "status": "confirmed",
            "end_time": updated_end,
            "note": "Da xac nhan",
        },
        headers=headers,
    )
    assert update_resp.status_code == 200
    updated = update_resp.get_json()
    assert updated["status"] == "confirmed"
    assert updated["end_time"] == updated_end
    assert updated["note"] == "Da xac nhan"


def test_invalid_status_transition_returns_400(client, app):
    data = _seed_reception_with_two_branches_and_refs(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_two_id"])
    start_time, end_time = _iso_window()

    create_resp = client.post(
        "/api/appointments",
        json={
            "customer_id": data["customer_two_id"],
            "start_time": start_time,
            "end_time": end_time,
        },
        headers=headers,
    )
    appointment_id = create_resp.get_json()["id"]

    update_resp = client.put(
        f"/api/appointments/{appointment_id}",
        json={"status": "completed"},
        headers=headers,
    )
    assert update_resp.status_code == 400
    assert update_resp.get_json()["error"] == "invalid_status_transition"


def test_invalid_time_range_returns_400(client, app):
    data = _seed_reception_with_two_branches_and_refs(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_two_id"])

    invalid_create_resp = client.post(
        "/api/appointments",
        json={
            "customer_id": data["customer_two_id"],
            "start_time": "2026-01-01T10:00:00",
            "end_time": "2026-01-01T09:00:00",
        },
        headers=headers,
    )
    assert invalid_create_resp.status_code == 400
    assert invalid_create_resp.get_json()["error"] == "invalid_time_range"

    start_time, end_time = _iso_window()
    create_resp = client.post(
        "/api/appointments",
        json={
            "customer_id": data["customer_two_id"],
            "start_time": start_time,
            "end_time": end_time,
        },
        headers=headers,
    )
    appointment_id = create_resp.get_json()["id"]

    invalid_update_resp = client.put(
        f"/api/appointments/{appointment_id}",
        json={"end_time": "2026-01-01T08:00:00"},
        headers=headers,
    )
    assert invalid_update_resp.status_code == 400
    assert invalid_update_resp.get_json()["error"] == "invalid_time_range"


def test_cross_branch_foreign_key_returns_forbidden_branch(client, app):
    data = _seed_reception_with_two_branches_and_refs(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_one_id"])
    start_time, end_time = _iso_window()

    create_resp = client.post(
        "/api/appointments",
        json={
            "customer_id": data["customer_two_id"],
            "start_time": start_time,
            "end_time": end_time,
        },
        headers=headers,
    )
    assert create_resp.status_code == 403
    assert create_resp.get_json()["error"] == "forbidden_branch"
