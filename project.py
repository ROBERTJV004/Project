from flask import Flask, request, jsonify, render_template, current_app, redirect, url_for, session
import psycopg2
from psycopg2 import extras
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import os
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, join_room, leave_room, send

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Initialize Flask App
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a secure secret key
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Database Connection
DATABASE_URL = os.getenv("SUPABASE_DATABASE_URL",
                         "postgresql://postgres.fnjdoevjrqypxezpjdzv:qydVog-gyzkyj-qizdu9@aws-0-eu-central-1.pooler.supabase.com:6543/postgres")


def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise e


# Serve the Homepage
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect("dashboard")
    return render_template('index.html')  # Homepage with navigation links


# User Registration Page
@app.route('/register')
def register_page():
    if 'user_id' in session:
        return redirect("dashboard")
    return render_template('register.html')  # HTML form for user registration


# Handle User Registration (POST API)
from werkzeug.security import generate_password_hash


@app.route('/users', methods=['POST'])
def create_user():
    try:
        # Retrieve form data
        username = request.form.get('username')
        email = request.form.get('email')
        role = request.form.get('role')
        password = generate_password_hash(request.form.get('password'))  # Hash the password

        if not username or not email or not role or not password:
            return jsonify({"error": "Missing required fields"}), 400

        query = """
        INSERT INTO users (username, email, role, password)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
        """
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, (username, email, role, password))
        user_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        # Store the user in the session
        session['user_id'] = user_id
        session['username'] = username

        # Redirect to the dashboard
        return redirect(url_for('dashboard'))

    except Exception as e:
        return render_template('register.html', error=str(e))


@app.route('/login', methods=['GET'])
def login_page():
    if 'user_id' in session:
        return redirect("dashboard")
    return render_template('login.html')  # Renders the login form


# Handle User Login (POST API)
from werkzeug.security import check_password_hash

from flask import redirect, url_for, session


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            # Extract form data
            email = request.form['email']  # Use request.form for HTML form submissions
            password = request.form['password']

            # Query the database for the user
            query = "SELECT id, username, password FROM users WHERE email = %s"
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(query, (email,))
            user = cur.fetchone()
            cur.close()
            conn.close()

            # Check if user exists
            if not user:
                error = "Invalid email or password"
                return render_template('login.html', error=error)

            user_id, username, hashed_password = user

            # Verify password
            if not check_password_hash(hashed_password, password):
                error = "Invalid email or password"
                return render_template('login.html', error=error)

            # Save user details in session
            session['user_id'] = user_id
            session['username'] = username

            # Redirect to the dashboard
            return redirect(url_for('dashboard'))

        except Exception as e:
            error = f"An error occurred: {e}"
            return render_template('login.html', error=error)

    # Render the login page for GET request
    return render_template('login.html')


@app.route('/logout', methods=['GET'])
def logout():
    # Clear the session data
    session.clear()
    # Redirect the user to the login page
    return redirect(url_for('login_page'))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Profile route
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    if request.method == 'POST':
        description = request.form.get('description', '')
        profile_picture = request.files.get('profile_picture')

        # Handle profile picture upload
        if profile_picture and allowed_file(profile_picture.filename):
            filename = secure_filename(profile_picture.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            profile_picture.save(filepath)

            # Update the profile picture in the database
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET profile_picture = %s WHERE id = %s",
                (f"/static/uploads/{filename}", user_id)
            )
            conn.commit()
            cur.close()
            conn.close()

        # Update the description in the database
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET description = %s WHERE id = %s",
            (description, user_id)
        )
        conn.commit()
        cur.close()
        conn.close()

        # Redirect back to the profile page
        return redirect(url_for('profile'))

    # Fetch updated user data to render on the profile page
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT username, email, description, profile_picture FROM users WHERE id = %s",
        (user_id,)
    )
    user = cur.fetchone()
    cur.close()
    conn.close()

    return render_template('profile.html', user=user)

def get_user_type(username):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT role FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        return user[0]
    except Exception as e:
        print(e)
        return "student"


@app.route('/student', methods=['GET'])
def student():
    # Ensure the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login_page'))  # Redirect to login if not authenticated

    user_id = session['user_id']
    username = session['username']

    user_type = get_user_type(username)
    if user_type == "coach":
        return redirect("/coach")

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Fetch user-specific bookings
        cur.execute("""
            SELECT b.id, b.booking_date, b.status 
            FROM bookings b
            WHERE b.student_id = %s
        """, (user_id,))
        bookings = cur.fetchall()

        cur.close()
        conn.close()

        # Pass data to the template
        return render_template(
            'dashboard.html',
            username=username,
            bookings=bookings,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/coach', methods=['GET'])
def coach():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))

    user_id = session['user_id']
    username = session['username']

    user_type = get_user_type(username)
    if user_type == "student":
        return redirect("/student")

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Modified query to join with users table
        cur.execute("""
            SELECT b.*, u.email as student_email
            FROM bookings b
            LEFT JOIN users u ON b.student_id = u.id
            WHERE b.coach_id = %s
        """, (user_id,))
        bookings = cur.fetchall()

        cur.close()
        conn.close()

        return render_template(
            'coach.html',
            username=username,
            bookings=bookings,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/coach/requests', methods=['GET'])
def coach_requests():
    # Ensure the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login_page'))  # Redirect to login if not authenticated

    user_id = session['user_id']
    username = session['username']

    user_type = get_user_type(username)
    if user_type == "student":
        return redirect("/student")

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Fetch user-specific bookings
        cur.execute("""
            SELECT *
            FROM bookings
            WHERE status = 'Pending'
            AND (booking_date > CURRENT_DATE 
                OR (booking_date = CURRENT_DATE AND booking_time > CURRENT_TIME))
            ORDER BY booking_date ASC, booking_time ASC;
        """, ())

        bookings = cur.fetchall()

        cur.close()
        conn.close()

        # Pass data to the template
        return render_template(
            'coach/requests.html',
            bookings=bookings,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Listings Page
@app.route('/listings', methods=['GET'])
def view_listings_page():
    query = "SELECT * FROM listings WHERE status = 'active';"
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        listings = [
            {
                "id": row[0],
                "user_id": row[1],
                "title": row[2],
                "description": row[3],
                "price": float(row[4]),
                "status": row[5],
                "created_at": row[6]
            }
            for row in rows
        ]
        return render_template('listings.html', listings=listings)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Create a Listing Page
@app.route('/create_listing')
def create_listing_page():
    return render_template('create_listing.html')  # HTML form for creating a listing


# API to Create a Listing
@app.route('/listings', methods=['POST'])
def create_listing():
    try:
        data = request.form
        query = """
        INSERT INTO listings (user_id, title, description, price, status)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id;
        """
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, (
            int(data['user_id']),  # Convert user_id to INT
            data['title'],
            data['description'],
            float(data['price']),  # Ensure price is a float
            data.get('status', 'draft')  # Default to 'draft' if status is not provided
        ))
        listing_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"id": listing_id, "message": "Listing created successfully!"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Reviews Page
@app.route('/reviews')
def reviews_page():
    return render_template('reviews.html')  # HTML form for adding reviews


# API to Add a Review
@app.route('/reviews', methods=['POST'])
def add_review():
    try:
        data = request.json
        booking_id = int(data['booking_id'])
        rating = int(data['rating'])
        review = data.get('review', '')

        query = """
        INSERT INTO reviews (booking_id, rating, review)
        VALUES (%s, %s, %s)
        RETURNING id;
        """
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, (booking_id, rating, review))
        review_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"id": review_id, "message": "Review added successfully!"}), 201

    except KeyError as e:
        return jsonify({"error": f"Missing field: {e}"}), 400
    except ValueError as e:
        return jsonify({"error": f"Invalid input: {e}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/my_bookings', methods=['GET'])
def my_bookings():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if not authenticated

    user_id = session['user_id']
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Fetch user's bookings
        query = """
        SELECT b.id, b.booking_date, b.status
        FROM bookings b
        WHERE b.student_id = %s
        """
        cur.execute(query, (user_id,))
        bookings = cur.fetchall()

        cur.close()
        conn.close()

        return render_template('my_bookings.html', bookings=bookings)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Route to display the booking creation form and create a booking
@app.route('/create_booking', methods=['GET', 'POST'])
def create_booking():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            # Extract all form data
            student_id = session['user_id']
            subject = request.form['subject']
            booking_date = request.form['booking_date']
            booking_time = request.form['booking_time']
            price = request.form['price']
            persons_booked = request.form['persons_booked']
            description = request.form['description']

            conn = get_db_connection()
            cur = conn.cursor()
            
            # Insert the booking with all required fields
            cur.execute("""
            INSERT INTO bookings (
                student_id, booking_date, booking_time, 
                price, subject, description, status, 
                persons_booked
            ) VALUES (
                %s, %s, %s, %s, %s, %s, 'Pending', %s
            )
            """, (
                student_id, booking_date, booking_time,
                price, subject, description,
                persons_booked
            ))
            
            conn.commit()
            cur.close()
            conn.close()

            return redirect(url_for('my_bookings'))

        except Exception as e:
            return jsonify({"error": str(e)}), 400

    return render_template('create_booking.html')


@app.route('/booking/accept', methods=['POST'])
def accept_booking():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))

    user_id = session['user_id']
    booking_id = request.form.get('id')

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # First verify this coach has permission to accept this booking
        cur.execute("""
            SELECT status 
            FROM bookings 
            WHERE id = %s AND status = 'Pending'
        """, (booking_id,))
        
        booking = cur.fetchone()
        if not booking:
            return jsonify({"error": "Booking not found or already processed"}), 400

        # Update the booking status to Accepted
        cur.execute("""
            UPDATE bookings 
            SET status = 'Accepted', 
                coach_id = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (user_id, booking_id))

        conn.commit()
        cur.close()
        conn.close()

        # Redirect back to the requests page
        return redirect(url_for('coach_requests'))

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)

