from .auth_routes import auth_bp
from .dashboard_routes import dashboard_bp
from .patient_routes import patients_bp
from .appointments import appointments_bp

def register_routes(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(patients_bp)
    app.register_blueprint(appointments_bp)
