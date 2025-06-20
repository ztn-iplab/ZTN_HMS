import requests
from flask import Flask, render_template, redirect, url_for, request, flash, session, g, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from wtforms import StringField, PasswordField, SelectField
from wtforms.validators import DataRequired, Email
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash
import requests
import certifi
from routes.auth import auth_bp

# === App Configuration ===
app = Flask(__name__)
app.config['SECRET_KEY'] = '7225b2a423a0eb52bffc1278c4d9a97f'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


#BluePrints
app.register_blueprint(auth_bp)

# === Extensions ===
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# === ZTN-IAM API URL ===
ZTN_IAM_URL = "https://localhost.localdomain/api/v1/auth"
API_KEY = "mohealthapikey987654"

# === Models ===
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    tenant_id = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"

class UserRole(db.Model):
    __tablename__ = 'user_roles'
    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(50), nullable=False)
    permissions = db.Column(db.JSON)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=True)

    __table_args__ = (
        db.UniqueConstraint('role_name', 'tenant_id', name='uq_role_per_tenant'),
        {'extend_existing': True},
    )

# === Forms ===
class RegisterForm(FlaskForm):
    mobile_number = StringField('Mobile Number', validators=[DataRequired()])
    first_name = StringField('First Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    role = SelectField('Role', choices=[], validators=[DataRequired()])
    custom_role = StringField('Custom Role')

# === User Loader ===
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# === Routes ===
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    # Fetch available roles from ZTN-IAM
    try:
        roles_response = requests.get(
            f"{ZTN_IAM_URL}/roles",
            headers={"X-API-KEY": API_KEY, "Content-Type": "application/json"},
            verify=False
        )
        if roles_response.status_code == 200:
            roles = roles_response.json()
            if roles:
                form.role.choices = [(r["role_name"], r["role_name"]) for r in roles]
                form.role.choices.append(("other", "Other"))  # 🔥 Allow dynamic roles
            else:
                flash("No roles defined for your tenant. Please contact admin.", 'warning')
        else:
            flash("Could not fetch roles from IAM service.", 'danger')

    except Exception as e:
        flash("IAM connection failed.", "danger")
        form.role.choices = [('user', 'User'), ('other', 'Other')]

    if form.validate_on_submit():
        selected_role = form.role.data

        # 🔥 If tenant chose "Other", attempt to create the new role first
        if selected_role == "other":
            custom_role = form.custom_role.data.strip()
            if not custom_role:
                flash("Custom role name is required.", "danger")
                return redirect(url_for("register"))

            # Try to create the new role via IAM
            try:
                role_creation = requests.post(
                    f"{ZTN_IAM_URL}/roles",
                    json={"role_name": custom_role, "permissions": {}},  # Permissions can be extended later
                    headers={
                        "X-API-KEY": API_KEY,
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {get_admin_token()}"  # Optional if your IAM requires JWT
                    },
                    verify=False
                )
                if role_creation.status_code != 201:
                    error_msg = role_creation.json().get("error", "Unknown error while creating custom role.")
                    flash(f"Custom role creation failed: {error_msg}", "danger")
                    return redirect(url_for("register"))
                selected_role = custom_role  # Set it to use in registration below
            except Exception:
                flash("Failed to create custom role via IAM.", "danger")
                return redirect(url_for("register"))

        # Proceed to register user with final role
        data = {
            "mobile_number": form.mobile_number.data,
            "first_name": form.first_name.data,
            "email": form.email.data,
            "password": form.password.data,
            "role": selected_role
        }
        try:
            response = requests.post(
                f"{ZTN_IAM_URL}/register",
                json=data,
                headers={"X-API-KEY": API_KEY, "Content-Type": "application/json"},
                verify=False
            )
            if response.status_code == 201:
                flash("User successfully registered!", "success")
                return redirect(url_for("login"))
            else:
                error = response.json().get("error", "An unknown error occurred.")
                flash(f"Registration failed: {error}", "danger")
        except Exception:
            flash("Failed to communicate with IAM service.", "danger")

    return render_template("auth/register.html", form=form)


  
# Route for login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        identifier = request.form.get("email")  # your input name is 'email'
        password = request.form.get("password")

        print("🔐 Identifier:", identifier)
        print("🔐 Password:", password)

        login_data = {
            "identifier": identifier,
            "password": password
        }

        try:
            response = requests.post(
                f"{ZTN_IAM_URL}/login",
                json=login_data,
                headers={"X-API-KEY": "mohealthapikey987654", "Content-Type": "application/json"},
                verify=False
            )

            print("📡 IAM Response:", response.status_code, response.text)

            data = response.json()
            if response.status_code == 200 and data.get("access_token"):
                session["access_token"] = data["access_token"]
                session["role"] = data.get("role")
                session["user_id"] = data.get("user_id")

                # 🔐 TOTP Handling
                if data.get("require_totp_setup"):
                    return redirect(url_for("setup_totp"))  # Redirect to setup

                if data.get("require_totp"):
                    return redirect(url_for("verify_totp"))  # Redirect to verify

                # ✅ Role-based redirect
                role = data.get("role")
                if role == "admin":
                    return redirect(url_for("admin_dashboard"))
                elif role == "doctor":
                    return redirect(url_for("doctor_dashboard"))
                elif role == "nurse":
                    return redirect(url_for("nurse_dashboard"))
                else:
                    flash("Unknown role.", "danger")
                    return redirect(url_for("login"))

            else:
                flash(data.get("error", "Login failed."), "danger")
                return redirect(url_for("login"))

        except Exception as e:
            print("❌ Exception:", e)
            flash("Login error.", "danger")
            return redirect(url_for("login"))

    return render_template("auth/login.html")



# Route for dashboard (redirect after login)
# Route for Admin Dashboard
@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for('login'))
    return render_template('dashboard/admin_dashboard.html')

# Route for Doctor Dashboard
@app.route('/doctor/dashboard')
def doctor_dashboard():
    if session.get('role') != 'doctor':
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for('login'))
    return render_template('dashboard/doctor_dashboard.html')

# Route for Nurse Dashboard
@app.route('/nurse/dashboard')
def nurse_dashboard():
    if session.get('role') != 'nurse':
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for('login'))
    return render_template('dashboard/nurse_dashboard.html')

# Route to test forgot-password functionality
@app.route('/test-forgot-password', methods=['POST'])
def test_forgot_password():
    data = request.get_json()
    identifier = data.get('identifier')

    if not identifier:
        return jsonify({"error": "Identifier is required."}), 400

    # Proceed with logic to send a reset request to ZTN-IAM
    response = requests.post(
        f"{ZTN_IAM_URL}/forgot-password",
        json={"identifier": identifier},
        headers={"X-API-KEY": "mohealthapikey987654", "Content-Type": "application/json"},
        verify=False  # Disable SSL verification temporarily for local development
    )
    
    # Handle ZTN-IAM Response
    if response.status_code == 200:
        return jsonify({"message": "Password reset email sent."}), 200
    else:
        error_message = response.json().get('error', 'An unknown error occurred.')
        return jsonify({"error": error_message}), response.status_code

@app.route("/setup-totp")
def setup_totp():
    return render_template("auth/setup_totp.html")


@app.route("/verify-totp")
def verify_totp():
    return render_template("auth/verify_totp.html")  # We'll customize this too

@app.route('/patients/view')
def view_patients():
    return render_template('patients/view_patients.html')

@app.route('/appointments/manage')
def manage_appointments():
    return render_template('records/manage_appointments.html')

# View Appointments (linked from Nurse dashboard)
@app.route('/appointments')
def view_appointments():
    # appointments = []  # Replace with actual query
    return render_template('appointments/view.html')

# View Patient Info (linked from Nurse dashboard)
@app.route('/patients/info')
def view_patient_details():
    # patients = []  
    return render_template('patients/details.html')

# 👥 User Management 
@app.route('/admin/users')
# @admin_required
def user_management():
    return render_template("admin/user_management.html")

# 📊 System Metrics 
@app.route('/admin/metrics')
# @admin_required
def system_metrics():
    return render_template("admin/system_metrics.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("login"))

if __name__ == '__main__':
    app.run(debug=True, ssl_context=('certs/hospital_app.crt', 'certs/hospital_app.key'))
