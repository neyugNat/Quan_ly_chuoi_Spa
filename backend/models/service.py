from backend.extensions import db
from backend.models.base import BaseModel, BranchScopedMixin


class Service(BaseModel, BranchScopedMixin):
    __tablename__ = "services"

    name = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    duration_minutes = db.Column(db.Integer, nullable=False)
    requirement_json = db.Column(db.Text, nullable=True)
    consumable_recipe_json = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), nullable=False, default="active")

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "branch_id": self.branch_id,
                "name": self.name,
                "price": float(self.price) if self.price is not None else None,
                "duration_minutes": self.duration_minutes,
                "requirement_json": self.requirement_json,
                "consumable_recipe_json": self.consumable_recipe_json,
                "status": self.status,
            }
        )
        return data
