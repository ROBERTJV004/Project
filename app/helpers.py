from functools import wraps

from flask import redirect, session, url_for

from app.models import Users


def get_db():
    return db

def login_required(f=None, *, account_type=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("login"))
            
            if account_type:
                user = Users.query.get(session["user_id"])
                if user.role != account_type:
                    return redirect("/")
                    
            return f(*args, **kwargs)
        return decorated_function
        
    if f is None:
        return decorator
    return decorator(f)

def get_account_type(username: str):
    return Users.query.filter_by(username=username).first().role
