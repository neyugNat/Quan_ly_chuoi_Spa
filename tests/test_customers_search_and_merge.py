# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false

import json

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


def _seed_reception_with_two_branches(app):
    with app.app_context():
        branch_one = Branch.query.first()
        branch_two = Branch(name="Chi nhanh 2", address="Demo 2", status="active")
        db.session.add(branch_two)
        db.session.commit()

        user = _create_user("customer_reception", "pass-123", "reception", [branch_one, branch_two])
        return {
            "username": user.username,
            "branch_one_id": branch_one.id,
            "branch_two_id": branch_two.id,
        }


def _auth_header(token, branch_id=None):
    headers = {"Authorization": f"Bearer {token}"}
    if branch_id is not None:
        headers["X-Branch-Id"] = str(branch_id)
    return headers


def _create_customer(client, headers, full_name, phone, **extra):
    payload = {"full_name": full_name, "phone": phone}
    payload.update(extra)
    resp = client.post("/api/customers", json=payload, headers=headers)
    assert resp.status_code == 201
    return resp.get_json()


def test_customers_tag_filter_returns_expected_items(client, app):
    data = _seed_reception_with_two_branches(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]

    branch_one_headers = _auth_header(token, data["branch_one_id"])
    branch_two_headers = _auth_header(token, data["branch_two_id"])

    vip_one = _create_customer(
        client,
        branch_one_headers,
        "Khach VIP 1",
        "0900000001",
        tags_json=["vip", "new"],
    )
    _create_customer(
        client,
        branch_one_headers,
        "Khach Thuong",
        "0900000002",
        tags_json=["regular"],
    )
    vip_two = _create_customer(
        client,
        branch_one_headers,
        "Khach VIP 2",
        "0900000003",
        tags_json="vip",
    )
    _create_customer(
        client,
        branch_two_headers,
        "Khach VIP Branch 2",
        "0900000099",
        tags_json=["vip"],
    )

    resp = client.get("/api/customers?tag=vip", headers=branch_one_headers)
    assert resp.status_code == 200
    items = resp.get_json()["items"]
    ids = {item["id"] for item in items}

    assert vip_one["id"] in ids
    assert vip_two["id"] in ids
    assert all(item["branch_id"] == data["branch_one_id"] for item in items)


def test_merge_customer_merges_tags_and_marks_source_merged(client, app):
    data = _seed_reception_with_two_branches(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_one_id"])

    target = _create_customer(
        client,
        headers,
        "Khach Target",
        "0910000001",
        tags_json=["vip"],
    )
    source = _create_customer(
        client,
        headers,
        "Khach Source",
        "0910000002",
        email="source@example.com",
        address="123 Demo",
        dob="1990-01-02",
        gender="female",
        tags_json=["loyal", "vip"],
    )

    merge_resp = client.post(
        f"/api/customers/{target['id']}/merge",
        json={"source_customer_id": source["id"]},
        headers=headers,
    )
    assert merge_resp.status_code == 200
    body = merge_resp.get_json()

    target_after = body["target"]
    source_after = body["source"]
    assert target_after["email"] == "source@example.com"
    assert target_after["address"] == "123 Demo"
    assert target_after["dob"] == "1990-01-02"
    assert target_after["gender"] == "female"
    assert json.loads(target_after["tags_json"]) == ["loyal", "vip"]
    assert source_after["status"] == "merged"


def test_merge_customer_rejects_cross_branch_source_id(client, app):
    data = _seed_reception_with_two_branches(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]

    branch_one_headers = _auth_header(token, data["branch_one_id"])
    branch_two_headers = _auth_header(token, data["branch_two_id"])

    target = _create_customer(client, branch_one_headers, "Target", "0920000001", tags_json=["a"])
    source = _create_customer(client, branch_two_headers, "Source", "0920000002", tags_json=["b"])

    merge_resp = client.post(
        f"/api/customers/{target['id']}/merge",
        json={"source_customer_id": source["id"]},
        headers=branch_one_headers,
    )
    assert merge_resp.status_code == 403
    assert merge_resp.get_json()["error"] == "forbidden_branch"
