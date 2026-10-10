import time
import threading
from functools import wraps
from flask import session, request, jsonify, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db
from config import Config

# ==========================================
# THREAD-SAFE LOGIN RATE LIMITER
# ==========================================
_lock = threading.Lock()
_failed_attempts = {}  # key: (scope, ip) -> list of timestamp floats

def check_rate_limit(ip: str, scope: str = 'login'):
    """
    Checks if an IP has exceeded maximum failed attempts within the lockout window.
    Returns (is_allowed: bool, retry_after_seconds: int).
    """
    now = time.time()
    window = Config.LOGIN_LOCKOUT_SECONDS
    max_attempts = Config.MAX_FAILED_LOGIN_ATTEMPTS
    key = (scope, ip)

    with _lock:
        timestamps = _failed_attempts.get(key, [])
        # Filter timestamps within the sliding window
        valid_timestamps = [t for t in timestamps if now - t < window]
        _failed_attempts[key] = valid_timestamps

        if len(valid_timestamps) >= max_attempts:
            oldest = valid_timestamps[0]
            retry_after = int(window - (now - oldest)) + 1
            return False, retry_after
        return True, 0

def record_failed_attempt(ip: str, scope: str = 'login'):
    now = time.time()
    key = (scope, ip)
    with _lock:
        if key not in _failed_attempts:
            _failed_attempts[key] = []
        _failed_attempts[key].append(now)

def reset_failed_attempts(ip: str, scope: str = 'login'):
    key = (scope, ip)
    with _lock:
        if key in _failed_attempts:
            del _failed_attempts[key]

# ==========================================
# PASSWORD STRENGTH VALIDATION
# ==========================================
def validate_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not any(c.isalpha() for c in password):
        return False, "Password must contain at least one letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number."
    return True, ""

# ==========================================
# PASSWORD HASHING & USER SESSION
# ==========================================
def hash_password(password: str) -> str:
    return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

def verify_password(password: str, hashed: str) -> bool:
    return check_password_hash(hashed, password)

def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role, full_name, phone, address FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return dict(user)
    return None

def is_owner():
    return session.get('role') == 'owner'

def owner_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_owner():
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Unauthorized: Owner access strictly required', 'status': 403}), 403
            return redirect(url_for('owner_login_page', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required. Please log in.', 'status': 401}), 401
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function
