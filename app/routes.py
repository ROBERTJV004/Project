import os
from flask import Blueprint, current_app, render_template, request, redirect, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from app.models import Bookings, Users
from project import allowed_file
from .helpers import get_account_type, login_required
from datetime import datetime
from app import db

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

@main.route("/profile", methods=["GET", "POST"])
@login_required(account_type="student") 
def profile():
    user_id = session["user_id"]

    if request.method == "POST":
        description = request.form.get("description", "")
        profile_picture = request.files.get("profile_picture")

        # Handle profile picture upload
        if profile_picture and allowed_file(profile_picture.filename):
            filename = secure_filename(str(profile_picture.filename))
            filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            profile_picture.save(filepath)

            # Update profile picture path in database
            user = Users.query.get(user_id)
            user.profile_picture = f"/static/uploads/{filename}"
            db.session.commit()

        # Update description in database
        user = Users.query.get(user_id)
        user.description = description
        db.session.commit()

        return redirect("/profile")

    # Get user data for profile page
    user = Users.query.with_entities(
        Users.username,
        Users.email, 
        Users.description,
        Users.profile_picture
    ).filter_by(id=user_id).first()

    return render_template("profile.html", user=user)

@main.route("/student/create_booking", methods=["GET"])
@login_required(account_type="student")
def create_booking():
    return render_template("student/create_booking.html")

@main.route("/student/my_bookings", methods=["GET", "POST"])
@login_required(account_type="student")
def my_bookings():
    if request.method == "GET":
        user_id = session["user_id"]
        # Only fetch bookings that haven't passed yet
        bookings = Bookings.query.with_entities(
            Bookings.id, 
            Bookings.booking_date, 
            Bookings.status
        ).filter(
            Bookings.student_id == user_id,
            (Bookings.booking_date > datetime.now().date()) |
            ((Bookings.booking_date == datetime.now().date()) & 
             (Bookings.booking_time > datetime.now().time()))
        ).order_by(Bookings.booking_date.asc(), Bookings.booking_time.asc()).all()
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

@main.route("/coach/requests", methods=["GET"])
@login_required(account_type="coach")
def coach_requests():
    try:
        # Fetch pending bookings that haven't passed yet
        bookings = [{
            'id': booking.id,
            'student_id': booking.student_id,
            'subject': booking.subject,
            'booking_date': booking.booking_date.strftime('%Y-%m-%d'),
            'booking_time': booking.booking_time.strftime('%H:%M'),
            'price': float(booking.price),
            'persons_booked': booking.persons_booked,
            'description': booking.description,
            'status': booking.status
        } for booking in Bookings.query.filter(
            Bookings.status == 'Pending',
            (Bookings.booking_date > datetime.now().date()) |
            ((Bookings.booking_date == datetime.now().date()) & 
             (Bookings.booking_time > datetime.now().time()))
        ).order_by(Bookings.booking_date.asc(), Bookings.booking_time.asc()).all()]

        return render_template("coach/requests.html", bookings=bookings)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@main.route("/coach/requests/accept", methods=["POST"])
@login_required(account_type="coach") 
def accept_request():
    try:
        booking_id = request.form.get("id")
        
        # Verify booking exists and is pending
        booking = Bookings.query.filter_by(id=booking_id, status='Pending').first()
        if not booking:
            return jsonify({"error": "Booking not found or already processed"}), 400

        # Update booking status and coach
        booking.status = 'Accepted'
        booking.coach_id = session['user_id']
        booking.updated_at = datetime.now()
        
        db.session.commit()

        return redirect("/coach/requests")

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main.route("/reviews", methods=["GET"])
@login_required
def reviews():
    try:
        user_id = session["user_id"]
        account_type = get_account_type(session["username"])
        
        # Query past bookings based on account type
        if account_type == "student":
            bookings = Bookings.query.join(
                Users, Users.id == Bookings.coach_id
            ).with_entities(
                Bookings.id,
                Bookings.booking_date,
                Bookings.booking_time,
                Bookings.subject,
                Bookings.price,
                Bookings.persons_booked,
                Bookings.description,
                Bookings.status,
                Bookings.student_review,
                Bookings.student_rating,
                Bookings.coach_review,
                Bookings.coach_rating,
                Users.username.label('coach_name')
            ).filter(
                Bookings.student_id == user_id,
                # (Bookings.booking_date < datetime.now().date()) |
                # ((Bookings.booking_date == datetime.now().date()) & 
                #  (Bookings.booking_time < datetime.now().time()))
            ).order_by(Bookings.booking_date.desc(), Bookings.booking_time.desc()).all()
        else:  # coach
            bookings = Bookings.query.join(
                Users, Users.id == Bookings.student_id
            ).with_entities(
                Bookings.id,
                Bookings.booking_date,
                Bookings.booking_time,
                Bookings.subject,
                Bookings.price,
                Bookings.persons_booked,
                Bookings.description,
                Bookings.status,
                Bookings.student_review,
                Bookings.student_rating,
                Bookings.coach_review,
                Bookings.coach_rating,
                Users.username.label('student_name')
            ).filter(
                Bookings.coach_id == user_id,
                # (Bookings.booking_date < datetime.now().date()) |
                # ((Bookings.booking_date == datetime.now().date()) & 
                #  (Bookings.booking_time < datetime.now().time()))
            ).order_by(Bookings.booking_date.desc(), Bookings.booking_time.desc()).all()

        return render_template(
            "reviews.html", 
            bookings=bookings, 
            account_type=account_type
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main.route("/submit_review", methods=["POST"])
@login_required
def submit_review():
    try:
        booking_id = request.form.get("booking_id")
        review_text = request.form.get("review_text")
        rating = request.form.get("rating")
        reviewer_type = request.form.get("reviewer_type")  # 'student' or 'coach'

        if not all([booking_id, review_text, rating, reviewer_type]):
            return jsonify({"error": "Missing required fields"}), 400

        booking = Bookings.query.get(booking_id)
        if not booking:
            return jsonify({"error": "Booking not found"}), 404

        # Verify the user has permission to review this booking
        user_id = session["user_id"]
        if reviewer_type == "student" and booking.student_id != user_id:
            return jsonify({"error": "Unauthorized"}), 403
        elif reviewer_type == "coach" and booking.coach_id != user_id:
            return jsonify({"error": "Unauthorized"}), 403

        # Update the appropriate review fields
        if reviewer_type == "student":
            booking.student_review = review_text
            booking.student_rating = rating
        else:
            booking.coach_review = review_text
            booking.coach_rating = rating

        db.session.commit()
        return jsonify({"message": "Review submitted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
