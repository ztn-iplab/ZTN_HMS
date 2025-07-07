import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ZTN_IAM_URL = os.getenv("ZTN_IAM_URL")
    API_KEY = os.getenv("API_KEY")

    # ✅ JWT Configuration for Cookie-based Auth
    JWT_TOKEN_LOCATION = ['cookies']
    JWT_ACCESS_COOKIE_NAME = 'access_token_cookie'
    # JWT_REFRESH_COOKIE_NAME = 'refresh_token_cookie'

    JWT_COOKIE_SECURE = False  # True in prod
    JWT_COOKIE_SAMESITE = "Lax"
    JWT_COOKIE_CSRF_PROTECT = False
        # Prevent CSRF from external origins

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    JWT_COOKIE_SECURE = True  # ⛓️ Enforce secure cookies in prod
