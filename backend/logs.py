from __future__ import annotations

import json
from typing import Any

from flask import current_app, g, has_request_context

from backend.extensions import db
from backend.models import ActivityLog


ACTION_LABELS = {
    "create_invoice": "Tạo hóa đơn",
    "add_invoice_payment": "Ghi nhận thanh toán",
    "refund_invoice": "Hoàn tiền hóa đơn",
    "cancel_invoice": "Hủy hóa đơn",
    "create_appointment": "Tạo lịch hẹn",
    "complete_appointment": "Hoàn thành lịch hẹn",
    "cancel_appointment": "Hủy lịch hẹn",
    "update_inventory_stock": "Sửa kho",
    "inventory_transaction": "Giao dịch kho",
    "transfer_inventory": "Chuyển kho",
    "save_staff": "Lưu nhân sự",
    "delete_staff": "Xóa nhân sự",
    "save_service": "Lưu dịch vụ",
    "delete_service": "Xóa dịch vụ",
    "create_account": "Tạo tài khoản",
    "change_own_password": "Đổi mật khẩu cá nhân",
    "change_branch_manager": "Đổi quản lý chi nhánh",
}


def _serialize_details(details: dict[str, Any] | None) -> str | None:
    if not details:
        return None
    try:
        return json.dumps(details, ensure_ascii=False, separators=(",", ":"))
    except TypeError:
        return str(details)


def write_log(
    action: str,
    *,
    branch_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    message: str | None = None,
    details: dict[str, Any] | None = None,
):
    """Queue one activity log row in the current SQLAlchemy session."""
    try:
        user = getattr(g, "web_user", None) if has_request_context() else None
        row = ActivityLog(
            action=action,
            action_label=ACTION_LABELS.get(action, action),
            branch_id=branch_id,
            actor_user_id=getattr(user, "id", None),
            actor_username=getattr(user, "username", None),
            actor_role=getattr(user, "role", None),
            entity_type=entity_type,
            entity_id=entity_id,
            message=message,
            details_json=_serialize_details(details),
        )
        db.session.add(row)
        return row
    except Exception:
        if has_request_context():
            current_app.logger.exception("write_log failed for action=%s", action)
        return None
