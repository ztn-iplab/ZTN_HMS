from datetime import datetime
from hospital_core.extensions import db

# -------------------------------
# Doctor (Authenticated via ZTN-IAM)
# -------------------------------
class Doctor(db.Model):
    __tablename__ = "doctors"

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
# Nurse (Authenticated via ZTN-IAM)
# -------------------------------
class Nurse(db.Model):
    __tablename__ = "nurses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)  # From ZTN-IAM
    full_name = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(100))
    contact_info = db.Column(db.String(150))
    is_active = db.Column(db.Boolean, default=True)

    interactions = db.relationship('NurseInteraction', backref='nurse', lazy=True)


# -------------------------------
# Patient (Locally stored)
# -------------------------------
class Patient(db.Model):
    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10))
    contact_info = db.Column(db.String(150))

    appointments = db.relationship('Appointment', backref='patient', lazy=True)
    diagnoses = db.relationship('Diagnosis', backref='patient', lazy=True)
    nurse_interactions = db.relationship('NurseInteraction', backref='patient', lazy=True)


# -------------------------------
# Appointment
# -------------------------------
class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    purpose = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# -------------------------------
# Diagnosis
# -------------------------------
class Diagnosis(db.Model):
    __tablename__ = "diagnoses"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)
    diagnosis_date = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text)

    treatments = db.relationship('Treatment', backref='diagnosis', lazy=True)


# -------------------------------
# Treatment
# -------------------------------
class Treatment(db.Model):
    __tablename__ = "treatments"

    id = db.Column(db.Integer, primary_key=True)
    diagnosis_id = db.Column(db.Integer, db.ForeignKey('diagnoses.id'), nullable=False)
    medication = db.Column(db.String(200))
    procedure = db.Column(db.String(200))
    notes = db.Column(db.Text)


# -------------------------------
# NurseInteraction
# -------------------------------
class NurseInteraction(db.Model):
    __tablename__ = "nurse_interactions"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    nurse_id = db.Column(db.Integer, db.ForeignKey('nurses.id'), nullable=True)
    notes = db.Column(db.Text)
    interaction_time = db.Column(db.DateTime, default=datetime.utcnow)
