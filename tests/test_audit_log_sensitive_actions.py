from backend.extensions import db
from backend.models.audit_log import AuditLog
from backend.models.branch import Branch
from backend.models.user import Role, User


def _login(client, username, password):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def _create_user(username, password, role_name="reception"):
    role = Role.query.filter_by(name=role_name).first()
    branches = Branch.query.all()
    user = User(username=username, is_active=True)
    user.set_password(password)
    user.roles = [role]
    user.branches = branches
    db.session.add(user)
    db.session.commit()
    return user


def _actions_exist(actions):
    existing_actions = {row.action for row in AuditLog.query.filter(AuditLog.action.in_(actions)).all()}
    return set(actions).issubset(existing_actions)


def test_lock_and_unlock_user_are_audited(client, app):
    with app.app_context():
        target_user = _create_user("audit_charlie", "charlie-pass")
        target_user_id = target_user.id

    admin_login = _login(client, "admin", "admin123")
    admin_token = admin_login.get_json()["token"]

    lock_resp = client.post(
        "/api/auth/lock-user",
        json={"user_id": target_user_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert lock_resp.status_code == 200

    unlock_resp = client.post(
        "/api/auth/unlock-user",
        json={"user_id": target_user_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert unlock_resp.status_code == 200

    with app.app_context():
        assert _actions_exist(["auth.lock_user", "auth.unlock_user"])


def test_forgot_and_reset_password_are_audited(client, app):
    with app.app_context():
        _create_user("audit_alice", "old-pass")

    forgot_resp = client.post("/api/auth/forgot-password", json={"username": "audit_alice"})
    assert forgot_resp.status_code == 200
    reset_token = forgot_resp.get_json()["reset_token"]

    reset_resp = client.post(
        "/api/auth/reset-password",
        json={"token": reset_token, "new_password": "new-pass"},
    )
    assert reset_resp.status_code == 200

    with app.app_context():
        assert _actions_exist(["auth.forgot_password", "auth.reset_password"])


def test_customer_create_and_update_are_audited(client, app):
    with app.app_context():
        _create_user("audit_reception", "pass-123", role_name="reception")

    staff_login = _login(client, "audit_reception", "pass-123")
    staff_token = staff_login.get_json()["token"]

    create_resp = client.post(
        "/api/customers",
        json={"full_name": "Audit Customer", "phone": "0911000000"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert create_resp.status_code == 201
    customer_id = create_resp.get_json()["id"]

    update_resp = client.put(
        f"/api/customers/{customer_id}",
        json={"full_name": "Audit Customer Updated"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert update_resp.status_code == 200

    with app.app_context():
        assert _actions_exist(["customer.create", "customer.update"])


def test_audit_logs_endpoint_requires_super_admin(client, app):
    with app.app_context():
        _create_user("audit_staff", "pass-123", role_name="reception")

    staff_login = _login(client, "audit_staff", "pass-123")
    staff_token = staff_login.get_json()["token"]

    resp = client.get(
        "/api/audit-logs",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "forbidden"


def test_super_admin_can_list_audit_logs(client):
    admin_login = _login(client, "admin", "admin123")
    admin_token = admin_login.get_json()["token"]

    resp = client.get(
        "/api/audit-logs?limit=10",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert "items" in body
    assert isinstance(body["items"], list)
