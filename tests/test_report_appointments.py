# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false

from datetime import datetime

from backend.extensions import db
from backend.models.appointment import Appointment
from backend.models.branch import Branch
from backend.models.customer import Customer
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


def _seed_appointments_report_data(app):
    with app.app_context():
        branch_one = Branch.query.first()
        assert branch_one is not None

        branch_two = Branch(name="Chi nhanh 2", address="Demo 2", status="active")
        branch_three = Branch(name="Chi nhanh 3", address="Demo 3", status="active")
        db.session.add_all([branch_two, branch_three])
        db.session.commit()

        manager = _create_user(
            "appointments_report_manager",
            "pass-123",
            "branch_manager",
            [branch_one, branch_two],
        )

        customer_two = Customer(branch_id=branch_two.id, full_name="Khach A", phone="0909000001")
        customer_three = Customer(branch_id=branch_three.id, full_name="Khach B", phone="0909000002")
        db.session.add_all([customer_two, customer_three])
        db.session.flush()

        db.session.add_all(
            [
                Appointment(
                    branch_id=branch_two.id,
                    customer_id=customer_two.id,
                    start_time=datetime(2026, 1, 10, 9, 0, 0),
                    end_time=datetime(2026, 1, 10, 10, 0, 0),
                    status="booked",
                ),
                Appointment(
                    branch_id=branch_two.id,
                    customer_id=customer_two.id,
                    start_time=datetime(2026, 1, 10, 10, 0, 0),
                    end_time=datetime(2026, 1, 10, 11, 0, 0),
                    status="arrived",
                ),
                Appointment(
                    branch_id=branch_two.id,
                    customer_id=customer_two.id,
                    start_time=datetime(2026, 1, 10, 11, 0, 0),
                    end_time=datetime(2026, 1, 10, 12, 0, 0),
                    status="completed",
                ),
                Appointment(
                    branch_id=branch_two.id,
                    customer_id=customer_two.id,
                    start_time=datetime(2026, 1, 10, 12, 0, 0),
                    end_time=datetime(2026, 1, 10, 13, 0, 0),
                    status="no_show",
                ),
                Appointment(
                    branch_id=branch_two.id,
                    customer_id=customer_two.id,
                    start_time=datetime(2026, 1, 10, 13, 0, 0),
                    end_time=datetime(2026, 1, 10, 14, 0, 0),
                    status="cancelled",
                ),
                Appointment(
                    branch_id=branch_two.id,
                    customer_id=customer_two.id,
                    start_time=datetime(2026, 1, 11, 9, 0, 0),
                    end_time=datetime(2026, 1, 11, 10, 0, 0),
                    status="in_service",
                ),
                Appointment(
                    branch_id=branch_two.id,
                    customer_id=customer_two.id,
                    start_time=datetime(2026, 1, 11, 10, 0, 0),
                    end_time=datetime(2026, 1, 11, 11, 0, 0),
                    status="paid",
                ),
                Appointment(
                    branch_id=branch_three.id,
                    customer_id=customer_three.id,
                    start_time=datetime(2026, 1, 10, 9, 0, 0),
                    end_time=datetime(2026, 1, 10, 10, 0, 0),
                    status="arrived",
                ),
            ]
        )
        db.session.commit()

        return {
            "username": manager.username,
            "branch_two_id": branch_two.id,
            "branch_three_id": branch_three.id,
        }


def test_appointments_report_requires_valid_branch_scope(client, app):
    data = _seed_appointments_report_data(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]

    branch_required_resp = client.get(
        "/api/reports/appointments",
        headers=_auth_header(token),
    )
    assert branch_required_resp.status_code == 400
    assert branch_required_resp.get_json()["error"] == "branch_required"

    forbidden_branch_resp = client.get(
        "/api/reports/appointments",
        headers=_auth_header(token, data["branch_three_id"]),
    )
    assert forbidden_branch_resp.status_code == 403
    assert forbidden_branch_resp.get_json()["error"] == "forbidden_branch"


def test_appointments_report_aggregates_by_day_and_applies_date_filters(client, app):
    data = _seed_appointments_report_data(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]

    resp = client.get(
        "/api/reports/appointments",
        headers=_auth_header(token, data["branch_two_id"]),
    )
    assert resp.status_code == 200
    assert resp.get_json()["items"] == [
        {
            "day": "2026-01-10",
            "total": 5,
            "arrived": 2,
            "no_show": 1,
            "cancelled": 1,
        },
        {
            "day": "2026-01-11",
            "total": 2,
            "arrived": 2,
            "no_show": 0,
            "cancelled": 0,
        },
    ]

    day_one_resp = client.get(
        "/api/reports/appointments?from=2026-01-10&to=2026-01-10",
        headers=_auth_header(token, data["branch_two_id"]),
    )
    assert day_one_resp.status_code == 200
    assert day_one_resp.get_json()["items"] == [
        {
            "day": "2026-01-10",
            "total": 5,
            "arrived": 2,
            "no_show": 1,
            "cancelled": 1,
        }
    ]


def test_appointments_report_invalid_date_filter_returns_missing_fields(client, app):
    data = _seed_appointments_report_data(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]

    resp = client.get(
        "/api/reports/appointments?to=invalid-date",
        headers=_auth_header(token, data["branch_two_id"]),
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "missing_fields"
