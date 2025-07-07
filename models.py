from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# -------------------------------
# 👨‍⚕️ Doctor (Authenticated via ZTN-IAM)
# -------------------------------
class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)  # From ZTN-IAM
    full_name = db.Column(db.String(120), nullable=False)
    specialization = db.Column(db.String(100))
    department = db.Column(db.String(100))
    contact_info = db.Column(db.String(150))
    is_active = db.Column(db.Boolean, default=True)

    appointments = db.relationship('Appointment', backref='doctor', lazy=True)
    diagnoses = db.relationship('Diagnosis', backref='doctor', lazy=True)


# -------------------------------
# 👩‍⚕️ Nurse (Authenticated via ZTN-IAM)
# -------------------------------
class Nurse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)  # From ZTN-IAM
    full_name = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(100))
    contact_info = db.Column(db.String(150))
    is_active = db.Column(db.Boolean, default=True)

    interactions = db.relationship('NurseInteraction', backref='nurse', lazy=True)


# -------------------------------
# 🧑‍🦲 Patient (Locally stored)
# -------------------------------
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10))
    contact_info = db.Column(db.String(150))

    appointments = db.relationship('Appointment', backref='patient', lazy=True)
    diagnoses = db.relationship('Diagnosis', backref='patient', lazy=True)
    nurse_interactions = db.relationship('NurseInteraction', backref='patient', lazy=True)


# -------------------------------
# 📆 Appointment
# -------------------------------
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=True)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    purpose = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# -------------------------------
# 🧾 Diagnosis
# -------------------------------
class Diagnosis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=True)
    diagnosis_date = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text)

    treatments = db.relationship('Treatment', backref='diagnosis', lazy=True)


# -------------------------------
# 💊 Treatment
# -------------------------------
class Treatment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    diagnosis_id = db.Column(db.Integer, db.ForeignKey('diagnosis.id'), nullable=False)
    medication = db.Column(db.String(200))
    procedure = db.Column(db.String(200))
    notes = db.Column(db.Text)


# -------------------------------
# 🧑‍⚕️ NurseInteraction
# -------------------------------
class NurseInteraction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    nurse_id = db.Column(db.Integer, db.ForeignKey('nurse.id'), nullable=True)
    notes = db.Column(db.Text)
    interaction_time = db.Column(db.DateTime, default=datetime.utcnow)
