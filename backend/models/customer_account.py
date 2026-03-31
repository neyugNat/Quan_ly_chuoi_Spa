from werkzeug.security import check_password_hash, generate_password_hash

from backend.extensions import db
from backend.models.base import BaseModel


class CustomerAccount(BaseModel):
    __tablename__ = "customer_accounts"

    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customers.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    reset_password_token = db.Column(db.String(255), nullable=True, index=True)
    reset_password_expires_at = db.Column(db.DateTime, nullable=True)

    customer = db.relationship("Customer", lazy="joined")

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def verify_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def to_dict(self):
        data = super().to_dict()
        customer = self.customer
        data.update(
            {
                "customer_id": self.customer_id,
                "email": self.email,
                "is_active": self.is_active,
                "customer": (
                    {
                        "id": customer.id,
                        "branch_id": customer.branch_id,
                        "full_name": customer.full_name,
                        "phone": customer.phone,
                        "email": customer.email,
                        "status": customer.status,
                    }
                    if customer
                    else None
                ),
            }
        )
        return data
