# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUntypedBaseClass=false

from datetime import datetime

from backend.extensions import db
from backend.models.base import BaseModel, BranchScopedMixin


class CustomerPackage(BaseModel, BranchScopedMixin):
    __tablename__: str = "customer_packages"

    customer_id: int = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False, index=True)
    package_id: int = db.Column(db.Integer, db.ForeignKey("packages.id"), nullable=False, index=True)
    sessions_total: int = db.Column(db.Integer, nullable=False)
    sessions_remaining: int = db.Column(db.Integer, nullable=False)
    expires_at: datetime | None = db.Column(db.DateTime, nullable=True, index=True)
    status: str = db.Column(db.String(32), nullable=False, default="active", index=True)

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "branch_id": self.branch_id,
                "customer_id": self.customer_id,
                "package_id": self.package_id,
                "sessions_total": self.sessions_total,
                "sessions_remaining": self.sessions_remaining,
                "expires_at": self.expires_at.isoformat() if self.expires_at else None,
                "status": self.status,
            }
        )
        return data
