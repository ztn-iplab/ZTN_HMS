from flask import Blueprint, render_template, session, redirect, url_for, flash
from utils.decorators import aig_required

dashboard_bp = Blueprint("dashboard", __name__)

from functools import wraps

def protect_role(required_roles):
    if isinstance(required_roles, str):
        required_roles = [required_roles]

    def wrapper(fn):
        @wraps(fn)
        def decorated(*args, **kwargs):
            user_role = session.get("role")
            if user_role not in required_roles:
                flash("Access denied.", "danger")
                return redirect(url_for("auth.login"))
            return fn(*args, **kwargs)
        return decorated
    return wrapper

@dashboard_bp.route("/")
def home():
    return render_template("index.html")

@dashboard_bp.route("/admin/dashboard")
@protect_role("admin")
def admin_dashboard():
    return render_template("dashboard/admin_dashboard.html")

@dashboard_bp.route("/doctor/dashboard")
@protect_role("doctor")
def doctor_dashboard():
    return render_template("dashboard/doctor_dashboard.html")

@dashboard_bp.route("/nurse/dashboard")
@protect_role("nurse")
def nurse_dashboard():
    return render_template("dashboard/nurse_dashboard.html")

@dashboard_bp.route("/admin/users")
@protect_role("admin")
def user_management():
    return render_template("admin/user_management.html", users=[])

@dashboard_bp.route("/admin/metrics")
@protect_role("admin")
def system_metrics():
    return render_template("admin/system_metrics.html")

@dashboard_bp.route("/patients/view")
@protect_role("doctor")
@aig_required("view_patient_list", action_class="ehr_read", threshold=0.65)
def view_patients():
    from hospital_core.models import Patient
    patients = Patient.query.all()
    return render_template("patients/view_patients.html", patients=patients)

@dashboard_bp.route("/appointments/manage")
@protect_role("doctor")
@aig_required("manage_appointments", action_class="clinical_schedule", threshold=0.65)
def manage_appointments():
    return render_template("records/manage_appointments.html")

@dashboard_bp.route("/appointments")
@protect_role("nurse")
@aig_required("view_appointments", action_class="clinical_schedule", threshold=0.6)
def view_appointments():
    if session.get("role") not in ["doctor", "nurse"]:
        flash("Access denied.", "danger")
        return redirect(url_for("auth.login"))
    return render_template("records/view.html")

@dashboard_bp.route("/patients/info")
@protect_role("nurse")
@aig_required("view_patient_details", action_class="ehr_read", threshold=0.7)
def view_patient_details():
    return render_template("patients/view_patients.html")
