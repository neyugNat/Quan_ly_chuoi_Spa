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
            "staff_manager",
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

    resp = client.get("/api/staffs", headers=_auth_header(token))
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "branch_required"


def test_user_cannot_access_staffs_outside_branch_scope(client, app):
    data = _seed_branch_manager_with_two_branches(app)
    login_resp = _login(client, data["username"], "pass-123")
    token = login_resp.get_json()["token"]

    resp = client.get(
        "/api/staffs",
        headers=_auth_header(token, data["branch_three_id"]),
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "forbidden_branch"


def test_staffs_create_list_get_update_in_scope(client, app):
    data = _seed_branch_manager_with_two_branches(app)
    login_resp = _login(client, data["username"], "pass-123")
    token = login_resp.get_json()["token"]
    headers = _auth_header(token, data["branch_two_id"])

    create_resp = client.post(
        "/api/staffs",
        json={
            "branch_id": data["branch_one_id"],
            "full_name": "Nguyen Van A",
            "phone": "0901234567",
            "title": "Therapist",
            "role": "senior_therapist",
            "skill_level": "L2",
            "user_id": None,
            "commission_scheme_json": '{"service": 0.1}',
            "status": "active",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    created = create_resp.get_json()
    assert created["branch_id"] == data["branch_two_id"]
    assert created["full_name"] == "Nguyen Van A"
    assert created["role"] == "senior_therapist"
    assert created["skill_level"] == "L2"
    assert created["status"] == "active"

    staff_id = created["id"]

    list_resp = client.get("/api/staffs", headers=headers)
    assert list_resp.status_code == 200
    items = list_resp.get_json()["items"]
    assert any(item["id"] == staff_id for item in items)

    get_resp = client.get(f"/api/staffs/{staff_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.get_json()["id"] == staff_id

    wrong_branch_resp = client.get(
        f"/api/staffs/{staff_id}",
        headers=_auth_header(token, data["branch_one_id"]),
    )
    assert wrong_branch_resp.status_code == 404
    assert wrong_branch_resp.get_json()["error"] == "not_found"

    update_resp = client.put(
        f"/api/staffs/{staff_id}",
        json={
            "full_name": "Nguyen Van B",
            "phone": None,
            "title": "Lead Therapist",
            "role": "branch_trainer",
            "skill_level": "L3",
            "user_id": 1,
            "commission_scheme_json": None,
            "status": "inactive",
            "branch_id": data["branch_one_id"],
        },
        headers=headers,
    )
    assert update_resp.status_code == 200
    updated = update_resp.get_json()
    assert updated["full_name"] == "Nguyen Van B"
    assert updated["phone"] is None
    assert updated["title"] == "Lead Therapist"
    assert updated["role"] == "branch_trainer"
    assert updated["skill_level"] == "L3"
    assert updated["user_id"] == 1
    assert updated["commission_scheme_json"] is None
    assert updated["status"] == "inactive"
    assert updated["branch_id"] == data["branch_two_id"]


def test_staffs_validation_errors_return_400(client, app):
    data = _seed_branch_manager_with_two_branches(app)
    login_resp = _login(client, data["username"], "pass-123")
    token = login_resp.get_json()["token"]
    headers = _auth_header(token, data["branch_one_id"])

    missing_fields_resp = client.post(
        "/api/staffs",
        json={"full_name": ""},
        headers=headers,
    )
    assert missing_fields_resp.status_code == 400
    assert missing_fields_resp.get_json()["error"] == "missing_fields"

    invalid_status_resp = client.post(
        "/api/staffs",
        json={"full_name": "Tran B", "status": "blocked"},
        headers=headers,
    )
    assert invalid_status_resp.status_code == 400
    assert invalid_status_resp.get_json()["error"] == "invalid_status"

    create_resp = client.post(
        "/api/staffs",
        json={"full_name": "Le C"},
        headers=headers,
    )
    staff_id = create_resp.get_json()["id"]

    invalid_update_resp = client.put(
        f"/api/staffs/{staff_id}",
        json={"status": "invalid"},
        headers=headers,
    )
    assert invalid_update_resp.status_code == 400
    assert invalid_update_resp.get_json()["error"] == "invalid_status"
