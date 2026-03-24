# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUntypedBaseClass=false

from datetime import datetime

from backend.extensions import db
from backend.models.base import BaseModel, BranchScopedMixin


class Shift(BaseModel, BranchScopedMixin):
    __tablename__: str = "shifts"

    staff_id: int = db.Column(db.Integer, db.ForeignKey("staffs.id"), nullable=False, index=True)
    start_time: datetime = db.Column(db.DateTime, nullable=False, index=True)
    end_time: datetime = db.Column(db.DateTime, nullable=False, index=True)
    status: str = db.Column(db.String(32), nullable=False, default="active", index=True)
    note: str | None = db.Column(db.Text, nullable=True)

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "branch_id": self.branch_id,
                "staff_id": self.staff_id,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "status": self.status,
                "note": self.note,
            }
        )
        return data
