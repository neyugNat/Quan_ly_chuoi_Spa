from backend.extensions import db
from backend.models.base import BaseModel, BranchScopedMixin


class InventoryItem(BaseModel, BranchScopedMixin):
    __tablename__ = "inventory_items"

    name = db.Column(db.String(255), nullable=False)
    sku = db.Column(db.String(64), nullable=True, index=True)
    unit = db.Column(db.String(32), nullable=False)
    min_stock = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    expiry_tracking = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(32), nullable=False, default="active")

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "branch_id": self.branch_id,
                "name": self.name,
                "sku": self.sku,
                "unit": self.unit,
                "min_stock": float(self.min_stock) if self.min_stock is not None else None,
                "expiry_tracking": self.expiry_tracking,
                "status": self.status,
            }
        )
        return data
