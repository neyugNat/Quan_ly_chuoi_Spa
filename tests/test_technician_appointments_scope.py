# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false

from datetime import datetime

from backend.extensions import db
from backend.models.appointment import Appointment
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
    assert role is not None
    user = User(username=username, is_active=True)
    user.set_password(password)
    user.roles = [role]
    user.branches = branches
    db.session.add(user)
    db.session.commit()
    return user


def _seed(app):
    with app.app_context():
        branch = Branch.query.first()
        assert branch is not None

        tech_user = _create_user("tech_user", "pass-123", "technician", [branch])
        other_user = _create_user("reception_user", "pass-123", "reception", [branch])

        tech_staff = Staff(branch_id=branch.id, full_name="Tech Staff", user_id=tech_user.id, status="active")
        other_staff = Staff(branch_id=branch.id, full_name="Other Staff", user_id=None, status="active")
        customer = Customer(branch_id=branch.id, full_name="Tech Customer", phone="0990000111")
        db.session.add_all([tech_staff, other_staff, customer])
        db.session.commit()

        appt_own = Appointment(
            branch_id=branch.id,
            customer_id=customer.id,
            staff_id=tech_staff.id,
            start_time=datetime(2026, 1, 1, 10, 0, 0),
            end_time=datetime(2026, 1, 1, 11, 0, 0),
            status="booked",
        )
        appt_other = Appointment(
            branch_id=branch.id,
            customer_id=customer.id,
            staff_id=other_staff.id,
            start_time=datetime(2026, 1, 1, 12, 0, 0),
            end_time=datetime(2026, 1, 1, 13, 0, 0),
            status="booked",
        )
        db.session.add_all([appt_own, appt_other])
        db.session.commit()

        return {
            "branch_id": branch.id,
            "tech_username": tech_user.username,
            "reception_username": other_user.username,
            "own_id": appt_own.id,
            "other_id": appt_other.id,
            "tech_staff_id": tech_staff.id,
        }


def test_technician_sees_only_own_appointments_and_can_write_note_and_complete(client, app):
    data = _seed(app)
    token = _login(client, data["tech_username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_id"])

    list_resp = client.get("/api/appointments", headers=headers)
    assert list_resp.status_code == 200
    items = list_resp.get_json()["items"]
    assert any(i["id"] == data["own_id"] for i in items)
    assert not any(i["id"] == data["other_id"] for i in items)

    forbidden_get = client.get(f"/api/appointments/{data['other_id']}", headers=headers)
    assert forbidden_get.status_code == 403
    assert forbidden_get.get_json()["error"] == "forbidden"

    forbidden_checkin = client.post(
        f"/api/appointments/{data['other_id']}/check-in",
        headers=headers,
    )
    assert forbidden_checkin.status_code == 403
    assert forbidden_checkin.get_json()["error"] == "forbidden"

    upsert_note = client.put(
        f"/api/appointments/{data['own_id']}/treatment-note",
        json={"subjective_note": "ok", "objective_note": "ok"},
        headers=headers,
    )
    assert upsert_note.status_code == 200
    assert upsert_note.get_json()["staff_id"] == data["tech_staff_id"]

    get_note = client.get(
        f"/api/appointments/{data['own_id']}/treatment-note",
        headers=headers,
    )
    assert get_note.status_code == 200
    assert get_note.get_json()["staff_id"] == data["tech_staff_id"]

    check_in = client.post(f"/api/appointments/{data['own_id']}/check-in", headers=headers)
    assert check_in.status_code == 200
    assert check_in.get_json()["status"] == "in_service"

    check_out = client.post(f"/api/appointments/{data['own_id']}/check-out", headers=headers)
    assert check_out.status_code == 200
    assert check_out.get_json()["status"] == "completed"
