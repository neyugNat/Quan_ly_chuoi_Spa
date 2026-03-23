from backend.extensions import db
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


def test_forgot_and_reset_password_happy_path(client, app):
    with app.app_context():
        _create_user("alice", "old-pass")

    forgot_resp = client.post("/api/auth/forgot-password", json={"username": "alice"})
    assert forgot_resp.status_code == 200
    token = forgot_resp.get_json()["reset_token"]

    reset_resp = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "new-pass"},
    )
    assert reset_resp.status_code == 200

    old_login = _login(client, "alice", "old-pass")
    assert old_login.status_code == 401

    new_login = _login(client, "alice", "new-pass")
    assert new_login.status_code == 200


def test_reset_password_invalid_token(client):
    resp = client.post(
        "/api/auth/reset-password",
        json={"token": "invalid-token", "new_password": "new-pass"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "invalid_token"


def test_change_password_still_works(client, app):
    with app.app_context():
        _create_user("bob", "start-pass")

    login_resp = _login(client, "bob", "start-pass")
    token = login_resp.get_json()["token"]

    change_resp = client.post(
        "/api/auth/change-password",
        json={"old_password": "start-pass", "new_password": "changed-pass"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert change_resp.status_code == 200

    assert _login(client, "bob", "start-pass").status_code == 401
    assert _login(client, "bob", "changed-pass").status_code == 200


def test_lock_unlock_user_and_locked_user_cannot_login(client, app):
    with app.app_context():
        locked_user = _create_user("charlie", "charlie-pass")
        locked_user_id = locked_user.id

    admin_login = _login(client, "admin", "admin123")
    admin_token = admin_login.get_json()["token"]

    lock_resp = client.post(
        "/api/auth/lock-user",
        json={"user_id": locked_user_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert lock_resp.status_code == 200
    assert lock_resp.get_json()["user"]["is_active"] is False

    locked_login = _login(client, "charlie", "charlie-pass")
    assert locked_login.status_code == 401

    unlock_resp = client.post(
        "/api/auth/unlock-user",
        json={"user_id": locked_user_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert unlock_resp.status_code == 200
    assert unlock_resp.get_json()["user"]["is_active"] is True

    unlocked_login = _login(client, "charlie", "charlie-pass")
    assert unlocked_login.status_code == 200


def test_lock_user_requires_super_admin(client, app):
    with app.app_context():
        _create_user("staff", "staff-pass", role_name="reception")
        target_user = _create_user("target", "target-pass", role_name="reception")
        target_user_id = target_user.id

    staff_login = _login(client, "staff", "staff-pass")
    staff_token = staff_login.get_json()["token"]

    resp = client.post(
        "/api/auth/lock-user",
        json={"user_id": target_user_id},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert resp.status_code == 403
