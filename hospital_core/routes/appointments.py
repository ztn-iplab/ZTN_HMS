from flask import Blueprint, render_template, session, redirect, url_for, flash
from hospital_core.models import Appointment, Doctor
from flask_sqlalchemy import SQLAlchemy

appointments_bp = Blueprint("appointments", __name__)

# Protect route so only doctors can access it
@appointments_bp.route("/appointments/manage")
def manage_appointments():
    if not session.get("role") == "doctor":
        flash("Access denied.", "danger")
        return redirect(url_for("auth.login"))

    # Get appointments for logged-in doctor
    doctor_id = session.get("user_id")
    appointments = Appointment.query.all()

    return render_template("appointments/manage_appointments.html", appointments=appointments)


# Edit appointment route
@appointments_bp.route("/appointments/edit/<int:appointment_id>", methods=["GET", "POST"])
def edit_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if request.method == "POST":
        appointment.scheduled_time = request.form["scheduled_time"]
        appointment.purpose = request.form["purpose"]
        db.session.commit()
        flash("Appointment updated successfully.", "success")
        return redirect(url_for("appointments.manage_appointments"))

    return render_template("appointments/edit_appointment.html", appointment=appointment)


# Delete appointment route
@appointments_bp.route("/appointments/delete/<int:appointment_id>")
def delete_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    db.session.delete(appointment)
    db.session.commit()
    flash("Appointment deleted successfully.", "success")
    return redirect(url_for("appointments.manage_appointments"))
