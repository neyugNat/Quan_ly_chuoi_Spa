# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false, reportCallIssue=false, reportAttributeAccessIssue=false

from backend.extensions import db
from backend.models.branch import Branch
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


def _seed_branch_manager_with_two_branches(app):
    with app.app_context():
        branch_one = Branch.query.first()
        assert branch_one is not None

        branch_two = Branch(name="Chi nhanh 2", address="Demo 2", status="active")
        branch_three = Branch(name="Chi nhanh 3", address="Demo 3", status="active")
        db.session.add_all([branch_two, branch_three])
        db.session.commit()

        staff_one = Staff(branch_id=branch_one.id, full_name="Staff One", status="active")
        staff_two = Staff(branch_id=branch_two.id, full_name="Staff Two", status="active")
        staff_three = Staff(branch_id=branch_three.id, full_name="Staff Three", status="active")
        db.session.add_all([staff_one, staff_two, staff_three])
        db.session.commit()

        manager = _create_user(
            "shift_manager",
            "pass-123",
            "branch_manager",
            [branch_one, branch_two],
        )
        return {
            "username": manager.username,
            "branch_one_id": branch_one.id,
            "branch_two_id": branch_two.id,
            "branch_three_id": branch_three.id,
            "staff_one_id": staff_one.id,
            "staff_two_id": staff_two.id,
            "staff_three_id": staff_three.id,
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

    resp = client.get("/api/shifts", headers=_auth_header(token))
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "branch_required"


def test_user_cannot_access_shifts_outside_branch_scope(client, app):
    data = _seed_branch_manager_with_two_branches(app)
    login_resp = _login(client, data["username"], "pass-123")
    token = login_resp.get_json()["token"]

    resp = client.get(
        "/api/shifts",
        headers=_auth_header(token, data["branch_three_id"]),
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "forbidden_branch"


def test_shifts_create_list_get_update_in_scope(client, app):
    data = _seed_branch_manager_with_two_branches(app)
    login_resp = _login(client, data["username"], "pass-123")
    token = login_resp.get_json()["token"]
    headers = _auth_header(token, data["branch_two_id"])

    create_resp = client.post(
        "/api/shifts",
        json={
            "staff_id": data["staff_two_id"],
            "start_time": "2026-03-20T08:00:00Z",
            "end_time": "2026-03-20T16:00:00Z",
            "status": "active",
            "note": "Ca sang",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    created = create_resp.get_json()
    assert created["branch_id"] == data["branch_two_id"]
    assert created["staff_id"] == data["staff_two_id"]
    assert created["status"] == "active"
    assert created["note"] == "Ca sang"

    shift_id = created["id"]

    list_resp = client.get("/api/shifts", headers=headers)
    assert list_resp.status_code == 200
    items = list_resp.get_json()["items"]
    assert any(item["id"] == shift_id for item in items)

    get_resp = client.get(f"/api/shifts/{shift_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.get_json()["id"] == shift_id

    update_resp = client.put(
        f"/api/shifts/{shift_id}",
        json={
            "start_time": "2026-03-20T09:00:00",
            "end_time": "2026-03-20T17:30:00",
            "status": "inactive",
            "note": None,
            "staff_id": data["staff_two_id"],
        },
        headers=headers,
    )
    assert update_resp.status_code == 200
    updated = update_resp.get_json()
    assert updated["start_time"] == "2026-03-20T09:00:00"
    assert updated["end_time"] == "2026-03-20T17:30:00"
    assert updated["status"] == "inactive"
    assert updated["note"] is None


def test_shift_get_wrong_branch_returns_404(client, app):
    data = _seed_branch_manager_with_two_branches(app)
    login_resp = _login(client, data["username"], "pass-123")
    token = login_resp.get_json()["token"]

    create_resp = client.post(
        "/api/shifts",
        json={
            "staff_id": data["staff_two_id"],
            "start_time": "2026-03-20T08:00:00",
            "end_time": "2026-03-20T16:00:00",
        },
        headers=_auth_header(token, data["branch_two_id"]),
    )
    shift_id = create_resp.get_json()["id"]

    wrong_branch_resp = client.get(
        f"/api/shifts/{shift_id}",
        headers=_auth_header(token, data["branch_one_id"]),
    )
    assert wrong_branch_resp.status_code == 404
    assert wrong_branch_resp.get_json()["error"] == "not_found"


def test_shifts_invalid_time_range_returns_missing_fields(client, app):
    data = _seed_branch_manager_with_two_branches(app)
    login_resp = _login(client, data["username"], "pass-123")
    token = login_resp.get_json()["token"]
    headers = _auth_header(token, data["branch_two_id"])

    invalid_create_resp = client.post(
        "/api/shifts",
        json={
            "staff_id": data["staff_two_id"],
            "start_time": "2026-03-20T16:00:00",
            "end_time": "2026-03-20T08:00:00",
        },
        headers=headers,
    )
    assert invalid_create_resp.status_code == 400
    assert invalid_create_resp.get_json()["error"] == "missing_fields"

    create_resp = client.post(
        "/api/shifts",
        json={
            "staff_id": data["staff_two_id"],
            "start_time": "2026-03-20T08:00:00",
            "end_time": "2026-03-20T16:00:00",
        },
        headers=headers,
    )
    shift_id = create_resp.get_json()["id"]

    invalid_update_resp = client.put(
        f"/api/shifts/{shift_id}",
        json={"end_time": "2026-03-20T07:59:00"},
        headers=headers,
    )
    assert invalid_update_resp.status_code == 400
    assert invalid_update_resp.get_json()["error"] == "missing_fields"


def test_shifts_invalid_status_returns_400_invalid_status(client, app):
    data = _seed_branch_manager_with_two_branches(app)
    login_resp = _login(client, data["username"], "pass-123")
    token = login_resp.get_json()["token"]
    headers = _auth_header(token, data["branch_two_id"])

    invalid_create_resp = client.post(
        "/api/shifts",
        json={
            "staff_id": data["staff_two_id"],
            "start_time": "2026-03-20T08:00:00",
            "end_time": "2026-03-20T16:00:00",
            "status": "paused",
        },
        headers=headers,
    )
    assert invalid_create_resp.status_code == 400
    assert invalid_create_resp.get_json()["error"] == "invalid_status"

    create_resp = client.post(
        "/api/shifts",
        json={
            "staff_id": data["staff_two_id"],
            "start_time": "2026-03-20T08:00:00",
            "end_time": "2026-03-20T16:00:00",
        },
        headers=headers,
    )
    shift_id = create_resp.get_json()["id"]

    invalid_update_resp = client.put(
        f"/api/shifts/{shift_id}",
        json={"status": "blocked"},
        headers=headers,
    )
    assert invalid_update_resp.status_code == 400
    assert invalid_update_resp.get_json()["error"] == "invalid_status"
