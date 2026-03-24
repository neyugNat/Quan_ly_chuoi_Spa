from backend.extensions import db
from backend.models.base import BaseModel, BranchScopedMixin


class CommissionRecord(BaseModel, BranchScopedMixin):
    __tablename__ = "commission_records"

    staff_id = db.Column(db.Integer, db.ForeignKey("staffs.id"), nullable=False, index=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=True, index=True)
    source_type = db.Column(db.String(64), nullable=True, index=True)
    source_id = db.Column(db.Integer, nullable=True, index=True)
    base_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    rate_percent = db.Column(db.Numeric(5, 2), nullable=True)
    commission_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    status = db.Column(db.String(32), nullable=False, default="pending", index=True)
    payload_json = db.Column(db.Text, nullable=True)

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "branch_id": self.branch_id,
                "staff_id": self.staff_id,
                "invoice_id": self.invoice_id,
                "source_type": self.source_type,
                "source_id": self.source_id,
                "base_amount": float(self.base_amount) if self.base_amount is not None else None,
                "rate_percent": float(self.rate_percent) if self.rate_percent is not None else None,
                "commission_amount": float(self.commission_amount)
                if self.commission_amount is not None
                else None,
                "status": self.status,
                "payload_json": self.payload_json,
            }
        )
        return data
