from backend.extensions import db
from backend.models.base import BaseModel, BranchScopedMixin


class Resource(BaseModel, BranchScopedMixin):
    __tablename__ = "resources"

    name = db.Column(db.String(255), nullable=False)
    resource_type = db.Column(db.String(32), nullable=False, index=True)
    code = db.Column(db.String(64), nullable=True, index=True)
    maintenance_flag = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(32), nullable=False, default="active")
    note = db.Column(db.Text, nullable=True)

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "branch_id": self.branch_id,
                "name": self.name,
                "resource_type": self.resource_type,
                "code": self.code,
                "maintenance_flag": self.maintenance_flag,
                "status": self.status,
                "note": self.note,
            }
        )
        return data
