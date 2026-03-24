import json

from backend.extensions import db
from backend.models.base import BaseModel


class AuditLog(BaseModel):
    __tablename__ = "audit_logs"

    user_id = db.Column(db.Integer, nullable=True, index=True)
    branch_id = db.Column(db.Integer, nullable=True, index=True)
    action = db.Column(db.String(128), nullable=False, index=True)
    entity = db.Column(db.String(128), nullable=True, index=True)
    before_json = db.Column(db.Text, nullable=True)
    after_json = db.Column(db.Text, nullable=True)

    @staticmethod
    def dumps(payload):
        if payload is None:
            return None
        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "user_id": self.user_id,
                "branch_id": self.branch_id,
                "action": self.action,
                "entity": self.entity,
                "before_json": self.before_json,
                "after_json": self.after_json,
            }
        )
        return data
