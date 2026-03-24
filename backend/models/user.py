from werkzeug.security import check_password_hash, generate_password_hash

from backend.extensions import db
from backend.models.base import BaseModel


class UserRole(db.Model):
    __tablename__ = "user_roles"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), primary_key=True)


class UserBranch(db.Model):
    __tablename__ = "user_branches"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), primary_key=True)


class Role(BaseModel):
    __tablename__ = "roles"

    name = db.Column(db.String(64), nullable=False, unique=True, index=True)

    def to_dict(self):
        data = super().to_dict()
        data.update({"name": self.name})
        return data


class User(BaseModel):
    __tablename__ = "users"

    username = db.Column(db.String(64), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    reset_password_token = db.Column(db.String(255), nullable=True, index=True)
    reset_password_expires_at = db.Column(db.DateTime, nullable=True)

    roles = db.relationship(
        "Role",
        secondary="user_roles",
        lazy="selectin",
    )
    branches = db.relationship(
        "Branch",
        secondary="user_branches",
        lazy="selectin",
    )

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def verify_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def role_names(self):
        return [r.name for r in (self.roles or [])]

    def branch_ids(self):
        if "super_admin" in self.role_names():
            from backend.models.branch import Branch

            return [branch_id for (branch_id,) in Branch.query.with_entities(Branch.id).order_by(Branch.id.asc()).all()]

        return [b.id for b in (self.branches or [])]

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "username": self.username,
                "is_active": self.is_active,
                "roles": self.role_names(),
                "branch_ids": self.branch_ids(),
            }
        )
        return data
