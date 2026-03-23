# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false, reportCallIssue=false, reportAttributeAccessIssue=false

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


def _seed_branch_manager_with_two_branches(app):
    with app.app_context():
        branch_one = Branch.query.first()
        assert branch_one is not None
        branch_two = Branch(name="Chi nhanh 2", address="Demo 2", status="active")
        branch_three = Branch(name="Chi nhanh 3", address="Demo 3", status="active")
        db.session.add_all([branch_two, branch_three])
        db.session.commit()

        manager = _create_user(
            "service_manager",
            "pass-123",
            "branch_manager",
            [branch_one, branch_two],
        )
        return {
            "username": manager.username,
            "branch_one_id": branch_one.id,
            "branch_two_id": branch_two.id,
            "branch_three_id": branch_three.id,
        }


def _auth_header(token, branch_id=None):
    headers = {"Authorization": f"Bearer {token}"}
    if branch_id is not None:
        headers["X-Branch-Id"] = str(branch_id)
    return headers


def test_multi_branch_user_must_provide_branch_header(client, app):
    data = _seed_branch_manager_with_two_branches(app)
    login_resp = _login(client, data["username"], "pass-123")
    token = login_resp.get_json()["token"]

    resp = client.get("/api/services", headers=_auth_header(token))
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "branch_required"


def test_user_cannot_access_service_outside_branch_scope(client, app):
    data = _seed_branch_manager_with_two_branches(app)
    login_resp = _login(client, data["username"], "pass-123")
    token = login_resp.get_json()["token"]

    resp = client.get(
        "/api/services",
        headers=_auth_header(token, data["branch_three_id"]),
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "forbidden_branch"


def test_services_create_list_get_update_in_scope(client, app):
    data = _seed_branch_manager_with_two_branches(app)
    login_resp = _login(client, data["username"], "pass-123")
    token = login_resp.get_json()["token"]
    headers = _auth_header(token, data["branch_two_id"])

    create_resp = client.post(
        "/api/services",
        json={
            "name": "Goi cham soc da",
            "price": 299000,
            "duration_minutes": 75,
            "status": "active",
            "requirement_json": '{"skills":["facial"]}',
            "consumable_recipe_json": '{"consumables":[{"sku":"MASK-01","qty":1}]}',
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    created = create_resp.get_json()
    assert created["branch_id"] == data["branch_two_id"]
    assert created["name"] == "Goi cham soc da"
    assert created["price"] == 299000.0
    assert created["duration_minutes"] == 75
    assert created["status"] == "active"

    service_id = created["id"]

    list_resp = client.get("/api/services", headers=headers)
    assert list_resp.status_code == 200
    items = list_resp.get_json()["items"]
    assert any(item["id"] == service_id for item in items)

    get_resp = client.get(f"/api/services/{service_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.get_json()["id"] == service_id

    update_resp = client.put(
        f"/api/services/{service_id}",
        json={
            "name": "Goi cham soc da nang cao",
            "price": "349000.50",
            "duration_minutes": "90",
            "status": "inactive",
            "requirement_json": '{"skills":["facial","massage"]}',
        },
        headers=headers,
    )
    assert update_resp.status_code == 200
    updated = update_resp.get_json()
    assert updated["name"] == "Goi cham soc da nang cao"
    assert updated["price"] == 349000.5
    assert updated["duration_minutes"] == 90
    assert updated["status"] == "inactive"


def test_services_validation_errors_return_400(client, app):
    data = _seed_branch_manager_with_two_branches(app)
    login_resp = _login(client, data["username"], "pass-123")
    token = login_resp.get_json()["token"]
    headers = _auth_header(token, data["branch_one_id"])

    missing_fields_resp = client.post(
        "/api/services",
        json={"name": "", "price": -1, "duration_minutes": 0},
        headers=headers,
    )
    assert missing_fields_resp.status_code == 400
    assert missing_fields_resp.get_json()["error"] == "missing_fields"

    invalid_status_resp = client.post(
        "/api/services",
        json={
            "name": "Massage",
            "price": 100000,
            "duration_minutes": 60,
            "status": "paused",
        },
        headers=headers,
    )
    assert invalid_status_resp.status_code == 400
    assert invalid_status_resp.get_json()["error"] == "invalid_status"
