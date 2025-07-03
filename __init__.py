from flask import Flask
from config import DevelopmentConfig
from .extensions import db, login_manager
from .routes import register_routes
from .models import User
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    register_routes(app)

    return app

