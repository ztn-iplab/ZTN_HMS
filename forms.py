# hospital_app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField
from wtforms.validators import DataRequired, Email

class RegisterForm(FlaskForm):
    mobile_number = StringField('Mobile Number', validators=[DataRequired()])
    first_name = StringField('First Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    role = SelectField('Role', choices=[], validators=[DataRequired()])
    custom_role = StringField('Custom Role')
