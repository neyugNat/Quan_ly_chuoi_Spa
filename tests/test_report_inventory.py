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


def _auth_header(token, branch_id=None):
    headers = {"Authorization": f"Bearer {token}"}
    if branch_id is not None:
        headers["X-Branch-Id"] = str(branch_id)
    return headers


def _seed_inventory_report_data(app):
    with app.app_context():
        branch_one = Branch.query.first()
        assert branch_one is not None

        branch_two = Branch(name="Chi nhanh 2", address="Demo 2", status="active")
        branch_three = Branch(name="Chi nhanh 3", address="Demo 3", status="active")
        db.session.add_all([branch_two, branch_three])
        db.session.commit()

        manager = _create_user(
            "inventory_manager",
            "pass-123",
            "branch_manager",
            [branch_one, branch_two],
        )

        item_body_oil = InventoryItem(
            branch_id=branch_two.id,
            name="Body Oil",
            sku="BO-001",
            unit="chai",
            min_stock=Decimal("3.000"),
            expiry_tracking=False,
            status="active",
        )
        item_aloe_gel = InventoryItem(
            branch_id=branch_two.id,
            name="Aloe Gel",
            sku="AG-001",
            unit="hop",
            min_stock=Decimal("1.000"),
            expiry_tracking=False,
            status="active",
        )
        item_cream_base = InventoryItem(
            branch_id=branch_two.id,
            name="Cream Base",
            sku="CB-001",
            unit="goi",
            min_stock=Decimal("10.000"),
            expiry_tracking=False,
            status="active",
        )
        item_inactive = InventoryItem(
            branch_id=branch_two.id,
            name="Inactive Item",
            sku="IN-001",
            unit="goi",
            min_stock=Decimal("2.000"),
            expiry_tracking=False,
            status="inactive",
        )
        db.session.add_all([item_body_oil, item_aloe_gel, item_cream_base, item_inactive])
        db.session.flush()

        db.session.add_all(
            [
                StockTransaction(
                    branch_id=branch_two.id,
                    inventory_item_id=item_body_oil.id,
                    transaction_type="in",
                    delta_qty=Decimal("6.000"),
                ),
                StockTransaction(
                    branch_id=branch_two.id,
                    inventory_item_id=item_body_oil.id,
                    transaction_type="out",
                    delta_qty=Decimal("-2.000"),
                ),
                StockTransaction(
                    branch_id=branch_two.id,
                    inventory_item_id=item_cream_base.id,
                    transaction_type="in",
                    delta_qty=Decimal("2.000"),
                ),
                StockTransaction(
                    branch_id=branch_two.id,
                    inventory_item_id=item_cream_base.id,
                    transaction_type="out",
                    delta_qty=Decimal("-5.000"),
                ),
                StockTransaction(
                    branch_id=branch_three.id,
                    inventory_item_id=item_body_oil.id,
                    transaction_type="in",
                    delta_qty=Decimal("100.000"),
                ),
            ]
        )
        db.session.commit()

        return {
            "username": manager.username,
            "branch_two_id": branch_two.id,
            "branch_three_id": branch_three.id,
            "item_body_oil_id": item_body_oil.id,
            "item_aloe_gel_id": item_aloe_gel.id,
            "item_cream_base_id": item_cream_base.id,
            "item_inactive_id": item_inactive.id,
        }


def test_inventory_report_requires_valid_branch_scope(client, app):
    data = _seed_inventory_report_data(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]

    branch_required_resp = client.get(
        "/api/reports/inventory",
        headers=_auth_header(token),
    )
    assert branch_required_resp.status_code == 400
    assert branch_required_resp.get_json()["error"] == "branch_required"

    forbidden_branch_resp = client.get(
        "/api/reports/inventory",
        headers=_auth_header(token, data["branch_three_id"]),
    )
    assert forbidden_branch_resp.status_code == 403
    assert forbidden_branch_resp.get_json()["error"] == "forbidden_branch"


def test_inventory_report_computes_stock_totals_and_low_stock_flags(client, app):
    data = _seed_inventory_report_data(app)
    token = _login(client, data["username"], "pass-123").get_json()["token"]

    resp = client.get(
        "/api/reports/inventory",
        headers=_auth_header(token, data["branch_two_id"]),
    )
    assert resp.status_code == 200

    items = resp.get_json()["items"]
    by_id = {item["id"]: item for item in items}

    assert data["item_inactive_id"] not in by_id

    assert by_id[data["item_body_oil_id"]] == {
        "id": data["item_body_oil_id"],
        "name": "Body Oil",
        "sku": "BO-001",
        "unit": "chai",
        "min_stock": 3.0,
        "current_stock": 4.0,
        "total_in": 6.0,
        "total_out": 2.0,
        "low_stock": False,
    }
    assert by_id[data["item_aloe_gel_id"]] == {
        "id": data["item_aloe_gel_id"],
        "name": "Aloe Gel",
        "sku": "AG-001",
        "unit": "hop",
        "min_stock": 1.0,
        "current_stock": 0.0,
        "total_in": 0.0,
        "total_out": 0.0,
        "low_stock": True,
    }
    assert by_id[data["item_cream_base_id"]] == {
        "id": data["item_cream_base_id"],
        "name": "Cream Base",
        "sku": "CB-001",
        "unit": "goi",
        "min_stock": 10.0,
        "current_stock": -3.0,
        "total_in": 2.0,
        "total_out": 5.0,
        "low_stock": True,
    }

    assert [item["id"] for item in items] == [
        data["item_aloe_gel_id"],
        data["item_cream_base_id"],
        data["item_body_oil_id"],
    ]
