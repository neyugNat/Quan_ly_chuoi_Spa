def _staff_login(client, *, username="admin", password="admin123"):
    return client.post(
        "/web/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def test_web_hr_page_renders_custom_layout(client):
    login_resp = _staff_login(client)
    assert login_resp.status_code == 200

    resp = client.get("/web/hr")
    assert resp.status_code == 200

    html = resp.get_data(as_text=True)
    assert "Quản lý đội ngũ nhân viên toàn hệ thống" in html
    assert "data-hr-root" in html
    assert "Thêm nhân viên" in html
    assert "Du lieu dong bo tu backend" not in html


def test_web_reports_page_renders_custom_layout(client):
    login_resp = _staff_login(client)
    assert login_resp.status_code == 200

    resp = client.get("/web/reports")
    assert resp.status_code == 200

    html = resp.get_data(as_text=True)
    assert "Phân tích hiệu suất kinh doanh toàn chuỗi" in html
    assert "legacy-reports-page" in html
    assert "Doanh thu theo tháng" in html
    assert "Top dịch vụ theo doanh thu" in html
    assert "Du lieu dong bo tu backend" not in html


def test_web_audit_logs_page_renders_custom_layout(client):
    login_resp = _staff_login(client)
    assert login_resp.status_code == 200

    resp = client.get("/web/audit-logs")
    assert resp.status_code == 200

    html = resp.get_data(as_text=True)
    assert "Theo dõi toàn bộ hoạt động" in html
    assert "data-audit-root" in html
    assert "Nhật ký hệ thống" in html
    assert "data-audit-search" in html
    assert "Du lieu dong bo tu backend" not in html
