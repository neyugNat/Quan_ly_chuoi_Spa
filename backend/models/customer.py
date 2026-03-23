from backend.extensions import db
from backend.models.base import BaseModel, BranchScopedMixin


class Customer(BaseModel, BranchScopedMixin):
    __tablename__ = "customers"

    full_name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(32), nullable=False, index=True)
    email = db.Column(db.String(255), nullable=True, index=True)
    dob = db.Column(db.String(16), nullable=True)
    gender = db.Column(db.String(16), nullable=True)
    address = db.Column(db.String(500), nullable=True)
    tags_json = db.Column(db.Text, nullable=True)
    allergy_note = db.Column(db.Text, nullable=True)
    marketing_consent = db.Column(db.Boolean, nullable=False, default=False)
    note = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), nullable=False, default="active")

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "branch_id": self.branch_id,
                "full_name": self.full_name,
                "phone": self.phone,
                "email": self.email,
                "dob": self.dob,
                "gender": self.gender,
                "address": self.address,
                "tags_json": self.tags_json,
                "allergy_note": self.allergy_note,
                "marketing_consent": self.marketing_consent,
                "note": self.note,
                "status": self.status,
            }
        )
        return data
