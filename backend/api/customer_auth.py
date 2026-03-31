# pyright: reportMissingImports=false, reportUnknownMemberType=false

from datetime import datetime, timedelta
import secrets
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from flask import current_app, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from sqlalchemy import func

from backend.api import api_bp
from backend.extensions import db
from backend.models.branch import Branch
from backend.models.customer import Customer
from backend.models.customer_account import CustomerAccount
from backend.utils.mailer import send_mail


CUSTOMER_IDENTITY_PREFIX = "customer:"


def _normalize_email(raw_value):
    return (raw_value or "").strip().lower()


def _is_password_valid(raw_password):
    return len(raw_password or "") >= 6


def _build_customer_claims(account: CustomerAccount):
    branch_id = account.customer.branch_id if account.customer else None
    return {
        "actor_type": "customer",
        "customer_id": account.customer_id,
        "branch_id": branch_id,
    }


def _resolve_branch(branch_id_raw):
    if branch_id_raw is not None and str(branch_id_raw).strip() != "":
        try:
            branch_id = int(branch_id_raw)
        except (TypeError, ValueError):
            return None
        branch = Branch.query.filter_by(id=branch_id).first()
        if branch:
            return branch
    return Branch.query.order_by(Branch.id.asc()).first()


def _build_fallback_phone():
    timestamp = datetime.utcnow().strftime("%y%m%d%H%M%S")
    suffix = secrets.randbelow(1000)
    return f"guest-{timestamp}-{suffix:03d}"[:32]


def _build_reset_url(token: str):
    base = (current_app.config.get("CUSTOMER_RESET_URL_BASE") or "").strip()
    if not base:
        return token

    parsed = urlparse(base)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["token"] = token
    query["mode"] = "customer"
    query["view"] = "reset"
    return urlunparse(parsed._replace(query=urlencode(query)))


def _find_account_by_email(email: str):
    return CustomerAccount.query.filter(func.lower(CustomerAccount.email) == email).first()


def _find_customer_by_email(email: str):
    return Customer.query.filter(func.lower(Customer.email) == email).order_by(Customer.id.asc()).first()


def _customer_identity(account: CustomerAccount):
    return f"{CUSTOMER_IDENTITY_PREFIX}{account.id}"


def _get_customer_account_from_jwt():
    identity = str(get_jwt_identity() or "")
    if not identity.startswith(CUSTOMER_IDENTITY_PREFIX):
        return None
    account_id_raw = identity[len(CUSTOMER_IDENTITY_PREFIX) :]
    if not account_id_raw.isdigit():
        return None
    return CustomerAccount.query.get(int(account_id_raw))


@api_bp.post("/customer-auth/register")
def customer_register():
    payload = request.get_json(silent=True) or {}
    email = _normalize_email(payload.get("email"))
    password = payload.get("password") or ""
    full_name = (payload.get("full_name") or "").strip()
    phone = (payload.get("phone") or "").strip()
    marketing_consent = bool(payload.get("marketing_consent", False))

    if not email or not password or not full_name:
        return jsonify({"error": "missing_fields"}), 400
    if not _is_password_valid(password):
        return jsonify({"error": "weak_password"}), 400

    if _find_account_by_email(email):
        return jsonify({"error": "email_exists"}), 409

    branch = _resolve_branch(payload.get("branch_id"))
    if branch is None:
        return jsonify({"error": "missing_branch"}), 400

    customer = _find_customer_by_email(email)
    if customer is None:
        customer = Customer(
            branch_id=branch.id,
            full_name=full_name,
            phone=phone or _build_fallback_phone(),
            email=email,
            status="active",
            marketing_consent=marketing_consent,
        )
        db.session.add(customer)
        db.session.flush()
    else:
        if not customer.full_name:
            customer.full_name = full_name
        if not customer.phone and phone:
            customer.phone = phone
        if not customer.email:
            customer.email = email
        if not customer.status:
            customer.status = "active"

    if CustomerAccount.query.filter_by(customer_id=customer.id).first():
        return jsonify({"error": "customer_account_exists"}), 409

    account = CustomerAccount(customer_id=customer.id, email=email, is_active=True)
    account.set_password(password)
    db.session.add(account)
    db.session.flush()

    access_token = create_access_token(
        identity=_customer_identity(account),
        additional_claims=_build_customer_claims(account),
    )

    try:
        send_mail(
            to_email=email,
            subject="Lotus Spa - Tai khoan khach hang da duoc tao",
            text_body=(
                f"Xin chao {customer.full_name},\n\n"
                "Tai khoan khach hang cua ban da duoc tao thanh cong.\n"
                "Ban co the dang nhap de dat lich tai Lotus Spa.\n\n"
                "Neu ban khong thuc hien thao tac nay, vui long lien he chi nhanh."
            ),
        )
    except Exception:
        current_app.logger.exception("customer register welcome mail failed")

    db.session.commit()
    return jsonify({"token": access_token, "account": account.to_dict()}), 201


@api_bp.post("/customer-auth/login")
def customer_login():
    payload = request.get_json(silent=True) or {}
    email = _normalize_email(payload.get("email"))
    password = payload.get("password") or ""

    if not email or not password:
        return jsonify({"error": "missing_credentials"}), 400

    account = _find_account_by_email(email)
    if not account or not account.is_active or not account.verify_password(password):
        return jsonify({"error": "invalid_credentials"}), 401

    if not account.customer or account.customer.status not in {"active", "vip", "new"}:
        return jsonify({"error": "customer_inactive"}), 401

    access_token = create_access_token(
        identity=_customer_identity(account),
        additional_claims=_build_customer_claims(account),
    )
    return jsonify({"token": access_token, "account": account.to_dict()})


@api_bp.get("/customer-auth/me")
@jwt_required()
def customer_me():
    account = _get_customer_account_from_jwt()
    if not account or not account.is_active:
        return jsonify({"error": "unauthorized"}), 401
    return jsonify(account.to_dict())


@api_bp.post("/customer-auth/forgot-password")
def customer_forgot_password():
    payload = request.get_json(silent=True) or {}
    email = _normalize_email(payload.get("email"))
    if not email:
        return jsonify({"error": "missing_email"}), 400

    account = _find_account_by_email(email)
    if not account or not account.is_active:
        return jsonify({"status": "ok"})

    token = secrets.token_urlsafe(32)
    account.reset_password_token = token
    account.reset_password_expires_at = datetime.utcnow() + timedelta(minutes=30)
    reset_url = _build_reset_url(token)

    try:
        send_mail(
            to_email=email,
            subject="Lotus Spa - Dat lai mat khau",
            text_body=(
                "Ban vua yeu cau dat lai mat khau.\n\n"
                f"Truy cap link sau de dat lai mat khau (hieu luc 30 phut):\n{reset_url}\n\n"
                "Neu ban khong yeu cau, co the bo qua email nay."
            ),
        )
    except Exception:
        db.session.rollback()
        current_app.logger.exception("customer forgot-password mail failed")
        return jsonify({"error": "mail_send_failed"}), 500

    db.session.commit()

    response = {"status": "ok"}
    if current_app.config.get("TESTING") or (current_app.config.get("MAIL_MODE") == "console"):
        response["reset_token"] = token
        response["reset_url"] = reset_url
    return jsonify(response)


@api_bp.post("/customer-auth/reset-password")
def customer_reset_password():
    payload = request.get_json(silent=True) or {}
    token = (payload.get("token") or "").strip()
    new_password = payload.get("new_password") or ""

    if not token or not new_password:
        return jsonify({"error": "missing_fields"}), 400
    if not _is_password_valid(new_password):
        return jsonify({"error": "weak_password"}), 400

    account = CustomerAccount.query.filter_by(reset_password_token=token).first()
    if not account:
        return jsonify({"error": "invalid_token"}), 400

    expires_at = account.reset_password_expires_at
    if not expires_at or expires_at < datetime.utcnow():
        account.reset_password_token = None
        account.reset_password_expires_at = None
        db.session.commit()
        return jsonify({"error": "expired_token"}), 400
    if not account.is_active:
        return jsonify({"error": "account_inactive"}), 400

    account.set_password(new_password)
    account.reset_password_token = None
    account.reset_password_expires_at = None
    db.session.commit()
    return jsonify({"status": "ok"})
