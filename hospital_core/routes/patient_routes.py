from flask import render_template
from hospital_core.models import Patient
from flask import Blueprint

patients_bp = Blueprint('patients', __name__)

@patients_bp.route("/patients")
def view_patients():
    patients = Patient.query.all()
    return render_template("patients/view_patients.html", patients=patients)
