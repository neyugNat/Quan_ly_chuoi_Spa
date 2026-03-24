# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false

from backend.extensions import db
from backend.models.branch import Branch
from backend.models.customer import Customer
from backend.models.resource import Resource
from backend.models.staff import Staff
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


def _seed_conflict_data(app):
    with app.app_context():
        branch = Branch.query.first()
        assert branch is not None

        user = _create_user("appointments_conflict_reception", "pass-123", "reception", [branch])

        customer_one = Customer(branch_id=branch.id, full_name="Customer One", phone="0901000001")
        customer_two = Customer(branch_id=branch.id, full_name="Customer Two", phone="0901000002")
        staff_one = Staff(branch_id=branch.id, full_name="Staff One", status="active")
        staff_two = Staff(branch_id=branch.id, full_name="Staff Two", status="active")
        resource_one = Resource(branch_id=branch.id, name="Room One", resource_type="room", status="active")
        resource_two = Resource(branch_id=branch.id, name="Room Two", resource_type="room", status="active")
        db.session.add_all([customer_one, customer_two, staff_one, staff_two, resource_one, resource_two])
        db.session.commit()

        return {
            "username": user.username,
            "branch_id": branch.id,
            "customer_one_id": customer_one.id,
            "customer_two_id": customer_two.id,
            "staff_one_id": staff_one.id,
            "staff_two_id": staff_two.id,
            "resource_one_id": resource_one.id,
            "resource_two_id": resource_two.id,
        }


def test_create_appointment_rejects_staff_and_resource_conflict_with_buffers(client, app):
    data = _seed_conflict_data(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_id"])

    existing_resp = client.post(
        "/api/appointments",
        json={
            "customer_id": data["customer_one_id"],
            "staff_id": data["staff_one_id"],
            "resource_id": data["resource_one_id"],
            "start_time": "2026-01-01T10:00:00",
            "end_time": "2026-01-01T11:00:00",
            "buffer_before_minutes": 10,
            "buffer_after_minutes": 10,
            "status": "confirmed",
        },
        headers=headers,
    )
    assert existing_resp.status_code == 201
    existing_id = existing_resp.get_json()["id"]

    conflict_resp = client.post(
        "/api/appointments",
        json={
            "customer_id": data["customer_two_id"],
            "staff_id": data["staff_one_id"],
            "resource_id": data["resource_one_id"],
            "start_time": "2026-01-01T11:05:00",
            "end_time": "2026-01-01T12:00:00",
        },
        headers=headers,
    )

    assert conflict_resp.status_code == 409
    payload = conflict_resp.get_json()
    assert payload["error"] == "conflict"
    assert {(item["appointment_id"], item["kind"]) for item in payload["conflicts"]} == {
        (existing_id, "staff"),
        (existing_id, "resource"),
    }


def test_create_appointment_ignores_non_blocking_statuses(client, app):
    data = _seed_conflict_data(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_id"])

    cancelled_resp = client.post(
        "/api/appointments",
        json={
            "customer_id": data["customer_one_id"],
            "staff_id": data["staff_one_id"],
            "resource_id": data["resource_one_id"],
            "start_time": "2026-01-01T10:00:00",
            "end_time": "2026-01-01T11:00:00",
            "status": "cancelled",
        },
        headers=headers,
    )
    assert cancelled_resp.status_code == 201

    create_resp = client.post(
        "/api/appointments",
        json={
            "customer_id": data["customer_two_id"],
            "staff_id": data["staff_one_id"],
            "resource_id": data["resource_one_id"],
            "start_time": "2026-01-01T10:15:00",
            "end_time": "2026-01-01T11:15:00",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201


def test_update_appointment_conflict_excludes_self_and_checks_others(client, app):
    data = _seed_conflict_data(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_id"])

    first_resp = client.post(
        "/api/appointments",
        json={
            "customer_id": data["customer_one_id"],
            "staff_id": data["staff_one_id"],
            "resource_id": data["resource_one_id"],
            "start_time": "2026-01-01T09:00:00",
            "end_time": "2026-01-01T10:00:00",
        },
        headers=headers,
    )
    assert first_resp.status_code == 201
    first_id = first_resp.get_json()["id"]

    self_update_resp = client.put(
        f"/api/appointments/{first_id}",
        json={"note": "Update without other conflicts"},
        headers=headers,
    )
    assert self_update_resp.status_code == 200

    second_resp = client.post(
        "/api/appointments",
        json={
            "customer_id": data["customer_two_id"],
            "staff_id": data["staff_one_id"],
            "resource_id": data["resource_two_id"],
            "start_time": "2026-01-01T10:30:00",
            "end_time": "2026-01-01T11:30:00",
            "status": "booked",
        },
        headers=headers,
    )
    assert second_resp.status_code == 201
    second_id = second_resp.get_json()["id"]

    conflict_update_resp = client.put(
        f"/api/appointments/{first_id}",
        json={
            "start_time": "2026-01-01T10:45:00",
            "end_time": "2026-01-01T11:00:00",
        },
        headers=headers,
    )
    assert conflict_update_resp.status_code == 409
    payload = conflict_update_resp.get_json()
    assert payload["error"] == "conflict"
    assert payload["conflicts"] == [{"appointment_id": second_id, "kind": "staff"}]
