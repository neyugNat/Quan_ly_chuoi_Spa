def test_customer_register_and_login_happy_path(client):
    register_resp = client.post(
        "/api/customer-auth/register",
        json={
            "full_name": "Khach Test",
            "email": "khach.test@example.com",
            "password": "secret123",
            "phone": "0901234567",
        },
    )
    assert register_resp.status_code == 201
    register_data = register_resp.get_json()
    assert register_data["account"]["email"] == "khach.test@example.com"
    assert register_data["account"]["customer"]["full_name"] == "Khach Test"

    login_resp = client.post(
        "/api/customer-auth/login",
        json={"email": "khach.test@example.com", "password": "secret123"},
    )
    assert login_resp.status_code == 200
    login_data = login_resp.get_json()
    assert login_data["token"]
    assert login_data["account"]["customer"]["full_name"] == "Khach Test"


def test_customer_me_requires_customer_token(client):
    register_resp = client.post(
        "/api/customer-auth/register",
        json={
            "full_name": "Me Test",
            "email": "me.test@example.com",
            "password": "secret123",
        },
    )
    token = register_resp.get_json()["token"]

    me_resp = client.get(
        "/api/customer-auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    me_data = me_resp.get_json()
    assert me_data["email"] == "me.test@example.com"
    assert me_data["customer"]["full_name"] == "Me Test"


def test_customer_forgot_and_reset_password_happy_path(client):
    register_resp = client.post(
        "/api/customer-auth/register",
        json={
            "full_name": "Reset Test",
            "email": "reset.test@example.com",
            "password": "oldpass123",
        },
    )
    assert register_resp.status_code == 201

    forgot_resp = client.post(
        "/api/customer-auth/forgot-password",
        json={"email": "reset.test@example.com"},
    )
    assert forgot_resp.status_code == 200
    forgot_data = forgot_resp.get_json()
    assert forgot_data["status"] == "ok"
    assert forgot_data["reset_token"]

    reset_resp = client.post(
        "/api/customer-auth/reset-password",
        json={
            "token": forgot_data["reset_token"],
            "new_password": "newpass123",
        },
    )
    assert reset_resp.status_code == 200
    assert reset_resp.get_json()["status"] == "ok"

    old_login = client.post(
        "/api/customer-auth/login",
        json={"email": "reset.test@example.com", "password": "oldpass123"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/customer-auth/login",
        json={"email": "reset.test@example.com", "password": "newpass123"},
    )
    assert new_login.status_code == 200


def test_customer_register_rejects_duplicate_email(client):
    first_resp = client.post(
        "/api/customer-auth/register",
        json={
            "full_name": "A",
            "email": "dup@example.com",
            "password": "secret123",
        },
    )
    assert first_resp.status_code == 201

    second_resp = client.post(
        "/api/customer-auth/register",
        json={
            "full_name": "B",
            "email": "dup@example.com",
            "password": "secret123",
        },
    )
    assert second_resp.status_code == 409
    assert second_resp.get_json()["error"] == "email_exists"
