# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false

from backend.extensions import db
from backend.models.branch import Branch
from backend.models.customer import Customer
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


def _seed_data(app):
    with app.app_context():
        branch = Branch.query.first()
        assert branch is not None
        user = _create_user("appointment_checkin_reception", "pass-123", "reception", [branch])

        customer = Customer(branch_id=branch.id, full_name="Customer Checkin", phone="0909111111")
        staff = Staff(branch_id=branch.id, full_name="Staff Checkin", status="active")
        db.session.add_all([customer, staff])
        db.session.commit()

        return {
            "username": user.username,
            "branch_id": branch.id,
            "customer_id": customer.id,
            "staff_id": staff.id,
        }


def _create_appointment(client, headers, customer_id):
    resp = client.post(
        "/api/appointments",
        json={
            "customer_id": customer_id,
            "start_time": "2026-01-01T09:00:00",
            "end_time": "2026-01-01T10:00:00",
            "status": "booked",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.get_json()["id"]


def test_check_in_sets_status_and_started_timestamp(client, app):
    data = _seed_data(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_id"])
    appointment_id = _create_appointment(client, headers, data["customer_id"])

    resp = client.post(f"/api/appointments/{appointment_id}/check-in", headers=headers)
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["status"] == "in_service"
    assert payload["service_started_at"] is not None


def test_check_out_sets_status_and_completed_timestamp(client, app):
    data = _seed_data(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_id"])
    appointment_id = _create_appointment(client, headers, data["customer_id"])

    check_in_resp = client.post(f"/api/appointments/{appointment_id}/check-in", headers=headers)
    assert check_in_resp.status_code == 200

    resp = client.post(f"/api/appointments/{appointment_id}/check-out", headers=headers)
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["status"] == "completed"
    assert payload["service_completed_at"] is not None


def test_check_out_before_check_in_returns_invalid_transition(client, app):
    data = _seed_data(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_id"])
    appointment_id = _create_appointment(client, headers, data["customer_id"])

    resp = client.post(f"/api/appointments/{appointment_id}/check-out", headers=headers)
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "invalid_status_transition"


def test_treatment_note_upsert_then_fetch_returns_same_data(client, app):
    data = _seed_data(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_id"])
    appointment_id = _create_appointment(client, headers, data["customer_id"])

    payload = {
        "staff_id": data["staff_id"],
        "subjective_note": "subjective",
        "objective_note": "objective",
        "assessment_note": "assessment",
        "plan_note": "plan",
        "attachment_json": '{"files":["abc.jpg"]}',
    }
    upsert_resp = client.put(
        f"/api/appointments/{appointment_id}/treatment-note",
        json=payload,
        headers=headers,
    )
    assert upsert_resp.status_code == 200

    get_resp = client.get(f"/api/appointments/{appointment_id}/treatment-note", headers=headers)
    assert get_resp.status_code == 200
    fetched = get_resp.get_json()
    assert fetched["appointment_id"] == appointment_id
    assert fetched["staff_id"] == payload["staff_id"]
    assert fetched["subjective_note"] == payload["subjective_note"]
    assert fetched["objective_note"] == payload["objective_note"]
    assert fetched["assessment_note"] == payload["assessment_note"]
    assert fetched["plan_note"] == payload["plan_note"]
    assert fetched["attachment_json"] == payload["attachment_json"]
