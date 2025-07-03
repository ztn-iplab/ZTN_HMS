from .auth_routes import auth_bp
from .dashboard_routes import dashboard_bp

def register_routes(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)

