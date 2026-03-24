# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUntypedBaseClass=false

from backend.extensions import db
from backend.models.base import BaseModel, BranchScopedMixin


class Staff(BaseModel, BranchScopedMixin):
    __tablename__: str = "staffs"

    user_id: int | None = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True, index=True
    )
    full_name: str = db.Column(db.String(255), nullable=False)
    phone: str | None = db.Column(db.String(32), nullable=True, index=True)
    title: str | None = db.Column(db.String(64), nullable=True)
    role: str | None = db.Column(db.String(64), nullable=True)
    skill_level: str | None = db.Column(db.String(64), nullable=True)
    commission_scheme_json: str | None = db.Column(db.Text, nullable=True)
    status: str = db.Column(db.String(32), nullable=False, default="active")

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "branch_id": self.branch_id,
                "user_id": self.user_id,
                "full_name": self.full_name,
                "phone": self.phone,
                "title": self.title,
                "role": self.role,
                "skill_level": self.skill_level,
                "commission_scheme_json": self.commission_scheme_json,
                "status": self.status,
            }
        )
        return data
