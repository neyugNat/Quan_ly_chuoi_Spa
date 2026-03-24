# pyright: basic, reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUntypedBaseClass=false

from backend.extensions import db
from backend.models.base import BaseModel, BranchScopedMixin


class Appointment(BaseModel, BranchScopedMixin):
    __tablename__ = "appointments"
    __table_args__ = (
        db.Index("ix_appointments_branch_start", "branch_id", "start_time"),
        db.Index("ix_appointments_branch_end", "branch_id", "end_time"),
    )

    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False, index=True)
    customer_package_id = db.Column(
        db.Integer, db.ForeignKey("customer_packages.id"), nullable=True, index=True
    )
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=True, index=True)
    staff_id = db.Column(db.Integer, db.ForeignKey("staffs.id"), nullable=True, index=True)
    resource_id = db.Column(db.Integer, db.ForeignKey("resources.id"), nullable=True, index=True)
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False, index=True)
    buffer_before_minutes = db.Column(db.Integer, nullable=False, default=0)
    buffer_after_minutes = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(32), nullable=False, default="booked", index=True)
    service_started_at = db.Column(db.DateTime, nullable=True)
    service_completed_at = db.Column(db.DateTime, nullable=True)
    sessions_used = db.Column(db.Integer, nullable=False, default=1)
    note = db.Column(db.Text, nullable=True)

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "branch_id": self.branch_id,
                "customer_id": self.customer_id,
                "customer_package_id": self.customer_package_id,
                "service_id": self.service_id,
                "staff_id": self.staff_id,
                "resource_id": self.resource_id,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "buffer_before_minutes": self.buffer_before_minutes,
                "buffer_after_minutes": self.buffer_after_minutes,
                "status": self.status,
                "service_started_at": self.service_started_at.isoformat() if self.service_started_at else None,
                "service_completed_at": self.service_completed_at.isoformat() if self.service_completed_at else None,
                "sessions_used": self.sessions_used,
                "note": self.note,
            }
        )
        return data
