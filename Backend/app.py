# app.py for Sickle Care Connect
from routes import routes
from doctor_routes import doctor_routes
from flask import Flask, jsonify
from flask_cors import CORS
from db import db
from sqlalchemy import inspect, text
from datetime import datetime


# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sicklecare.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)

app.register_blueprint(routes)
app.register_blueprint(doctor_routes)


@app.errorhandler(500)
def internal_error(error):
    response = jsonify(
        {'message': 'Internal server error', 'error': str(error)})
    response.status_code = 500
    return response


# Create database tables if they don't exist
with app.app_context():
    db.create_all()

    inspector = inspect(db.engine)
    appointment_cols = [c['name']
                        for c in inspector.get_columns('appointment')]

    if 'notes' not in appointment_cols:
        db.session.execute(
            text('ALTER TABLE appointment ADD COLUMN notes TEXT'))

    if 'status' not in appointment_cols:
        db.session.execute(
            text("ALTER TABLE appointment ADD COLUMN status VARCHAR(50) DEFAULT 'pending'"))

    db.session.commit()

    # Clean up past canceled appointments 
    from models import Appointment, DoctorAppointment
    today_str = datetime.now().date().isoformat()

    # Delete past canceled patient appointments
    past_canceled = Appointment.query.filter(
        Appointment.status == 'cancelled',
        Appointment.preferred_date < today_str
    ).delete()

    # Delete past canceled doctor appointments
    past_canceled_doc = DoctorAppointment.query.filter(
        DoctorAppointment.status == 'cancelled',
        DoctorAppointment.appointment_date < datetime.now()
    ).delete()

    if past_canceled > 0 or past_canceled_doc > 0:
        db.session.commit()

# Home route


@app.route("/")
def home():
    return {"message": "Welcome to Sickle Care Connect API"}


# Run server
if __name__ == '__main__':
    app.run(debug=True)
