from flask import Blueprint, render_template, request, redirect, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash

from app.models import Bookings, Users
from .helpers import get_account_type, login_required, get_db
from datetime import datetime

# Create a Blueprint instead of a Flask app
main = Blueprint('main', __name__)

@main.route("/")
@login_required
def index():
    username = session["username"]
    account_type = get_account_type(username)
    
    if account_type == "coach":
        return redirect("coach")
    else:
        return redirect("student")

@main.route("/coach", methods=["GET"])
@login_required(account_type="coach")
def coach():
    user_id = session["user_id"]
    username = session["username"]
    bookings = Bookings.query.join(Users, Users.id == Bookings.student_id).filter(Bookings.coach_id == user_id).all()
    return render_template("coach.html", username=username, bookings=bookings)

@main.route("/student", methods=["GET"])
@login_required(account_type="student")
def student():
    username = session["username"]
    return render_template("student.html", username=username)

@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        
        # Ensure username was submitted
        if not username:
            return render_template("register.html", error="Must provide username")
        
        # Ensure password was submitted
        if not password:
            return render_template("register.html", error="Must provide password")
        
        # Ensure confirmation was submitted
        if not confirmation:
            return render_template("register.html", error="Must provide confirmation")
        
        # Ensure password and confirmation match
        if password != confirmation:
            return render_template("register.html", error="Passwords must match")
        
        db = get_db()
        
        # Check if username already exists
        if db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone():
            return render_template("register.html", error="Username already exists")
        
        # Insert new user into database
        db.execute(
            "INSERT INTO users (username, hash) VALUES (?, ?)",
            (username, generate_password_hash(password))
        )
        db.commit()
        
        # Redirect to login page
        return redirect("/login")
    
    return render_template("register.html")

@main.route("/login", methods=["GET", "POST"])
def login():
    # Forget any user_id
    session.clear()
    
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        # Ensure username was submitted
        if not username:
            return render_template("login.html", error="Must provide username")
        
        # Ensure password was submitted
        if not password:
            return render_template("login.html", error="Must provide password")
        
        db = get_db()
        
        # Query database for username
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        
        # Ensure username exists and password is correct
        if not user or not check_password_hash(user["hash"], password):
            return render_template("login.html", error="Invalid username and/or password")
        
        # Remember which user has logged in
        session["user_id"] = user["id"]
        
        # Redirect user to home page
        return redirect("/")
    
    return render_template("login.html")

@main.route("/logout")
def logout():
    # Forget any user_id
    session.clear()
    
    # Redirect user to login form
    return redirect("/")

@main.route("/chat", methods=["POST"])
@login_required
def chat():
    user_message = request.json.get("message")
    chat_id = request.json.get("chat_id")
    
    if not user_message:
        return jsonify({"error": "Message is required"}), 400
    
    db = get_db()
    user_id = session["user_id"]
    
    # If no chat_id, create new chat
    if not chat_id:
        chat_id = db.execute(
            "INSERT INTO chats (user_id, timestamp) VALUES (?, ?)",
            (user_id, datetime.now())
        ).lastrowid
        db.commit()
    
    # Store user message
    db.execute(
        "INSERT INTO messages (chat_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (chat_id, "user", user_message, datetime.now())
    )
    db.commit()
    
    # Get AI response
    ai_message = "This is a placeholder AI response"
    
    # Store AI response
    db.execute(
        "INSERT INTO messages (chat_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (chat_id, "assistant", ai_message, datetime.now())
    )
    db.commit()
    
    return jsonify({
        "chat_id": chat_id,
        "response": ai_message
    })

@main.route("/history/<int:chat_id>")
@login_required
def history(chat_id):
    db = get_db()
    user_id = session["user_id"]
    
    # Verify chat belongs to user
    chat = db.execute(
        "SELECT * FROM chats WHERE id = ? AND user_id = ?",
        (chat_id, user_id)
    ).fetchone()
    
    if not chat:
        return jsonify({"error": "Chat not found"}), 404
    
    # Get chat messages
    messages = db.execute(
        "SELECT role, content FROM messages WHERE chat_id = ? ORDER BY timestamp",
        (chat_id,)
    ).fetchall()
    
    return jsonify([dict(message) for message in messages]) 