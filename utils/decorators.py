from functools import wraps
from flask import redirect, session, url_for, flash

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("access_token") or session.get("role") != "admin":
            flash("Session expired. Please login again.", "danger")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapper
