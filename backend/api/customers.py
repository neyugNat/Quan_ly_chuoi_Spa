# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false, reportUntypedFunctionDecorator=false

import json

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from backend.api import api_bp
from backend.decorators.rbac import require_roles
from backend.extensions import db
from backend.models.audit_log import AuditLog
from backend.models.customer import Customer
from backend.utils.scoping import get_current_branch_id


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


def _coerce_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off", ""}:
            return False
    return bool(value)


def _extract_tags(raw_tags):
    if raw_tags is None:
        return []

    if isinstance(raw_tags, (list, tuple, set)):
        values = list(raw_tags)
    else:
        text = str(raw_tags).strip()
        if not text:
            return []

        values = None
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                values = parsed
            elif isinstance(parsed, str):
                values = [parsed]
        except (TypeError, ValueError):
            pass

        if values is None:
            if "," in text:
                values = text.split(",")
            else:
                values = [text]

    tags = []
    seen = set()
    for value in values:
        tag = str(value).strip()
        if not tag:
            continue
        key = tag.lower()
        if key in seen:
            continue
        seen.add(key)
        tags.append(tag)
    return tags


def _serialize_tags(tags):
    if not tags:
        return None
    return json.dumps(sorted(tags, key=str.lower), ensure_ascii=True, separators=(",", ":"))


def _coerce_tags_json(raw_tags):
    tags = _extract_tags(raw_tags)
    return _serialize_tags(tags)


def _has_tag(raw_tags, wanted_tag):
    wanted = wanted_tag.strip().lower()
    if not wanted:
        return True
    return any(tag.lower() == wanted for tag in _extract_tags(raw_tags))


def _merge_tags_json(target_tags_json, source_tags_json):
    merged_by_key = {}
    for tag in _extract_tags(target_tags_json):
        merged_by_key.setdefault(tag.lower(), tag)
    for tag in _extract_tags(source_tags_json):
        merged_by_key.setdefault(tag.lower(), tag)
    return _serialize_tags(list(merged_by_key.values()))


@api_bp.get("/customers")
@jwt_required()
@require_roles("super_admin", "branch_manager", "reception", "cashier")
def list_customers():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    q = (request.args.get("q") or "").strip()
    tag = (request.args.get("tag") or "").strip()
    query = Customer.query.filter(Customer.branch_id == branch_id)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Customer.full_name.ilike(like))
            | (Customer.phone.ilike(like))
            | (Customer.email.ilike(like))
        )
    items = query.order_by(Customer.id.desc()).all()
    if tag:
        items = [customer for customer in items if _has_tag(customer.tags_json, tag)]
    items = items[:200]
    return jsonify({"items": [c.to_dict() for c in items]})


@api_bp.post("/customers")
@jwt_required()
@require_roles("super_admin", "branch_manager", "reception", "cashier")
def create_customer():
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    payload = request.get_json(silent=True) or {}
    full_name = (payload.get("full_name") or "").strip()
    phone = (payload.get("phone") or "").strip()
    if not full_name or not phone:
        return jsonify({"error": "missing_fields"}), 400

    customer = Customer(
        branch_id=branch_id,
        full_name=full_name,
        phone=phone,
        email=(payload.get("email") or "").strip() or None,
        dob=(payload.get("dob") or "").strip() or None,
        gender=(payload.get("gender") or "").strip() or None,
        address=(payload.get("address") or "").strip() or None,
        tags_json=_coerce_tags_json(payload.get("tags_json")),
        allergy_note=(payload.get("allergy_note") or None),
        marketing_consent=_coerce_bool(payload.get("marketing_consent"), default=False),
        note=(payload.get("note") or None),
        status=(payload.get("status") or "active"),
    )
    db.session.add(customer)
    db.session.flush()

    user_id = int(get_jwt_identity())
    _audit(user_id, branch_id, "customer.create", entity="Customer", after=customer.to_dict())
    db.session.commit()
    return jsonify(customer.to_dict()), 201


@api_bp.get("/customers/<int:customer_id>")
@jwt_required()
@require_roles("super_admin", "branch_manager", "reception", "cashier")
def get_customer(customer_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    customer = Customer.query.filter_by(id=customer_id, branch_id=branch_id).first()
    if not customer:
        return jsonify({"error": "not_found"}), 404
    return jsonify(customer.to_dict())


@api_bp.put("/customers/<int:customer_id>")
@jwt_required()
@require_roles("super_admin", "branch_manager", "reception", "cashier")
def update_customer(customer_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    customer = Customer.query.filter_by(id=customer_id, branch_id=branch_id).first()
    if not customer:
        return jsonify({"error": "not_found"}), 404

    before = customer.to_dict()
    payload = request.get_json(silent=True) or {}

    for key in [
        "full_name",
        "phone",
        "email",
        "dob",
        "gender",
        "address",
        "tags_json",
        "allergy_note",
        "note",
        "status",
    ]:
        if key in payload:
            val = payload.get(key)
            if key == "tags_json":
                val = _coerce_tags_json(val)
            elif isinstance(val, str):
                val = val.strip()
            setattr(customer, key, val or None)
    if "marketing_consent" in payload:
        customer.marketing_consent = _coerce_bool(payload.get("marketing_consent"), default=False)

    user_id = int(get_jwt_identity())
    _audit(user_id, branch_id, "customer.update", entity="Customer", before=before, after=customer.to_dict())
    db.session.commit()
    return jsonify(customer.to_dict())


@api_bp.post("/customers/<int:customer_id>/merge")
@jwt_required()
@require_roles("super_admin", "branch_manager", "reception", "cashier")
def merge_customer(customer_id: int):
    branch_id, err, status = get_current_branch_id()
    if err:
        return jsonify(err), status

    payload = request.get_json(silent=True) or {}
    source_customer_id = payload.get("source_customer_id")
    if source_customer_id is None:
        return jsonify({"error": "missing_source_customer_id"}), 400

    try:
        source_customer_id = int(source_customer_id)
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_source_customer_id"}), 400

    if source_customer_id == customer_id:
        return jsonify({"error": "cannot_merge_same_customer"}), 400

    target = Customer.query.filter_by(id=customer_id).first()
    if not target:
        return jsonify({"error": "not_found"}), 404
    if target.branch_id != branch_id:
        return jsonify({"error": "forbidden_branch"}), 403

    source = Customer.query.filter_by(id=source_customer_id).first()
    if not source:
        return jsonify({"error": "not_found"}), 404
    if source.branch_id != branch_id:
        return jsonify({"error": "forbidden_branch"}), 403

    before = {
        "target": target.to_dict(),
        "source": source.to_dict(),
    }

    for field_name in ["email", "address", "dob", "gender"]:
        if not getattr(target, field_name) and getattr(source, field_name):
            setattr(target, field_name, getattr(source, field_name))

    target.tags_json = _merge_tags_json(target.tags_json, source.tags_json)
    source.status = "merged"

    after = {
        "target": target.to_dict(),
        "source": source.to_dict(),
    }
    user_id = int(get_jwt_identity())
    _audit(user_id, branch_id, "customer.merge", entity="Customer", before=before, after=after)
    db.session.commit()
    return jsonify(after)
