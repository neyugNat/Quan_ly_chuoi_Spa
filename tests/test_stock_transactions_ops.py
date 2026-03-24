# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false

from decimal import Decimal

from backend.extensions import db
from backend.models.branch import Branch
from backend.models.inventory_item import InventoryItem
from backend.models.stock_transaction import StockTransaction
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


def _seed_manager_and_inventory(app):
    with app.app_context():
        branch_one = Branch.query.first()
        assert branch_one is not None
        branch_two = Branch(name="Chi nhanh 2", address="Demo 2", status="active")
        branch_three = Branch(name="Chi nhanh 3", address="Demo 3", status="active")
        db.session.add_all([branch_two, branch_three])
        db.session.commit()

        manager = _create_user(
            "stock_manager",
            "pass-123",
            "branch_manager",
            [branch_one, branch_two],
        )

        inventory_item = InventoryItem(
            branch_id=branch_two.id,
            name="Tinh dau massage",
            sku="TD-001",
            unit="chai",
            min_stock=0,
            expiry_tracking=True,
            status="active",
        )
        db.session.add(inventory_item)
        db.session.commit()

        return {
            "username": manager.username,
            "branch_one_id": branch_one.id,
            "branch_two_id": branch_two.id,
            "branch_three_id": branch_three.id,
            "inventory_item_id": inventory_item.id,
        }


def _auth_header(token, branch_id=None):
    headers = {"Authorization": f"Bearer {token}"}
    if branch_id is not None:
        headers["X-Branch-Id"] = str(branch_id)
    return headers


def test_stock_transactions_require_valid_branch_scope(client, app):
    data = _seed_manager_and_inventory(app)
    login_resp = _login(client, data["username"], "pass-123")
    token = login_resp.get_json()["token"]

    branch_required_resp = client.get(
        "/api/stock-transactions",
        headers=_auth_header(token),
    )
    assert branch_required_resp.status_code == 400
    assert branch_required_resp.get_json()["error"] == "branch_required"

    forbidden_branch_resp = client.get(
        "/api/stock-transactions",
        headers=_auth_header(token, data["branch_three_id"]),
    )
    assert forbidden_branch_resp.status_code == 403
    assert forbidden_branch_resp.get_json()["error"] == "forbidden_branch"


def test_create_stock_in_then_out_and_list_items(client, app):
    data = _seed_manager_and_inventory(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_two_id"])

    create_in_resp = client.post(
        "/api/stock-transactions",
        json={
            "inventory_item_id": data["inventory_item_id"],
            "transaction_type": "in",
            "qty": "5.250",
            "expiry_date": "2026-12-31",
            "note": "Nhap kho lan 1",
        },
        headers=headers,
    )
    assert create_in_resp.status_code == 201
    created_in = create_in_resp.get_json()
    assert created_in["delta_qty"] == 5.25
    assert created_in["source_type"] is None
    assert created_in["source_id"] is None

    create_out_resp = client.post(
        "/api/stock-transactions",
        json={
            "inventory_item_id": data["inventory_item_id"],
            "transaction_type": "out",
            "qty": "2.125",
            "note": "Xuat dung",
        },
        headers=headers,
    )
    assert create_out_resp.status_code == 201
    created_out = create_out_resp.get_json()
    assert created_out["delta_qty"] == -2.125

    list_resp = client.get(
        f"/api/stock-transactions?inventory_item_id={data['inventory_item_id']}",
        headers=headers,
    )
    assert list_resp.status_code == 200
    items = list_resp.get_json()["items"]
    assert len(items) == 2
    assert {item["transaction_type"] for item in items} == {"in", "out"}

    with app.app_context():
        total_stock = (
            db.session.query(db.func.sum(StockTransaction.delta_qty))
            .filter(
                StockTransaction.branch_id == data["branch_two_id"],
                StockTransaction.inventory_item_id == data["inventory_item_id"],
            )
            .scalar()
        )
        assert total_stock == Decimal("3.125")


def test_adjust_negative_blocked_when_stock_would_go_below_zero(client, app):
    data = _seed_manager_and_inventory(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_two_id"])

    seed_resp = client.post(
        "/api/stock-transactions",
        json={
            "inventory_item_id": data["inventory_item_id"],
            "transaction_type": "in",
            "qty": "1.000",
        },
        headers=headers,
    )
    assert seed_resp.status_code == 201

    adjust_resp = client.post(
        "/api/stock-transactions",
        json={
            "inventory_item_id": data["inventory_item_id"],
            "transaction_type": "adjust",
            "delta_qty": "-1.500",
        },
        headers=headers,
    )
    assert adjust_resp.status_code == 400
    assert adjust_resp.get_json()["error"] == "insufficient_stock"


def test_out_blocked_when_insufficient_stock(client, app):
    data = _seed_manager_and_inventory(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]
    headers = _auth_header(token, data["branch_two_id"])

    out_resp = client.post(
        "/api/stock-transactions",
        json={
            "inventory_item_id": data["inventory_item_id"],
            "transaction_type": "out",
            "qty": "0.250",
        },
        headers=headers,
    )
    assert out_resp.status_code == 400
    assert out_resp.get_json()["error"] == "insufficient_stock"
