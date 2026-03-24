# pyright: reportMissingImports=false

from datetime import datetime, timedelta
from decimal import Decimal
import secrets

from flask import jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from backend.api import api_bp
from backend.decorators.rbac import require_roles
from backend.extensions import db
from backend.models.audit_log import AuditLog
from backend.models.user import Role, User


def _audit(user_id, branch_id, action, entity=None, before=None, after=None):
    log = AuditLog(
        user_id=user_id,
        branch_id=branch_id,
        action=action,
        entity=entity,
        before_json=AuditLog.dumps(before),
        after_json=AuditLog.dumps(after),
    )
    db.session.add(log)


@api_bp.post("/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    if not username or not password:
        return jsonify({"error": "missing_credentials"}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.is_active or not user.verify_password(password):
        return jsonify({"error": "invalid_credentials"}), 401

    claims = {
        "roles": user.role_names(),
        "branch_ids": user.branch_ids(),
    }
    access_token = create_access_token(identity=str(user.id), additional_claims=claims)
    _audit(user_id=user.id, branch_id=None, action="auth.login", entity="User")
    db.session.commit()

    return jsonify({"token": access_token, "user": user.to_dict()})


@api_bp.get("/auth/me")
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user or not user.is_active:
        return jsonify({"error": "unauthorized"}), 401
    return jsonify(user.to_dict())


@api_bp.post("/auth/change-password")
@jwt_required()
def change_password():
    user_id = int(get_jwt_identity())
    payload = request.get_json(silent=True) or {}
    old_password = payload.get("old_password") or ""
    new_password = payload.get("new_password") or ""
    if not old_password or not new_password:
        return jsonify({"error": "missing_fields"}), 400

    user = User.query.get(user_id)
    if not user or not user.is_active:
        return jsonify({"error": "unauthorized"}), 401
    if not user.verify_password(old_password):
        return jsonify({"error": "invalid_old_password"}), 400

    user.set_password(new_password)
    _audit(user_id=user.id, branch_id=None, action="auth.change_password", entity="User")
    db.session.commit()
    return jsonify({"status": "ok"})


@api_bp.post("/auth/forgot-password")
def forgot_password():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    if not username:
        return jsonify({"error": "missing_username"}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.is_active:
        return jsonify({"error": "not_found_or_inactive"}), 404

    token = secrets.token_urlsafe(32)
    user.reset_password_token = token
    user.reset_password_expires_at = datetime.utcnow() + timedelta(minutes=15)
    _audit(user_id=user.id, branch_id=None, action="auth.forgot_password", entity="User")
    db.session.commit()
    return jsonify({"status": "ok", "reset_token": token})


@api_bp.post("/auth/reset-password")
def reset_password():
    payload = request.get_json(silent=True) or {}
    token = (payload.get("token") or "").strip()
    new_password = payload.get("new_password") or ""
    if not token or not new_password:
        return jsonify({"error": "missing_fields"}), 400

    user = User.query.filter_by(reset_password_token=token).first()
    if not user:
        return jsonify({"error": "invalid_token"}), 400

    expires_at = user.reset_password_expires_at
    if not expires_at or expires_at < datetime.utcnow():
        user.reset_password_token = None
        user.reset_password_expires_at = None
        db.session.commit()
        return jsonify({"error": "expired_token"}), 400
    if not user.is_active:
        return jsonify({"error": "account_inactive"}), 400

    user.set_password(new_password)
    user.reset_password_token = None
    user.reset_password_expires_at = None
    _audit(user_id=user.id, branch_id=None, action="auth.reset_password", entity="User")
    db.session.commit()
    return jsonify({"status": "ok"})


@api_bp.post("/auth/lock-user")
@jwt_required()
@require_roles("super_admin")
def lock_user():
    payload = request.get_json(silent=True) or {}
    target_user_id = payload.get("user_id")
    if target_user_id is None:
        return jsonify({"error": "missing_user_id"}), 400

    user = User.query.get(target_user_id)
    if not user:
        return jsonify({"error": "not_found"}), 404

    user.is_active = False
    actor_user_id = int(get_jwt_identity())
    _audit(
        user_id=actor_user_id,
        branch_id=None,
        action="auth.lock_user",
        entity="User",
        before={"target_user_id": user.id, "is_active": True},
        after={"target_user_id": user.id, "is_active": False},
    )
    db.session.commit()
    return jsonify({"status": "ok", "user": user.to_dict()})


@api_bp.post("/auth/unlock-user")
@jwt_required()
@require_roles("super_admin")
def unlock_user():
    payload = request.get_json(silent=True) or {}
    target_user_id = payload.get("user_id")
    if target_user_id is None:
        return jsonify({"error": "missing_user_id"}), 400

    user = User.query.get(target_user_id)
    if not user:
        return jsonify({"error": "not_found"}), 404

    user.is_active = True
    actor_user_id = int(get_jwt_identity())
    _audit(
        user_id=actor_user_id,
        branch_id=None,
        action="auth.unlock_user",
        entity="User",
        before={"target_user_id": user.id, "is_active": False},
        after={"target_user_id": user.id, "is_active": True},
    )
    db.session.commit()
    return jsonify({"status": "ok", "user": user.to_dict()})


def ensure_basic_seed():
    # Idempotent seed: roles + an admin user + a default branch.
    from backend.models.branch import Branch

    if not Branch.query.first():
        b = Branch(name="Chi nhanh 1", address="Demo", status="active")
        db.session.add(b)
        db.session.flush()

    for role_name in ["super_admin", "branch_manager", "reception", "technician", "cashier", "warehouse"]:
        if not Role.query.filter_by(name=role_name).first():
            db.session.add(Role(name=role_name))
    db.session.flush()

    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", is_active=True)
        admin.set_password("admin123")
        admin.roles = [Role.query.filter_by(name="super_admin").first()]
        admin.branches = list(Branch.query.all())
        db.session.add(admin)
    db.session.commit()


def _ensure_user(*, username, password, role_names, branches):
    role_by_name = {role.name: role for role in Role.query.filter(Role.name.in_(role_names)).all()}
    user = User.query.filter_by(username=username).first()
    if user is None:
        user = User(username=username, is_active=True)
        db.session.add(user)
    user.is_active = True
    user.set_password(password)
    user.roles = [role_by_name[role_name] for role_name in role_names]
    user.branches = list(branches)
    return user


def ensure_demo_seed():
    from backend.models.appointment import Appointment
    from backend.models.branch import Branch
    from backend.models.customer import Customer
    from backend.models.inventory_item import InventoryItem
    from backend.models.service import Service
    from backend.models.staff import Staff
    from backend.models.stock_transaction import StockTransaction

    ensure_basic_seed()

    branch_definitions = [
        ("Chi nhanh 1", "Demo"),
        ("Chi nhanh 2", "Demo 2"),
    ]
    branches = []
    for name, address in branch_definitions:
        branch = Branch.query.filter_by(name=name).first()
        if branch is None:
            branch = Branch(name=name, address=address, status="active")
            db.session.add(branch)
            db.session.flush()
        if branch.status != "active":
            branch.status = "active"
        if not branch.address:
            branch.address = address
        branches.append(branch)

    branch_by_name = {branch.name: branch for branch in branches}

    user_definitions = [
        {
            "username": "admin",
            "password": "admin123",
            "role_names": ["super_admin"],
            "branch_names": [branch.name for branch in branches],
        },
        {
            "username": "manager_b1",
            "password": "manager123",
            "role_names": ["branch_manager"],
            "branch_names": ["Chi nhanh 1"],
        },
        {
            "username": "reception_b1",
            "password": "reception123",
            "role_names": ["reception"],
            "branch_names": ["Chi nhanh 1"],
        },
        {
            "username": "technician_b2",
            "password": "technician123",
            "role_names": ["technician"],
            "branch_names": ["Chi nhanh 2"],
        },
        {
            "username": "cashier_b1",
            "password": "cashier123",
            "role_names": ["cashier"],
            "branch_names": ["Chi nhanh 1"],
        },
        {
            "username": "warehouse_b2",
            "password": "warehouse123",
            "role_names": ["warehouse"],
            "branch_names": ["Chi nhanh 2"],
        },
    ]
    for user_definition in user_definitions:
        scoped_branches = [branch_by_name[name] for name in user_definition["branch_names"] if name in branch_by_name]
        _ensure_user(
            username=user_definition["username"],
            password=user_definition["password"],
            role_names=user_definition["role_names"],
            branches=scoped_branches,
        )

    db.session.flush()

    service_templates = [
        ("Massage Co Ban", Decimal("250000"), 60),
        ("Cham Soc Da Mat", Decimal("320000"), 75),
        ("Goi Dau Duong Sinh", Decimal("180000"), 45),
        ("Tri Lieu Co Vai Gay", Decimal("420000"), 90),
    ]
    services_by_branch = {}
    for branch in branches:
        branch_services = []
        for service_name, price, duration in service_templates:
            service = Service.query.filter_by(branch_id=branch.id, name=service_name).first()
            if service is None:
                service = Service(
                    branch_id=branch.id,
                    name=service_name,
                    price=price,
                    duration_minutes=duration,
                    status="active",
                )
                db.session.add(service)
            else:
                service.price = price
                service.duration_minutes = duration
                service.status = "active"
            branch_services.append(service)
        services_by_branch[branch.id] = branch_services

    customer_templates = [
        ("Nguyen Van A", "male"),
        ("Tran Thi B", "female"),
        ("Le Van C", "male"),
        ("Pham Thi D", "female"),
        ("Hoang Van E", "male"),
        ("Do Thi F", "female"),
    ]
    customers_by_branch = {}
    for branch in branches:
        branch_customers = []
        for index, (full_name, gender) in enumerate(customer_templates, start=1):
            phone = f"090{branch.id:02d}{index:04d}"
            customer = Customer.query.filter_by(branch_id=branch.id, phone=phone).first()
            if customer is None:
                customer = Customer(
                    branch_id=branch.id,
                    full_name=full_name,
                    phone=phone,
                    email=f"kh{branch.id}{index}@demo.local",
                    gender=gender,
                    address=f"Dia chi mau {branch.id}-{index}",
                    marketing_consent=bool(index % 2),
                    status="active",
                )
                db.session.add(customer)
            else:
                customer.full_name = full_name
                customer.gender = gender
                customer.status = "active"
            branch_customers.append(customer)
        customers_by_branch[branch.id] = branch_customers

    staff_templates = [
        ("Ky thuat vien 1", "technician", "senior"),
        ("Ky thuat vien 2", "technician", "middle"),
        ("Le tan", "reception", "middle"),
        ("Thu ngan", "cashier", "middle"),
    ]
    staff_by_branch = {}
    for branch in branches:
        branch_staff = []
        for index, (full_name, role, skill_level) in enumerate(staff_templates, start=1):
            phone = f"091{branch.id:02d}{index:04d}"
            staff = Staff.query.filter_by(branch_id=branch.id, phone=phone).first()
            if staff is None:
                staff = Staff(
                    branch_id=branch.id,
                    full_name=full_name,
                    phone=phone,
                    title="Nhan vien",
                    role=role,
                    skill_level=skill_level,
                    status="active",
                )
                db.session.add(staff)
            else:
                staff.full_name = full_name
                staff.role = role
                staff.skill_level = skill_level
                staff.status = "active"
            branch_staff.append(staff)
        staff_by_branch[branch.id] = branch_staff

    demo_user_links = [
        ("technician_b2", "Chi nhanh 2", "technician"),
        ("reception_b1", "Chi nhanh 1", "reception"),
        ("cashier_b1", "Chi nhanh 1", "cashier"),
    ]
    for username, branch_name, staff_role in demo_user_links:
        user = User.query.filter_by(username=username).first()
        branch = branch_by_name.get(branch_name)
        if user is None or branch is None:
            continue
        staff = (
            Staff.query.filter_by(branch_id=branch.id, role=staff_role)
            .order_by(Staff.id.asc())
            .first()
        )
        if staff is not None and staff.user_id != user.id:
            staff.user_id = user.id

    inventory_templates = [
        ("Tinh Dau", "chai", Decimal("12"), Decimal("10"), Decimal("2")),
        ("Khau Trang", "hop", Decimal("20"), Decimal("30"), Decimal("4")),
        ("Kem Duong", "tuyp", Decimal("8"), Decimal("20"), Decimal("6")),
        ("Gang Tay", "hop", Decimal("15"), Decimal("18"), Decimal("5")),
        ("Khan Uot", "goi", Decimal("25"), Decimal("28"), Decimal("7")),
    ]
    inventory_by_branch = {}
    for branch in branches:
        branch_items = []
        for index, (name, unit, min_stock, qty_in, qty_out) in enumerate(inventory_templates, start=1):
            sku = f"SEED-B{branch.id:02d}-ITM{index:02d}"
            item = InventoryItem.query.filter_by(branch_id=branch.id, sku=sku).first()
            if item is None:
                item = InventoryItem(
                    branch_id=branch.id,
                    name=name,
                    sku=sku,
                    unit=unit,
                    min_stock=min_stock,
                    expiry_tracking=False,
                    status="active",
                )
                db.session.add(item)
                db.session.flush()
            else:
                item.name = name
                item.unit = unit
                item.min_stock = min_stock
                item.status = "active"

            in_source_id = 1000 + (branch.id * 100) + index
            in_tx = StockTransaction.query.filter_by(
                branch_id=branch.id,
                inventory_item_id=item.id,
                source_type="seed_demo",
                source_id=in_source_id,
                transaction_type="in",
            ).first()
            if in_tx is None:
                db.session.add(
                    StockTransaction(
                        branch_id=branch.id,
                        inventory_item_id=item.id,
                        transaction_type="in",
                        delta_qty=qty_in,
                        source_type="seed_demo",
                        source_id=in_source_id,
                        note="seed in",
                    )
                )

            out_source_id = 2000 + (branch.id * 100) + index
            out_tx = StockTransaction.query.filter_by(
                branch_id=branch.id,
                inventory_item_id=item.id,
                source_type="seed_demo",
                source_id=out_source_id,
                transaction_type="out",
            ).first()
            if out_tx is None:
                db.session.add(
                    StockTransaction(
                        branch_id=branch.id,
                        inventory_item_id=item.id,
                        transaction_type="out",
                        delta_qty=-qty_out,
                        source_type="seed_demo",
                        source_id=out_source_id,
                        note="seed out",
                    )
                )

            branch_items.append(item)
        inventory_by_branch[branch.id] = branch_items

    db.session.flush()

    appointment_statuses = [
        "booked",
        "confirmed",
        "arrived",
        "in_service",
        "completed",
        "paid",
        "cancelled",
        "no_show",
    ]
    base_time = datetime(2026, 1, 15, 9, 0, 0)
    for branch in branches:
        branch_customers = customers_by_branch[branch.id]
        branch_services = services_by_branch[branch.id]
        branch_staff = staff_by_branch[branch.id]

        for index, status in enumerate(appointment_statuses, start=1):
            start_time = base_time + timedelta(days=index % 3, minutes=(index - 1) * 70)
            end_time = start_time + timedelta(minutes=60)
            marker = f"seed-appt-b{branch.id}-n{index}"
            appointment = Appointment.query.filter_by(branch_id=branch.id, note=marker).first()
            if appointment is None:
                appointment = Appointment(
                    branch_id=branch.id,
                    customer_id=branch_customers[(index - 1) % len(branch_customers)].id,
                    service_id=branch_services[(index - 1) % len(branch_services)].id,
                    staff_id=branch_staff[(index - 1) % len(branch_staff)].id,
                    start_time=start_time,
                    end_time=end_time,
                    status=status,
                    note=marker,
                )
                db.session.add(appointment)
            else:
                appointment.customer_id = branch_customers[(index - 1) % len(branch_customers)].id
                appointment.service_id = branch_services[(index - 1) % len(branch_services)].id
                appointment.staff_id = branch_staff[(index - 1) % len(branch_staff)].id
                appointment.start_time = start_time
                appointment.end_time = end_time
                appointment.status = status

    db.session.commit()
