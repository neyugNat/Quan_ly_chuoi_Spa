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
            "report_manager",
            "pass-123",
            "branch_manager",
            [branch_one, branch_two],
        )

        item_no_tx = InventoryItem(
            branch_id=branch_two.id,
            name="Bot tao bien",
            sku="BTB-001",
            unit="goi",
            min_stock=Decimal("5.000"),
            expiry_tracking=False,
            status="active",
        )
        item_low = InventoryItem(
            branch_id=branch_two.id,
            name="Kem massage",
            sku="KM-001",
            unit="hop",
            min_stock=Decimal("10.000"),
            expiry_tracking=False,
            status="active",
        )
        item_above_min = InventoryItem(
            branch_id=branch_two.id,
            name="Tinh dau",
            sku="TD-001",
            unit="chai",
            min_stock=Decimal("2.000"),
            expiry_tracking=True,
            status="active",
        )
        item_inactive = InventoryItem(
            branch_id=branch_two.id,
            name="Muoi ngam",
            sku="MN-001",
            unit="goi",
            min_stock=Decimal("8.000"),
            expiry_tracking=False,
            status="inactive",
        )
        db.session.add_all([item_no_tx, item_low, item_above_min, item_inactive])
        db.session.flush()

        db.session.add_all(
            [
                StockTransaction(
                    branch_id=branch_two.id,
                    inventory_item_id=item_low.id,
                    transaction_type="in",
                    delta_qty=Decimal("3.000"),
                ),
                StockTransaction(
                    branch_id=branch_two.id,
                    inventory_item_id=item_above_min.id,
                    transaction_type="in",
                    delta_qty=Decimal("4.000"),
                ),
            ]
        )
        db.session.commit()

        return {
            "username": manager.username,
            "branch_two_id": branch_two.id,
            "branch_three_id": branch_three.id,
            "item_no_tx_id": item_no_tx.id,
            "item_low_id": item_low.id,
            "item_above_min_id": item_above_min.id,
            "item_inactive_id": item_inactive.id,
        }


def _auth_header(token, branch_id=None):
    headers = {"Authorization": f"Bearer {token}"}
    if branch_id is not None:
        headers["X-Branch-Id"] = str(branch_id)
    return headers


def test_low_stock_report_requires_valid_branch_scope(client, app):
    data = _seed_manager_and_inventory(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]

    branch_required_resp = client.get(
        "/api/reports/low-stock",
        headers=_auth_header(token),
    )
    assert branch_required_resp.status_code == 400
    assert branch_required_resp.get_json()["error"] == "branch_required"

    forbidden_branch_resp = client.get(
        "/api/reports/low-stock",
        headers=_auth_header(token, data["branch_three_id"]),
    )
    assert forbidden_branch_resp.status_code == 403
    assert forbidden_branch_resp.get_json()["error"] == "forbidden_branch"


def test_low_stock_report_includes_no_tx_and_excludes_above_min(client, app):
    data = _seed_manager_and_inventory(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]

    resp = client.get(
        "/api/reports/low-stock",
        headers=_auth_header(token, data["branch_two_id"]),
    )
    assert resp.status_code == 200

    items = resp.get_json()["items"]
    by_id = {item["id"]: item for item in items}

    assert data["item_no_tx_id"] in by_id
    assert by_id[data["item_no_tx_id"]]["current_stock"] == 0.0
    assert by_id[data["item_no_tx_id"]]["min_stock"] == 5.0
    assert by_id[data["item_no_tx_id"]]["deficit"] == 5.0

    assert data["item_low_id"] in by_id
    assert by_id[data["item_low_id"]]["current_stock"] == 3.0
    assert by_id[data["item_low_id"]]["deficit"] == 7.0

    assert data["item_above_min_id"] not in by_id
    assert data["item_inactive_id"] not in by_id

    assert [item["id"] for item in items] == [data["item_low_id"], data["item_no_tx_id"]]
