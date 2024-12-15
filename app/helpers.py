from functools import wraps
import os

from flask import redirect, session, url_for

from app.models import Users

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f=None, *, account_type=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get("user_id"):
                return redirect("/login")
            
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
