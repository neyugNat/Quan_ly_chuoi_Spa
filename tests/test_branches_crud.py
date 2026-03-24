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


def test_super_admin_can_create_update_list_get_branches(client):
    admin_login = _login(client, "admin", "admin123")
    admin_token = admin_login.get_json()["token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    create_resp = client.post(
        "/api/branches",
        json={
            "name": "Chi nhanh 2",
            "address": "123 Test",
            "working_hours_json": '{"mon":"09:00-18:00"}',
            "status": "inactive",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    created = create_resp.get_json()
    assert created["name"] == "Chi nhanh 2"
    assert created["address"] == "123 Test"
    assert created["working_hours_json"] == '{"mon":"09:00-18:00"}'
    assert created["status"] == "inactive"

    branch_id = created["id"]

    get_resp = client.get(f"/api/branches/{branch_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.get_json()["id"] == branch_id

    update_resp = client.put(
        f"/api/branches/{branch_id}",
        json={
            "name": "Chi nhanh 2 - Updated",
            "address": "456 Update",
            "status": "active",
            "working_hours_json": '{"tue":"10:00-19:00"}',
        },
        headers=headers,
    )
    assert update_resp.status_code == 200
    updated = update_resp.get_json()
    assert updated["name"] == "Chi nhanh 2 - Updated"
    assert updated["address"] == "456 Update"
    assert updated["status"] == "active"
    assert updated["working_hours_json"] == '{"tue":"10:00-19:00"}'

    list_resp = client.get("/api/branches", headers=headers)
    assert list_resp.status_code == 200
    body = list_resp.get_json()
    assert "items" in body
    assert any(item["id"] == branch_id for item in body["items"])


def test_create_branch_missing_name_returns_400(client):
    admin_login = _login(client, "admin", "admin123")
    admin_token = admin_login.get_json()["token"]

    resp = client.post(
        "/api/branches",
        json={"name": "   "},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "missing_fields"


def test_non_super_admin_cannot_access_branches_endpoints(client, app):
    with app.app_context():
        _create_user("branch_reception", "pass-123", role_name="reception")

    login_resp = _login(client, "branch_reception", "pass-123")
    token = login_resp.get_json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    list_resp = client.get("/api/branches", headers=headers)
    assert list_resp.status_code == 403
    assert list_resp.get_json()["error"] == "forbidden"

    create_resp = client.post("/api/branches", json={"name": "Unauthorized"}, headers=headers)
    assert create_resp.status_code == 403
    assert create_resp.get_json()["error"] == "forbidden"
