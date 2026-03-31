from backend.models.customer_account import CustomerAccount


def test_web_login_page_renders(client):
    resp = client.get("/web/login")
    assert resp.status_code == 200
    assert "Lotus Spa Management" in resp.get_data(as_text=True)


def test_web_customer_register_login_and_reset_flow(client, app):
    register_resp = client.post(
        "/web/customer/register",
        data={
            "full_name": "Khach Web",
            "email": "khach.web@example.com",
            "phone": "0900000000",
            "password": "secret123",
            "confirm_password": "secret123",
        },
        follow_redirects=True,
    )
    assert register_resp.status_code == 200
    assert "Tạo tài khoản thành công" in register_resp.get_data(as_text=True)

    login_resp = client.post(
        "/web/customer/login",
        data={"email": "khach.web@example.com", "password": "secret123"},
        follow_redirects=True,
    )
    assert login_resp.status_code == 200
    assert "Xin chào Khach Web" in login_resp.get_data(as_text=True)

    forgot_resp = client.post(
        "/web/customer/forgot-password",
        data={"email": "khach.web@example.com"},
        follow_redirects=True,
    )
    assert forgot_resp.status_code == 200
    assert "Nếu email tồn tại" in forgot_resp.get_data(as_text=True)

    with app.app_context():
        account = CustomerAccount.query.filter_by(email="khach.web@example.com").first()
        assert account is not None
        assert account.reset_password_token is not None
        token = account.reset_password_token

    reset_resp = client.post(
        "/web/customer/reset-password",
        data={
            "token": token,
            "new_password": "newsecret123",
            "confirm_password": "newsecret123",
        },
        follow_redirects=True,
    )
    assert reset_resp.status_code == 200
    assert "Đặt lại mật khẩu thành công" in reset_resp.get_data(as_text=True)

    relogin_resp = client.post(
        "/web/customer/login",
        data={"email": "khach.web@example.com", "password": "newsecret123"},
        follow_redirects=True,
    )
    assert relogin_resp.status_code == 200
    assert "Xin chào Khach Web" in relogin_resp.get_data(as_text=True)
