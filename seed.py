from hospital_core import create_app
from hospital_core.extensions import db
from hospital_core.models import Doctor, Patient, Appointment, Diagnosis, Treatment
from datetime import datetime

app = create_app()

with app.app_context():
    # 🔁 Clear all data (optional: for a clean test)
    db.drop_all()
    db.create_all()

    # 👨‍⚕️ Create 5 doctors
    doctors = [
        Doctor(user_id=101, full_name="Dr. Naomi Okeke", specialization="Cardiology", department="Heart Unit", contact_info="naomi.okeke@hospital.org"),
        Doctor(user_id=102, full_name="Dr. James Mwangi", specialization="Neurology", department="Brain and Spine", contact_info="james.mwangi@hospital.org"),
        Doctor(user_id=103, full_name="Dr. Sarah Kamanzi", specialization="Pediatrics", department="Children's Ward", contact_info="sarah.kamanzi@hospital.org"),
        Doctor(user_id=104, full_name="Dr. Emmanuel Nsubuga", specialization="Orthopedics", department="Bone and Joints", contact_info="emmanuel.nsubuga@hospital.org"),
        Doctor(user_id=105, full_name="Dr. Linda Mugisha", specialization="General Surgery", department="Surgical Unit", contact_info="linda.mugisha@hospital.org")
    ]

    # 🧑 Create 5 patients
    patients = [
        Patient(full_name="John Bizimana", date_of_birth=datetime(1990, 4, 12), gender="Male", contact_info="john.b@example.com"),
        Patient(full_name="Jane Nyambura", date_of_birth=datetime(1985, 8, 5), gender="Female", contact_info="jane.nyambura@example.com"),
        Patient(full_name="Samuel Akinyi", date_of_birth=datetime(1992, 11, 22), gender="Male", contact_info="samuel.akinyi@example.com"),
        Patient(full_name="Tina Kagabo", date_of_birth=datetime(1994, 2, 13), gender="Female", contact_info="tina.kagabo@example.com"),
        Patient(full_name="Richard Mutebi", date_of_birth=datetime(1988, 6, 30), gender="Male", contact_info="richard.mutebi@example.com")
    ]

    # 📅 Create 5 appointments
    appointments = [
        Appointment(patient=patients[0], doctor=doctors[0], scheduled_time=datetime(2025, 7, 10, 14, 0), purpose="Routine heart checkup"),
        Appointment(patient=patients[1], doctor=doctors[1], scheduled_time=datetime(2025, 7, 11, 9, 30), purpose="Neurological evaluation"),
        Appointment(patient=patients[2], doctor=doctors[2], scheduled_time=datetime(2025, 7, 12, 10, 0), purpose="Pediatric consultation"),
        Appointment(patient=patients[3], doctor=doctors[3], scheduled_time=datetime(2025, 7, 13, 15, 30), purpose="Orthopedic checkup"),
        Appointment(patient=patients[4], doctor=doctors[4], scheduled_time=datetime(2025, 7, 14, 11, 0), purpose="Surgical assessment")
    ]

    # 🩺 Add 5 diagnoses
    diagnoses = [
        Diagnosis(patient=patients[0], doctor=doctors[0], description="Mild arrhythmia"),
        Diagnosis(patient=patients[1], doctor=doctors[1], description="Chronic migraine"),
        Diagnosis(patient=patients[2], doctor=doctors[2], description="Asthma"),
        Diagnosis(patient=patients[3], doctor=doctors[3], description="Fractured tibia"),
        Diagnosis(patient=patients[4], doctor=doctors[4], description="Appendicitis")
    ]

    # 💊 Add 5 treatments
    treatments = [
        Treatment(diagnosis=diagnoses[0], medication="Beta-blockers", procedure="ECG monitoring", notes="Patient to return in 1 month"),
        Treatment(diagnosis=diagnoses[1], medication="Sumatriptan", procedure="MRI", notes="Prescribed rest and hydration"),
        Treatment(diagnosis=diagnoses[2], medication="Salbutamol inhaler", procedure="Pulmonary function test", notes="Follow-up in 6 months"),
        Treatment(diagnosis=diagnoses[3], medication="Pain relievers", procedure="X-ray", notes="Casting required for 6 weeks"),
        Treatment(diagnosis=diagnoses[4], medication="Antibiotics", procedure="Appendectomy", notes="Post-surgery monitoring required")
    ]

    # Add all data to session
    db.session.add_all(doctors + patients + appointments + diagnoses + treatments)
    db.session.commit()

    print("✅ Seeded hospital database with 5 records for each entity.")
from hospital_core import create_app
from hospital_core.extensions import db
from hospital_core.models import Doctor, Patient, Appointment, Diagnosis, Treatment

from datetime import datetime

app = create_app()

with app.app_context():
    # 🔁 Clear all data (optional: for a clean test)
    db.drop_all()
    db.create_all()

    # 👨‍⚕️ Create a doctor
    doc = Doctor(
        user_id=101,  # Simulate a ZTN-IAM user ID
        full_name="Dr. Naomi Okeke",
        specialization="Cardiology",
        department="Heart Unit",
        contact_info="naomi.okeke@hospital.org"
    )

    # 🧑 Create a patient
    pat = Patient(
        full_name="John Bizimana",
        date_of_birth=datetime(1990, 4, 12),
        gender="Male",
        contact_info="john.b@example.com"
    )

    # 📅 Create an appointment
    appt = Appointment(
        patient=pat,
        doctor=doc,
        scheduled_time=datetime(2025, 7, 10, 14, 0),
        purpose="Routine heart checkup"
    )

    # 🩺 Add a diagnosis
    diag = Diagnosis(
        patient=pat,
        doctor=doc,
        description="Mild arrhythmia"
    )

    # 💊 Add a treatment
    treat = Treatment(
        diagnosis=diag,
        medication="Beta-blockers",
        procedure="ECG monitoring",
        notes="Patient to return in 1 month"
    )

    db.session.add_all([doc, pat, appt, diag, treat])
    db.session.commit()

    print("✅ Seeded hospital database with test data.")

