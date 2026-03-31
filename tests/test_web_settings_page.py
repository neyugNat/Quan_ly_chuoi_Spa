def _staff_login(client, *, username="admin", password="admin123"):
    return client.post(
        "/web/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def test_web_settings_page_renders_for_staff(client):
    login_resp = _staff_login(client)
    assert login_resp.status_code == 200

    resp = client.get("/web/settings")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Tuỳ chỉnh giao diện, ngôn ngữ và hệ thống" in html
    assert "data-settings-root" in html
    assert "Lưu cài đặt" in html


def test_web_settings_change_password_happy_path(client):
    login_resp = _staff_login(client)
    assert login_resp.status_code == 200

    change_resp = client.post(
        "/web/settings/change-password",
        data={
            "old_password": "admin123",
            "new_password": "admin1234",
            "confirm_password": "admin1234",
        },
        follow_redirects=True,
    )
    assert change_resp.status_code == 200
    assert "Cập nhật mật khẩu thành công." in change_resp.get_data(as_text=True)

    client.post("/web/logout", follow_redirects=True)

    relogin_resp = _staff_login(client, password="admin1234")
    assert relogin_resp.status_code == 200
    assert "Tổng quan" in relogin_resp.get_data(as_text=True)

    restore_resp = client.post(
        "/web/settings/change-password",
        data={
            "old_password": "admin1234",
            "new_password": "admin123",
            "confirm_password": "admin123",
        },
        follow_redirects=True,
    )
    assert restore_resp.status_code == 200
    assert "Cập nhật mật khẩu thành công." in restore_resp.get_data(as_text=True)
