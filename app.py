import requests
from flask import Flask, render_template, redirect, url_for, request, flash, session, g, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField
from wtforms.validators import DataRequired, Email
from werkzeug.security import generate_password_hash
import certifi
from forms import LoginForm

# Initialize the Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = '7225b2a423a0eb52bffc1278c4d9a97f'  # Use a strong secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ZTN-IAM API URL
ZTN_IAM_URL = "https://localhost.localdomain/api/v1/auth/"  # ZTN-IAM service URL

# Models
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
    
    tenant = db.relationship('Tenant', backref='roles')

    __table_args__ = (
        db.UniqueConstraint('role_name', 'tenant_id', name='uq_role_per_tenant'),
        {'extend_existing': True},  # <<< ✨ THIS IS THE PATCH ✨
    )

class RegisterForm(FlaskForm):
    mobile_number = StringField('Mobile Number', validators=[DataRequired()])
    first_name = StringField('First Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    role = SelectField('Role', choices=[('doctor', 'Doctor'), ('nurse', 'Nurse'), ('admin', 'Admin')], validators=[DataRequired()])

# User loader function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Route for homepage (index.html)
@app.route('/')
def home():
    return render_template('index.html')  # This will be your homepage or landing page


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()  # WTForms form instance
    
    # Fetch roles from ZTN-IAM API
    roles_response = requests.get(
        f"{ZTN_IAM_URL}/roles",  # Assuming the roles endpoint is available in the ZTN-IAM API
        headers={"X-API-KEY": "mohealthapikey987654", "Content-Type": "application/json"},
        verify=False  # Temporarily disable SSL verification for development
    )
    
    # Check if the roles are fetched successfully
    if roles_response.status_code == 200:
        roles = roles_response.json()  # Parse the JSON response
        
        # Populate the role dropdown in the form with the roles fetched from ZTN-IAM
        form.role.choices = [(role['role_name'], role['role_name']) for role in roles]  # Adjust based on the structure of the response
    else:
        roles = []  # In case of an error, use an empty list for roles
        
    if form.validate_on_submit():
        # Prepare registration data to send to ZTN-IAM
        data = {
            "mobile_number": form.mobile_number.data,
            "first_name": form.first_name.data,
            "password": form.password.data,
            "email": form.email.data,
            "role": form.role.data  # Store selected role from the form
        }

        # Send the registration request to ZTN-IAM
        response = requests.post(
            f"{ZTN_IAM_URL}/register", 
            json=data,
            headers={"X-API-KEY": "mohealthapikey987654", "Content-Type": "application/json"},
            verify=False  # Disable SSL verification temporarily for local development
        )
        
        # Check the response from ZTN-IAM
        if response.status_code == 201:
            flash("User successfully registered!", 'success')
            return redirect(url_for('login'))
        else:
            error_message = response.json().get('error', 'An unknown error occurred.')
            flash(f"Registration failed: {error_message}", 'danger')
            return redirect(url_for('register'))

    return render_template('auth/register.html', form=form)


   
# Route for login
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()  # WTForms login form
    if form.validate_on_submit():
        login_data = {
            "identifier": form.username.data,
            "password": form.password.data
        }
        print(f"Sending login data: {login_data}")  # Log data being sent to ZTN-IAM
        
        # Send login request to ZTN-IAM
        try:
            response = requests.post(
                f"{ZTN_IAM_URL}/login", 
                json=login_data,
                headers={"X-API-KEY": "mohealthapikey987654", "Content-Type": "application/json"},
                verify=False  # Disable SSL verification temporarily
            )

            print(f"ZTN-IAM Response Status Code: {response.status_code}")  # Log status code
            print(f"ZTN-IAM Response Body: {response.text}")  # Log raw response body

            data = response.json()

            if response.status_code == 200:
                if "error" in data:
                    flash(f"Error: {data['error']}", 'danger')
                    return redirect(url_for('login'))

                if data.get("message") == "Login successful":
                    access_token = data.get("access_token")
                    role = data.get("role")  # Get role from ZTN-IAM response
                    user_id = data.get("user_id")
                
                    session['access_token'] = access_token
                    session['role'] = role
                    session['user_id'] = user_id

                    if role == 'admin':
                        return redirect(url_for('admin_dashboard'))
                    elif role == 'doctor':
                        return redirect(url_for('doctor_dashboard'))
                    elif role == 'nurse':
                        return redirect(url_for('nurse_dashboard'))
                    else:
                        flash('Role not recognized!', 'danger')
                        return redirect(url_for('login'))
                else:
                    error_message = data.get('error', 'Invalid credentials. Please try again.')
                    flash(error_message, 'danger')
                    return redirect(url_for('login'))
            else:
                flash(f"Unexpected response status code: {response.status_code}", 'danger')
                return redirect(url_for('login'))

        except requests.exceptions.RequestException as e:
            print(f"Request exception: {e}")  # Log exception
            flash("An error occurred while attempting to log in.", 'danger')
            return redirect(url_for('login'))

    return render_template('auth/login.html', form=form)

# Route for dashboard (redirect after login)
# Route for Admin Dashboard
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if session.get('role') != 'admin':
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for('login'))
    return render_template('dashboard/admin_dashboard.html')

# Route for Doctor Dashboard
@app.route('/doctor/dashboard')
@login_required
def doctor_dashboard():
    if session.get('role') != 'doctor':
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for('login'))
    return render_template('dashboard/doctor_dashboard.html')

# Route for Nurse Dashboard
@app.route('/nurse/dashboard')
@login_required
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



if __name__ == '__main__':
    app.run(debug=True, ssl_context=('certs/hospital_app.crt', 'certs/hospital_app.key'))
