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

@main.route("/student/create_booking", methods=["GET"])
@login_required(account_type="student")
def create_booking():
    return render_template("student/create_booking.html")

@main.route("/student/my_bookings", methods=["GET", "POST"])
@login_required(account_type="student")
def my_bookings():
    if request.method == "GET":
        user_id = session["user_id"]
        bookings = Bookings.query.with_entities(Bookings.id, Bookings.booking_date, Bookings.status).filter_by(student_id=user_id).all()
        return render_template("student/my_bookings.html", bookings=bookings)
    
    try:
        # Extract all form data
        student_id = session['user_id']
        subject = request.form['subject']
        booking_date = request.form['booking_date']
        booking_time = request.form['booking_time']
        price = request.form['price']
        persons_booked = request.form['persons_booked']
        description = request.form['description']

        booking = Bookings(
            student_id=student_id,
            subject=subject,
            booking_date=booking_date,
            booking_time=booking_time,
            price=price,
            persons_booked=persons_booked,
            description=description
        ) 

        db.session.add(booking)
        db.session.commit()

        return redirect("/student/my_bookings")

    except Exception as e:
        return jsonify({"error": str(e)}), 400
