# hospital_core/__init__.py

import os
from flask import Flask
from config import DevelopmentConfig
from hospital_core.extensions import db, login_manager, migrate
from hospital_core.routes import register_routes
from flask_jwt_extended import JWTManager
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

jwt = JWTManager()

def create_app(config_class=DevelopmentConfig):
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
        static_folder=os.path.join(os.path.dirname(__file__), '..', 'static')
    )

    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    # # ✅ Force model registration inside app context
    # with app.app_context():
    #     import hospital_core.models  # 👈 this is key
    #     print("📦 Registered Models:", db.metadata.tables.keys())  # debug log

    # Register Blueprints/routes
    register_routes(app)

    @login_manager.user_loader
    def load_user(user_id):
        return None

    return app
