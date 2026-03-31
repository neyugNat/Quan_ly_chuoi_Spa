from backend.models.customer import Customer


def _staff_login(client, *, username="admin", password="admin123"):
    return client.post(
        "/web/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def test_web_customers_page_renders_legacy_layout(client):
    login_resp = _staff_login(client)
    assert login_resp.status_code == 200

    resp = client.get("/web/customers")
    assert resp.status_code == 200

    html = resp.get_data(as_text=True)
    assert "Quản lý hồ sơ và hành trình khách hàng" in html
    assert "Thêm khách hàng" in html
    assert "Tổng khách hàng" in html
    assert "Tìm tên, số điện thoại..." in html
    assert "data-customers-root" in html
    assert "Ngày sinh:" not in html
    assert "data-page-status" in html
    assert "data-page-prev" in html
    assert "data-page-next" in html


def test_web_customers_create_from_modal_form(client, app):
    login_resp = _staff_login(client)
    assert login_resp.status_code == 200

    phone = "0999888777"
    create_resp = client.post(
        "/web/customers/create",
        data={
            "full_name": "Khach Them Moi",
            "phone": phone,
            "email": "khach.them.moi@example.com",
            "dob": "1997-10-11",
            "note": "Ghi chu test web",
        },
        follow_redirects=True,
    )
    assert create_resp.status_code == 200
    html = create_resp.get_data(as_text=True)
    assert "Đã thêm khách hàng mới." in html
    assert "11/10/1997" in html

    with app.app_context():
        customer = Customer.query.filter_by(phone=phone).first()
        assert customer is not None
        assert customer.full_name == "Khach Them Moi"
