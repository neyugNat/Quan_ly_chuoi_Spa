from backend.extensions import db
from backend.models.branch import Branch
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


def _seed_scope_users(app):
    with app.app_context():
        branch_one = Branch.query.first()
        branch_two = Branch(name="Chi nhanh 2", address="Demo 2", status="active")
        db.session.add(branch_two)
        db.session.commit()

        single_branch_user = _create_user(
            "scope_one",
            "pass-123",
            "reception",
            [branch_one],
        )
        multi_branch_user = _create_user(
            "scope_many",
            "pass-123",
            "reception",
            [branch_one, branch_two],
        )
        forbidden_role_user = _create_user(
            "scope_tech",
            "pass-123",
            "technician",
            [branch_one],
        )
        return {
            "branch_one_id": branch_one.id,
            "branch_two_id": branch_two.id,
            "single_username": single_branch_user.username,
            "multi_username": multi_branch_user.username,
            "forbidden_username": forbidden_role_user.username,
        }


def test_customers_requires_allowed_roles(client, app):
    data = _seed_scope_users(app)
    login_resp = _login(client, data["forbidden_username"], "pass-123")
    token = login_resp.get_json()["token"]

    resp = client.get(
        "/api/customers",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Branch-Id": str(data["branch_one_id"]),
        },
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "forbidden"


def test_cannot_access_branch_outside_scope(client, app):
    data = _seed_scope_users(app)
    login_resp = _login(client, data["single_username"], "pass-123")
    token = login_resp.get_json()["token"]

    resp = client.get(
        "/api/customers",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Branch-Id": str(data["branch_two_id"]),
        },
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "forbidden_branch"


def test_multiple_branches_require_explicit_branch_header(client, app):
    data = _seed_scope_users(app)
    login_resp = _login(client, data["multi_username"], "pass-123")
    token = login_resp.get_json()["token"]

    resp = client.get(
        "/api/customers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "branch_required"


def test_single_branch_auto_selects_when_header_missing(client, app):
    data = _seed_scope_users(app)
    login_resp = _login(client, data["single_username"], "pass-123")
    token = login_resp.get_json()["token"]

    resp = client.post(
        "/api/customers",
        json={"full_name": "Scope User", "phone": "0900000000"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["branch_id"] == data["branch_one_id"]
