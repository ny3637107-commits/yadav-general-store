import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

ENVIRONMENT = os.environ.get('FLASK_ENV', os.environ.get('ENVIRONMENT', 'development')).lower()

raw_secret = os.environ.get('SECRET_KEY')
if not raw_secret or not raw_secret.strip():
    raise RuntimeError(
        "FATAL SECURITY ERROR: SECRET_KEY environment variable MUST be explicitly set and non-empty in both development and production."
    )
SECRET_KEY = raw_secret.strip()

class Config:
    ENVIRONMENT = ENVIRONMENT
    SECRET_KEY = SECRET_KEY
    DB_PATH = os.path.join(BASE_DIR, 'yadav_store.db')

    # Upload Directories
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    PAYMENTS_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'payments')
    PRODUCTS_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'products')

    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload

    # Cookie & Security Configuration
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = (ENVIRONMENT == 'production') or (os.environ.get('COOKIE_SECURE', 'false').lower() == 'true')

    # Rate Limiting Configuration
    MAX_FAILED_LOGIN_ATTEMPTS = 5
    LOGIN_LOCKOUT_SECONDS = 300  # 5 minutes

    DEBUG = (ENVIRONMENT != 'production')
