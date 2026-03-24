from backend.extensions import db
from backend.models.base import BaseModel, BranchScopedMixin


class Payment(BaseModel, BranchScopedMixin):
    __tablename__ = "payments"

    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=True, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    method = db.Column(db.String(32), nullable=False)
    status = db.Column(db.String(32), nullable=False, default="posted", index=True)
    paid_at = db.Column(db.DateTime, nullable=True, index=True)
    reference_code = db.Column(db.String(128), nullable=True, index=True)
    metadata_json = db.Column(db.Text, nullable=True)

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "branch_id": self.branch_id,
                "invoice_id": self.invoice_id,
                "customer_id": self.customer_id,
                "amount": float(self.amount) if self.amount is not None else None,
                "method": self.method,
                "status": self.status,
                "paid_at": self.paid_at.isoformat() if self.paid_at else None,
                "reference_code": self.reference_code,
                "metadata_json": self.metadata_json,
            }
        )
        return data
