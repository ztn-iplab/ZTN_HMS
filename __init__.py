# hospital_app/__init__.py

from flask import Flask
from config import DevelopmentConfig
from .extensions import db, login_manager
from .routes import register_routes
from .models import db as models_db, Doctor, Nurse, Patient, Appointment, Diagnosis, Treatment, NurseInteraction
from flask_jwt_extended import JWTManager
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

jwt = JWTManager()

def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    jwt.init_app(app)

    # Register Blueprints/routes FIRST
    register_routes(app)

    # Then create tables AFTER everything is fully registered
    with app.app_context():
        db.create_all()

    @login_manager.user_loader
    def load_user(user_id):
        return None

    return app
