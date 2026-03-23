from datetime import datetime

from sqlalchemy import func

from backend.extensions import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now())
    updated_at = db.Column(
        db.DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class BranchScopedMixin:
    branch_id = db.Column(db.Integer, nullable=False, index=True)


class BaseModel(db.Model, TimestampMixin):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
