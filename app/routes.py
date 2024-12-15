from flask import Blueprint, render_template, request, redirect, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash

from app.models import Bookings, Users
from .helpers import get_account_type, login_required
from datetime import datetime
from app import db

# Create a Blueprint instead of a Flask app
main = Blueprint('main', __name__)

@main.route("/")
def index():
    if 'user_id' in session:
        username = session["username"]
        account_type = get_account_type(username)
        
        if account_type == "coach":
            return redirect("coach")
        else:
            return redirect("student")
    return render_template("index.html")

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

@main.route("/register", methods=["GET"])
def register_page():
    if 'user_id' in session:
        return redirect("/")
    return render_template('register.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if 'user_id' in session:
            return redirect("/")
        
        if request.method == 'GET':
            return render_template('login.html')
        
        email = request.form['email']
        password = request.form['password']

        user = Users.query.filter_by(email=email).first()

        if not user:
            error = "Invalid email or password"
            return render_template('login.html', error=error)

        if not check_password_hash(user.password, password):
            error = "Invalid email or password"
            return render_template('login.html', error=error)

        session['user_id'] = user.id
        session['username'] = user.username

        return redirect("/")

    except Exception as e:
        error = f"An error occurred: {e}"
        return render_template('login.html', error=error)

@main.route('/users', methods=['POST'])
def create_user():
    try:
        username = request.form.get('username')
        email = request.form.get('email')
        role = request.form.get('role')
        password = generate_password_hash(request.form.get('password'))

        if not username or not email or not role or not password:
            return jsonify({"error": "Missing required fields"}), 400

        # Create new user instance
        new_user = Users(
            username=username,
            email=email,
            role=role,
            password=password
        )

        # Add to database and commit
        db.session.add(new_user)
        db.session.commit()

        # Get the user that was just created
        user = Users.query.filter_by(username=username).first()

        session['user_id'] = user.id
        session['username'] = username

        return redirect("/")

    except Exception as e:
        return render_template('register.html', error="Failed to create account")

@main.route("/logout")
def logout():
    session.clear()
    
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