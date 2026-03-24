from backend.extensions import db
from backend.models.base import BaseModel


class TreatmentNote(BaseModel):
    __tablename__ = "treatment_notes"

    appointment_id = db.Column(
        db.Integer, db.ForeignKey("appointments.id"), nullable=False, index=True
    )
    staff_id = db.Column(db.Integer, db.ForeignKey("staffs.id"), nullable=True, index=True)
    subjective_note = db.Column(db.Text, nullable=True)
    objective_note = db.Column(db.Text, nullable=True)
    assessment_note = db.Column(db.Text, nullable=True)
    plan_note = db.Column(db.Text, nullable=True)
    attachment_json = db.Column(db.Text, nullable=True)

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "appointment_id": self.appointment_id,
                "staff_id": self.staff_id,
                "subjective_note": self.subjective_note,
                "objective_note": self.objective_note,
                "assessment_note": self.assessment_note,
                "plan_note": self.plan_note,
                "attachment_json": self.attachment_json,
            }
        )
        return data
