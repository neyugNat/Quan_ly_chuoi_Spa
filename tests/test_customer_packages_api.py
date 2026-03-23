# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false, reportCallIssue=false, reportAttributeAccessIssue=false

from backend.extensions import db
from backend.models.branch import Branch
from backend.models.user import Role, User


def _login(client, username, password):
    return client.post("/api/auth/login", json={"username": username, "password": password})


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


def _seed_manager_with_two_branches(app):
    with app.app_context():
        branch_one = Branch.query.first()
        assert branch_one is not None
        branch_two = Branch(name="Chi nhanh 2", address="Demo 2", status="active")
        branch_three = Branch(name="Chi nhanh 3", address="Demo 3", status="active")
        db.session.add_all([branch_two, branch_three])
        db.session.commit()

        manager = _create_user(
            "cp_manager",
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


def test_customer_packages_multi_branch_requires_branch_header(client, app):
    data = _seed_manager_with_two_branches(app)
    login_resp = _login(client, data["username"], "pass-123")
    token = login_resp.get_json()["token"]

    resp = client.get("/api/customer-packages", headers=_auth_header(token))
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "branch_required"


def test_customer_packages_create_list_get_update_in_scope(client, app):
    data = _seed_manager_with_two_branches(app)
    login_resp = _login(client, data["username"], "pass-123")
    token = login_resp.get_json()["token"]
    headers = _auth_header(token, data["branch_two_id"])

    customer_resp = client.post(
        "/api/customers",
        json={"full_name": "CP Customer", "phone": "0900999000"},
        headers=headers,
    )
    assert customer_resp.status_code == 201
    customer_id = customer_resp.get_json()["id"]

    package_resp = client.post(
        "/api/packages",
        json={"name": "CP Package", "sessions_total": 5, "validity_days": 30},
        headers=headers,
    )
    assert package_resp.status_code == 201
    package_id = package_resp.get_json()["id"]

    create_resp = client.post(
        "/api/customer-packages",
        json={"customer_id": customer_id, "package_id": package_id},
        headers=headers,
    )
    assert create_resp.status_code == 201
    created = create_resp.get_json()
    assert created["branch_id"] == data["branch_two_id"]
    assert created["customer_id"] == customer_id
    assert created["package_id"] == package_id
    assert created["sessions_total"] == 5
    assert created["sessions_remaining"] == 5
    assert created["status"] == "active"
    assert created["expires_at"] is not None

    cp_id = created["id"]

    list_resp = client.get(
        f"/api/customer-packages?customer_id={customer_id}",
        headers=headers,
    )
    assert list_resp.status_code == 200
    items = list_resp.get_json()["items"]
    assert any(item["id"] == cp_id for item in items)

    get_resp = client.get(f"/api/customer-packages/{cp_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.get_json()["id"] == cp_id

    update_resp = client.put(
        f"/api/customer-packages/{cp_id}",
        json={"sessions_remaining": 3, "status": "inactive"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    updated = update_resp.get_json()
    assert updated["sessions_remaining"] == 3
    assert updated["status"] == "inactive"


def test_customer_packages_validation_errors(client, app):
    data = _seed_manager_with_two_branches(app)
    login_resp = _login(client, data["username"], "pass-123")
    token = login_resp.get_json()["token"]
    headers = _auth_header(token, data["branch_one_id"])

    missing_fields = client.post(
        "/api/customer-packages",
        json={"customer_id": None, "package_id": None},
        headers=headers,
    )
    assert missing_fields.status_code == 400
    assert missing_fields.get_json()["error"] == "missing_fields"

    invalid_customer_id = client.get(
        "/api/customer-packages?customer_id=abc",
        headers=headers,
    )
    assert invalid_customer_id.status_code == 400
    assert invalid_customer_id.get_json()["error"] == "invalid_customer_id"
