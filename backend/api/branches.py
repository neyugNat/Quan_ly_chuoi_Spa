from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from backend.api import api_bp
from backend.decorators.rbac import require_roles
from backend.extensions import db
from backend.models.branch import Branch


def _normalize_status(value):
    if value is None:
        return None
    status = (value or "").strip()
    if status not in {"active", "inactive"}:
        return None
    return status


@api_bp.get("/branches")
@jwt_required()
@require_roles("super_admin")
def list_branches():
    items = Branch.query.order_by(Branch.id.desc()).all()
    return jsonify({"items": [item.to_dict() for item in items]})


@api_bp.post("/branches")
@jwt_required()
@require_roles("super_admin")
def create_branch():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    if not name:
        return jsonify({"error": "missing_fields"}), 400

    status = _normalize_status(payload.get("status"))
    if payload.get("status") is not None and status is None:
        return jsonify({"error": "invalid_status"}), 400

    branch = Branch(
        name=name,
        address=(payload.get("address") or "").strip() or None,
        status=status or "active",
        working_hours_json=payload.get("working_hours_json"),
    )
    db.session.add(branch)
    db.session.commit()
    return jsonify(branch.to_dict()), 201


@api_bp.get("/branches/<int:branch_id>")
@jwt_required()
@require_roles("super_admin")
def get_branch(branch_id: int):
    branch = Branch.query.get(branch_id)
    if not branch:
        return jsonify({"error": "not_found"}), 404
    return jsonify(branch.to_dict())


@api_bp.put("/branches/<int:branch_id>")
@jwt_required()
@require_roles("super_admin")
def update_branch(branch_id: int):
    branch = Branch.query.get(branch_id)
    if not branch:
        return jsonify({"error": "not_found"}), 404

    payload = request.get_json(silent=True) or {}

    if "name" in payload:
        name = (payload.get("name") or "").strip()
        if not name:
            return jsonify({"error": "missing_fields"}), 400
        branch.name = name

    if "address" in payload:
        address = payload.get("address")
        if isinstance(address, str):
            address = address.strip()
        branch.address = address or None

    if "status" in payload:
        status = _normalize_status(payload.get("status"))
        if status is None:
            return jsonify({"error": "invalid_status"}), 400
        branch.status = status

    if "working_hours_json" in payload:
        branch.working_hours_json = payload.get("working_hours_json")

    db.session.commit()
    return jsonify(branch.to_dict())


@api_bp.delete("/branches/<int:branch_id>")
@jwt_required()
@require_roles("super_admin")
def delete_branch(branch_id: int):
    from backend.models.appointment import Appointment
    from backend.models.commission_record import CommissionRecord
    from backend.models.customer import Customer
    from backend.models.customer_package import CustomerPackage
    from backend.models.inventory_item import InventoryItem
    from backend.models.invoice import Invoice
    from backend.models.package import Package
    from backend.models.payment import Payment
    from backend.models.resource import Resource
    from backend.models.service import Service
    from backend.models.shift import Shift
    from backend.models.staff import Staff
    from backend.models.stock_transaction import StockTransaction
    from backend.models.user import User, UserBranch

    branch = Branch.query.get(branch_id)
    if not branch:
        return jsonify({"error": "not_found"}), 404

    payload = request.get_json(silent=True) or {}
    password = payload.get("password") or ""
    if not password:
        return jsonify({"error": "missing_fields"}), 400

    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user or not user.verify_password(password):
        return jsonify({"error": "invalid_password"}), 400

    if Branch.query.count() <= 1:
        return jsonify({"error": "cannot_delete_last_branch"}), 400

    usage_counts = {
        "appointments": Appointment.query.filter_by(branch_id=branch_id).count(),
        "customers": Customer.query.filter_by(branch_id=branch_id).count(),
        "staffs": Staff.query.filter_by(branch_id=branch_id).count(),
        "services": Service.query.filter_by(branch_id=branch_id).count(),
        "packages": Package.query.filter_by(branch_id=branch_id).count(),
        "invoices": Invoice.query.filter_by(branch_id=branch_id).count(),
        "payments": Payment.query.filter_by(branch_id=branch_id).count(),
        "shifts": Shift.query.filter_by(branch_id=branch_id).count(),
        "customer_packages": CustomerPackage.query.filter_by(branch_id=branch_id).count(),
        "commission_records": CommissionRecord.query.filter_by(branch_id=branch_id).count(),
        "inventory_items": InventoryItem.query.filter_by(branch_id=branch_id).count(),
        "resources": Resource.query.filter_by(branch_id=branch_id).count(),
        "stock_transactions": StockTransaction.query.filter_by(branch_id=branch_id).count(),
    }
    in_use_details = {key: value for key, value in usage_counts.items() if value > 0}
    if in_use_details:
        return jsonify({"error": "branch_in_use", "details": in_use_details}), 400

    UserBranch.query.filter_by(branch_id=branch_id).delete()
    db.session.delete(branch)
    db.session.commit()
    return jsonify({"status": "ok"})
