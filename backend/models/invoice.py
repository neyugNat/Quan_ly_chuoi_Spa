from backend.extensions import db
from backend.models.base import BaseModel, BranchScopedMixin


class Invoice(BaseModel, BranchScopedMixin):
    __tablename__ = "invoices"

    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=True, index=True)
    appointment_id = db.Column(
        db.Integer, db.ForeignKey("appointments.id"), nullable=True, index=True
    )
    subtotal_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    discount_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    tax_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    paid_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    balance_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    status = db.Column(db.String(32), nullable=False, default="unpaid", index=True)
    line_items_json = db.Column(db.Text, nullable=True)

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "branch_id": self.branch_id,
                "customer_id": self.customer_id,
                "appointment_id": self.appointment_id,
                "subtotal_amount": float(self.subtotal_amount)
                if self.subtotal_amount is not None
                else None,
                "discount_amount": float(self.discount_amount)
                if self.discount_amount is not None
                else None,
                "tax_amount": float(self.tax_amount) if self.tax_amount is not None else None,
                "total_amount": float(self.total_amount)
                if self.total_amount is not None
                else None,
                "paid_amount": float(self.paid_amount) if self.paid_amount is not None else None,
                "balance_amount": float(self.balance_amount)
                if self.balance_amount is not None
                else None,
                "status": self.status,
                "line_items_json": self.line_items_json,
            }
        )
        return data
