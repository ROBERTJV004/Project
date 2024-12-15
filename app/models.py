from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)
    profile_picture = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    password = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    # listings = db.relationship('Listing', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'
    


class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    listing_name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Listing {self.listing_name}, ${self.price}>'

class Bookings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    coach_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    booking_date = db.Column(db.Date, nullable=False)
    booking_time = db.Column(db.Time, nullable=False)
    price = db.Column(db.Float, nullable=False, default=0.00)
    subject = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Pending')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(), onupdate=db.func.now())
    persons_booked = db.Column(db.Integer, nullable=False, default=1)

    # Relationships
    student = db.relationship('Users', foreign_keys=[student_id], backref='student_bookings')
    coach = db.relationship('Users', foreign_keys=[coach_id], backref='coach_bookings')

    def __repr__(self):
        return f'<Booking {self.id}: Student {self.student_id} with Coach {self.coach_id}>'
