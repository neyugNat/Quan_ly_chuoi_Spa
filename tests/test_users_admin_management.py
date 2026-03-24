from backend.extensions import db
from backend.models.audit_log import AuditLog
from backend.models.branch import Branch
from backend.models.staff import Staff
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


def test_super_admin_can_create_list_set_password_and_delete_user(client, app):
    with app.app_context():
        staff = Staff(
            branch_id=1,
            full_name="Test Staff",
            phone="0900000000",
            title="Nhan vien",
            role="technician",
            skill_level="middle",
            status="active",
        )
        db.session.add(staff)
        db.session.commit()
        staff_id = staff.id

    admin_login = _login(client, "admin", "admin123")
    admin_token = admin_login.get_json()["token"]

    branches = client.get(
        "/api/branches",
        headers={"Authorization": f"Bearer {admin_token}"},
    ).get_json()["items"]
    branch_ids = [branches[0]["id"]]

    create_resp = client.post(
        "/api/users",
        json={
            "username": "new_employee",
            "password": "pass123",
            "role_names": ["technician"],
            "branch_ids": branch_ids,
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_resp.status_code == 201
    user_id = create_resp.get_json()["id"]

    list_resp = client.get(
        "/api/users?q=new_",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_resp.status_code == 200
    assert any(item["id"] == user_id for item in list_resp.get_json()["items"])

    link_resp = client.put(
        f"/api/staffs/{staff_id}",
        json={"user_id": user_id},
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Branch-Id": str(branch_ids[0]),
        },
    )
    assert link_resp.status_code == 200
    assert link_resp.get_json()["user_id"] == user_id

    set_pw_resp = client.post(
        f"/api/users/{user_id}/set-password",
        json={"new_password": "newpass456"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert set_pw_resp.status_code == 200

    assert _login(client, "new_employee", "pass123").status_code == 401
    assert _login(client, "new_employee", "newpass456").status_code == 200

    delete_resp = client.delete(
        f"/api/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert delete_resp.status_code == 200

    assert _login(client, "new_employee", "newpass456").status_code == 401

    with app.app_context():
        staff = Staff.query.get(staff_id)
        assert staff is not None
        assert staff.user_id is None

        actions = {row.action for row in AuditLog.query.filter(AuditLog.action.in_(["user.create", "user.set_password", "user.delete"]))}
        assert {"user.create", "user.set_password", "user.delete"}.issubset(actions)


def test_users_endpoints_require_super_admin(client, app):
    with app.app_context():
        _create_user("staff_user", "staff-pass", role_name="reception")

    staff_login = _login(client, "staff_user", "staff-pass")
    staff_token = staff_login.get_json()["token"]

    resp = client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "forbidden"
