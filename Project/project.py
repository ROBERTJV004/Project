from flask import Flask, request, jsonify, render_template, current_app, redirect, url_for, session, flash
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import os
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, join_room, leave_room, send
from supabase import create_client, Client

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

SUPABASE_URL = os.getenv("SUPABASE_URL", "user=postgres.fnjdoevjrqypxezpjdzv password=qydVog-gyzkyj-qizdu9 host=aws-0-eu-central-1.pooler.supabase.com port=6543 dbname=postgres")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZuamRvZXZqcnF5cHhlenBqZHp2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzI3MDQ2MzEsImV4cCI6MjA0ODI4MDYzMX0.RB-KnY9kj4jUoUecQiPhxCV4BecKB32ZUrm1jQVPwEE")


def get_db_connection():
    try:
        conn = psycopg2.connect(SUPABASE_URL)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise e


# Serve the Homepage
@app.route('/')
def home():
    return render_template('index.html')  # Homepage with navigation links


# User Registration Page
@app.route('/register')
def register_page():
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


@app.route('/dashboard', methods=['GET'])
def dashboard():
    # Ensure the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login_page'))  # Redirect to login if not authenticated

    user_id = session['user_id']
    username = session['username']

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Fetch user-specific bookings
        cur.execute("""
            SELECT b.id, l.title, b.booking_date, b.status 
            FROM bookings b
            JOIN listings l ON b.listing_id = l.id
            WHERE b.student_id = %s OR b.coach_id = %s
        """, (user_id, user_id))
        bookings = cur.fetchall()

        # Fetch all listings created by the user
        cur.execute("""
            SELECT id, title, description, price, status 
            FROM listings
            WHERE user_id = %s
        """, (user_id,))
        listings = cur.fetchall()

        cur.close()
        conn.close()

        # Pass data to the template
        return render_template(
            'dashboard.html',
            username=username,
            bookings=bookings,
            listings=listings
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Listings Page
@app.route('/all_listings', methods=['GET'])
def all_listings():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if not authenticated
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Fetch Approved Listings (status = 'approved')
        cur.execute("SELECT * FROM listings WHERE status = 'approved'")
        approved_listings = cur.fetchall()

        # Fetch All Pending Listings (status = 'pending')
        cur.execute("SELECT * FROM listings WHERE status = 'pending'")
        all_pending_listings = cur.fetchall()

        cur.close()
        conn.close()

        # Render the template and pass both lists
        return render_template('all_listings.html', approved_listings=approved_listings, all_pending_listings=all_pending_listings)

    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 500
    
@app.route('/view_listing/<int:listing_id>', methods=['GET', 'POST'])
def view_listing(listing_id):
    # Ensure the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect if not logged in

    try:
        user_id = session['user_id']  # Get the logged-in user's ID
        conn = get_db_connection()
        cur = conn.cursor()

        # Fetch the listing details based on listing_id
        cur.execute("SELECT * FROM listings WHERE id = %s", (listing_id,))
        listing = cur.fetchone()

        if not listing:
            return "Listing not found", 404

        if request.method == 'POST':
            # Extract listing details for the `bookings` table
            student_id = listing[1]  # Assuming student_id is in the 2nd column
            subject = listing[2]  # Assuming subject is in the 3rd column
            lesson_date = listing[3]  # Assuming lesson_date is in the 4th column
            lesson_time = listing[4]  # Assuming lesson_time is in the 5th column
            price = listing[5]  # Assuming price is in the 6th column
            description = listing[6]  # Assuming description is in the 7th column

            # Insert the approved listing into the `bookings` table
            cur.execute("""
                INSERT INTO bookings (student_id, coach_id, listing_id, booking_date, booking_time, price, subject, description, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'approved')
            """, (student_id, user_id, listing[0], lesson_date, lesson_time, price, subject, description))

            # Update the status in the `listings` table
            cur.execute("""
                UPDATE listings
                SET status = 'approved'
                WHERE id = %s
            """, (listing_id,))

            # Commit the changes to the database
            conn.commit()

            cur.close()
            conn.close()

            # Redirect to a confirmation page or back to all listings
            return redirect(url_for('approval_success'))

        # Prepare the listing details for the template
        listing_dict = {
            "id": listing[0],
            "student_id": listing[1],
            "title": listing[2],
            "lesson_date": listing[3],
            "lesson_time": listing[4],
            "price": listing[5],
            "description": listing[6],
            "status": listing[7]
        }

        cur.close()
        conn.close()

        return render_template('view_listing.html', listing=listing_dict)

    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 500

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

@app.route('/my_bookings', methods=['GET', 'POST'])
def my_bookings():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect if the user is not logged in

    user_id = session['user_id']

    if request.method == 'POST':
        # Get form data for a new booking
        subject = request.form['subject']
        lesson_date = request.form['date']
        lesson_time = request.form['time']
        price = request.form['price']
        description = request.form['description']

        try:
            # Insert the new booking into the listings table (for lesson request)
            query = """
            INSERT INTO listings (user_id, title, lesson_date, lesson_time, price, description, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;
            """
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(query, (user_id, subject, lesson_date, lesson_time, price, description, 'pending'))
            booking_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            conn.close()

            # Redirect to the confirmation page or reload my bookings
            return redirect(url_for('lesson_request_confirmation'))

        except Exception as e:
            return jsonify({"error": f"An error occurred: {e}"}), 400

    try:
        # Fetch the user's bookings, showing their status (pending or approved)
        query = """
        SELECT id, title, lesson_date, lesson_time, price, status 
        FROM listings
        WHERE user_id = %s
        """
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, (user_id,))
        bookings = cur.fetchall()
        cur.close()
        conn.close()

        return render_template('my_bookings.html', bookings=bookings)

    except Exception as e:
        return jsonify({"error": f"An error occurred while fetching bookings: {e}"}), 500

@app.route('/lesson_request_confirmation', methods=['GET'])
def lesson_request_confirmation():
    return render_template('lesson_request_confirmation.html')  # Render your confirmation page


@app.route('/approve_listing/<listing_id>', methods=['POST'])
def approve_listing(listing_id):
    # Ensure the user is logged in and is a coach
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect if the user is not logged in

    coach_id = session['user_id']

    try:
        # Connect to the database
        conn = get_db_connection()
        cur = conn.cursor()

        # Check if the listing exists and is pending
        cur.execute("""
            SELECT * FROM listings
            WHERE id = %s AND status = 'pending'
        """, (listing_id,))
        listing = cur.fetchone()

        if not listing:
            return jsonify({"error": "Listing not found or already approved"}), 400

        # Step 1: Update the status of the listing to 'approved'
        cur.execute("""
            UPDATE listings
            SET status = 'approved', updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (listing_id,))
        conn.commit()

        cur.close()
        conn.close()

        # Return the success message and a button to go back to the "All Listings" page
        return render_template('approve_success.html', listing_id=listing_id)

    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 400

@app.route('/delete_listing/<listing_id>', methods=['POST'])
def delete_listing(listing_id):
    # Ensure the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect if the user is not logged in

    user_id = session['user_id']

    try:
        # Connect to the database
        conn = get_db_connection()
        cur = conn.cursor()

        # Check if the listing exists and is approved
        cur.execute("""
            SELECT * FROM listings
            WHERE id = %s AND status = 'approved'
        """, (listing_id,))
        listing = cur.fetchone()

        if not listing:
            return jsonify({"error": "Listing not found or not approved"}), 400

        # Step 1: Delete the listing from the listings table
        cur.execute("""
            DELETE FROM listings
            WHERE id = %s
        """, (listing_id,))
        conn.commit()

        cur.close()
        conn.close()

        # Redirect to the "All Listings" page
        return redirect(url_for('all_listings'))

    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 400
    

if __name__ == "__main__":
    app.run(debug=True)

