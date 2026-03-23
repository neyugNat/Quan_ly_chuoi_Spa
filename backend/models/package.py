from backend.extensions import db
from backend.models.base import BaseModel, BranchScopedMixin


class Package(BaseModel, BranchScopedMixin):
    __tablename__ = "packages"

    name = db.Column(db.String(255), nullable=False)
    sessions_total = db.Column(db.Integer, nullable=False)
    validity_days = db.Column(db.Integer, nullable=True)
    shareable = db.Column(db.Boolean, nullable=False, default=False)
    allowed_branches_json = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), nullable=False, default="active")

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "branch_id": self.branch_id,
                "name": self.name,
                "sessions_total": self.sessions_total,
                "validity_days": self.validity_days,
                "shareable": self.shareable,
                "allowed_branches_json": self.allowed_branches_json,
                "status": self.status,
            }
        )
        return data
