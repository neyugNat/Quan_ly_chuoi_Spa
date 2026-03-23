from backend.extensions import db
from backend.models.base import BaseModel, BranchScopedMixin


class StockTransaction(BaseModel, BranchScopedMixin):
    __tablename__ = "stock_transactions"

    inventory_item_id = db.Column(
        db.Integer, db.ForeignKey("inventory_items.id"), nullable=False, index=True
    )
    transaction_type = db.Column(db.String(32), nullable=False, index=True)
    delta_qty = db.Column(db.Numeric(12, 3), nullable=False)
    source_type = db.Column(db.String(64), nullable=True, index=True)
    source_id = db.Column(db.Integer, nullable=True, index=True)
    counterparty_branch_id = db.Column(db.Integer, nullable=True, index=True)
    expiry_date = db.Column(db.Date, nullable=True, index=True)
    note = db.Column(db.Text, nullable=True)

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "branch_id": self.branch_id,
                "inventory_item_id": self.inventory_item_id,
                "transaction_type": self.transaction_type,
                "delta_qty": float(self.delta_qty) if self.delta_qty is not None else None,
                "source_type": self.source_type,
                "source_id": self.source_id,
                "counterparty_branch_id": self.counterparty_branch_id,
                "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
                "note": self.note,
            }
        )
        return data
