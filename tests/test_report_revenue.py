# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false

from datetime import datetime
from decimal import Decimal

from backend.extensions import db
from backend.models.appointment import Appointment
from backend.models.branch import Branch
from backend.models.customer import Customer
from backend.models.invoice import Invoice
from backend.models.payment import Payment
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


def _auth_header(token, branch_id=None):
    headers = {"Authorization": f"Bearer {token}"}
    if branch_id is not None:
        headers["X-Branch-Id"] = str(branch_id)
    return headers


def _seed_revenue_data(app):
    with app.app_context():
        branch_one = Branch.query.first()
        assert branch_one is not None

        branch_two = Branch(name="Chi nhanh 2", address="Demo 2", status="active")
        branch_three = Branch(name="Chi nhanh 3", address="Demo 3", status="active")
        db.session.add_all([branch_two, branch_three])
        db.session.commit()

        manager = _create_user(
            "revenue_manager",
            "pass-123",
            "branch_manager",
            [branch_one, branch_two],
        )

        customer = Customer(branch_id=branch_two.id, full_name="Khach A", phone="0909000001")
        staff = Staff(branch_id=branch_two.id, full_name="Staff A", status="active")
        service = Service(
            branch_id=branch_two.id,
            name="Massage",
            price=Decimal("100.00"),
            duration_minutes=60,
            status="active",
        )
        db.session.add_all([customer, staff, service])
        db.session.flush()

        appointment_day_one = Appointment(
            branch_id=branch_two.id,
            customer_id=customer.id,
            service_id=service.id,
            staff_id=staff.id,
            start_time=datetime(2026, 1, 10, 9, 0, 0),
            end_time=datetime(2026, 1, 10, 10, 0, 0),
            status="completed",
        )
        appointment_day_two = Appointment(
            branch_id=branch_two.id,
            customer_id=customer.id,
            service_id=service.id,
            staff_id=staff.id,
            start_time=datetime(2026, 1, 11, 9, 0, 0),
            end_time=datetime(2026, 1, 11, 10, 0, 0),
            status="completed",
        )
        db.session.add_all([appointment_day_one, appointment_day_two])
        db.session.flush()

        invoice_day_one_a = Invoice(
            branch_id=branch_two.id,
            customer_id=customer.id,
            appointment_id=appointment_day_one.id,
            subtotal_amount=Decimal("100.00"),
            discount_amount=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("100.00"),
            paid_amount=Decimal("0.00"),
            balance_amount=Decimal("100.00"),
            status="unpaid",
            line_items_json="[]",
        )
        invoice_day_one_b = Invoice(
            branch_id=branch_two.id,
            customer_id=customer.id,
            appointment_id=appointment_day_one.id,
            subtotal_amount=Decimal("60.00"),
            discount_amount=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("60.00"),
            paid_amount=Decimal("0.00"),
            balance_amount=Decimal("60.00"),
            status="unpaid",
            line_items_json="[]",
        )
        invoice_day_two = Invoice(
            branch_id=branch_two.id,
            customer_id=customer.id,
            appointment_id=appointment_day_two.id,
            subtotal_amount=Decimal("200.00"),
            discount_amount=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("200.00"),
            paid_amount=Decimal("0.00"),
            balance_amount=Decimal("200.00"),
            status="unpaid",
            line_items_json="[]",
        )
        invoice_without_appointment = Invoice(
            branch_id=branch_two.id,
            customer_id=customer.id,
            appointment_id=None,
            subtotal_amount=Decimal("30.00"),
            discount_amount=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("30.00"),
            paid_amount=Decimal("0.00"),
            balance_amount=Decimal("30.00"),
            status="unpaid",
            line_items_json="[]",
        )
        invoice_refunded = Invoice(
            branch_id=branch_two.id,
            customer_id=customer.id,
            appointment_id=appointment_day_one.id,
            subtotal_amount=Decimal("90.00"),
            discount_amount=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("90.00"),
            paid_amount=Decimal("0.00"),
            balance_amount=Decimal("90.00"),
            status="unpaid",
            line_items_json="[]",
        )
        db.session.add_all(
            [
                invoice_day_one_a,
                invoice_day_one_b,
                invoice_day_two,
                invoice_without_appointment,
                invoice_refunded,
            ]
        )
        db.session.flush()

        db.session.add_all(
            [
                Payment(
                    branch_id=branch_two.id,
                    invoice_id=invoice_day_one_a.id,
                    customer_id=customer.id,
                    amount=Decimal("100.00"),
                    method="cash",
                    status="posted",
                    paid_at=datetime(2026, 1, 10, 11, 0, 0),
                ),
                Payment(
                    branch_id=branch_two.id,
                    invoice_id=invoice_day_one_b.id,
                    customer_id=customer.id,
                    amount=Decimal("50.00"),
                    method="card",
                    status="posted",
                    paid_at=datetime(2026, 1, 10, 15, 30, 0),
                ),
                Payment(
                    branch_id=branch_two.id,
                    invoice_id=invoice_day_two.id,
                    customer_id=customer.id,
                    amount=Decimal("200.00"),
                    method="bank_transfer",
                    status="posted",
                    paid_at=datetime(2026, 1, 11, 10, 0, 0),
                ),
                Payment(
                    branch_id=branch_two.id,
                    invoice_id=invoice_without_appointment.id,
                    customer_id=customer.id,
                    amount=Decimal("30.00"),
                    method="cash",
                    status="posted",
                    paid_at=datetime(2026, 1, 10, 17, 0, 0),
                ),
                Payment(
                    branch_id=branch_two.id,
                    invoice_id=invoice_refunded.id,
                    customer_id=customer.id,
                    amount=Decimal("999.00"),
                    method="cash",
                    status="refunded",
                    paid_at=datetime(2026, 1, 10, 16, 0, 0),
                ),
            ]
        )
        db.session.commit()

        return {
            "username": manager.username,
            "branch_two_id": branch_two.id,
            "branch_three_id": branch_three.id,
            "staff_id": staff.id,
            "service_id": service.id,
        }


def test_revenue_report_requires_valid_branch_scope(client, app):
    data = _seed_revenue_data(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]

    branch_required_resp = client.get(
        "/api/reports/revenue",
        headers=_auth_header(token),
    )
    assert branch_required_resp.status_code == 400
    assert branch_required_resp.get_json()["error"] == "branch_required"

    forbidden_branch_resp = client.get(
        "/api/reports/revenue",
        headers=_auth_header(token, data["branch_three_id"]),
    )
    assert forbidden_branch_resp.status_code == 403
    assert forbidden_branch_resp.get_json()["error"] == "forbidden_branch"


def test_revenue_report_aggregates_by_day_staff_service_and_excludes_refunded(client, app):
    data = _seed_revenue_data(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]

    resp = client.get(
        "/api/reports/revenue",
        headers=_auth_header(token, data["branch_two_id"]),
    )
    assert resp.status_code == 200

    items = resp.get_json()["items"]
    assert items == [
        {
            "day": "2026-01-10",
            "staff_id": data["staff_id"],
            "service_id": data["service_id"],
            "revenue": 150.0,
            "payments_count": 2,
        },
        {
            "day": "2026-01-10",
            "staff_id": None,
            "service_id": None,
            "revenue": 30.0,
            "payments_count": 1,
        },
        {
            "day": "2026-01-11",
            "staff_id": data["staff_id"],
            "service_id": data["service_id"],
            "revenue": 200.0,
            "payments_count": 1,
        },
    ]


def test_revenue_report_staff_filter_narrows_results(client, app):
    data = _seed_revenue_data(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]

    resp = client.get(
        f"/api/reports/revenue?staff_id={data['staff_id']}",
        headers=_auth_header(token, data["branch_two_id"]),
    )
    assert resp.status_code == 200

    items = resp.get_json()["items"]
    assert items == [
        {
            "day": "2026-01-10",
            "staff_id": data["staff_id"],
            "service_id": data["service_id"],
            "revenue": 150.0,
            "payments_count": 2,
        },
        {
            "day": "2026-01-11",
            "staff_id": data["staff_id"],
            "service_id": data["service_id"],
            "revenue": 200.0,
            "payments_count": 1,
        },
    ]


def test_revenue_report_invalid_filter_returns_missing_fields(client, app):
    data = _seed_revenue_data(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]

    resp = client.get(
        "/api/reports/revenue?from=invalid-date",
        headers=_auth_header(token, data["branch_two_id"]),
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "missing_fields"
