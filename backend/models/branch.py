from backend.extensions import db
from backend.models.base import BaseModel


class Branch(BaseModel):
    __tablename__ = "branches"

    name = db.Column(db.String(255), nullable=False)
    address = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(32), nullable=False, default="active")
    working_hours_json = db.Column(db.Text, nullable=True)

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "name": self.name,
                "address": self.address,
                "status": self.status,
                "working_hours_json": self.working_hours_json,
            }
        )
        return data
