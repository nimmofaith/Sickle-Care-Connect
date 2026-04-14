import os
from routes import routes
from doctor_routes import doctor_routes
from admin_routes import admin_routes
from flask import Flask, jsonify
from flask_cors import CORS
from db import db
from sqlalchemy import inspect, text
from datetime import datetime
from werkzeug.security import generate_password_hash
from models import Admin

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  #

app = Flask(__name__)
CORS(app,
     resources={
         r"/*": {
             "origins": [
                 "http://127.0.0.1:5500",
                 "http://localhost:5500",
                 "http://127.0.0.1:3000",
                 "http://localhost:3000",
                 "https://sicklecareconnect.netlify.app",
                 "https://sickle-care-connect.onrender.com"
             ]
         }
     },
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "X-Requested-With", "X-Doctor-ID"])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'sicklecare.db')}"

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# JWT Configuration
app.config['JWT_SECRET_KEY'] = os.getenv(
    'JWT_SECRET_KEY', 'your-secret-key-change-in-production')

db.init_app(app)

app.register_blueprint(routes)
app.register_blueprint(doctor_routes)
app.register_blueprint(admin_routes)


@app.errorhandler(500)
def internal_error(error):
    response = jsonify(
        {'message': 'Internal server error', 'error': str(error)})
    response.status_code = 500
    return response


with app.app_context():
    db.create_all()

    admin_name = os.getenv("ADMIN_NAME")
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if admin_name and admin_email and admin_password:
        existing_admin = Admin.query.filter_by(email=admin_email).first()
        if not existing_admin:
            hashed_password = generate_password_hash(admin_password)
            admin_user = Admin(
                name=admin_name, email=admin_email, password=hashed_password)
            db.session.add(admin_user)
            db.session.commit()
            print("Admin auto-created securely")
    else:
        print("Admin environment variables not set")

    inspector = inspect(db.engine)

    # Check and add missing columns to appointment table
    appointment_cols = [c['name']
                        for c in inspector.get_columns('appointment')]

    if 'notes' not in appointment_cols:
        db.session.execute(
            text('ALTER TABLE appointment ADD COLUMN notes TEXT'))

    if 'status' not in appointment_cols:
        db.session.execute(
            text("ALTER TABLE appointment ADD COLUMN status VARCHAR(50) DEFAULT 'pending'"))

    # Check and add missing created_at columns to other tables (SQLite compatible)
    tables_to_check = ['patient', 'doctor', 'prescription',
                       'hospital', 'medical_profile', 'consultation_note']

    for table_name in tables_to_check:
        try:
            table_cols = [c['name'] for c in inspector.get_columns(table_name)]
            if 'created_at' not in table_cols:
                # Add column without default for SQLite compatibility
                db.session.execute(
                    text(f'ALTER TABLE {table_name} ADD COLUMN created_at DATETIME'))
                # Update existing rows with current timestamp
                db.session.execute(
                    text(f"UPDATE {table_name} SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))
                print(f"Added created_at column to {table_name} table")
        except Exception as e:
            print(f"Column {table_name}.created_at: {e}")

    try:
        prescription_cols = [c['name']
                             for c in inspector.get_columns('prescription')]
        if 'refill_date' not in prescription_cols:
            db.session.execute(
                text('ALTER TABLE prescription ADD COLUMN refill_date VARCHAR(50)'))
            print("Added refill_date column to prescription table")
    except Exception as e:
        print(f"Column prescription.refill_date: {e}")

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


@app.route("/")
def home():
    return {"message": "Welcome to Sickle Care Connect API"}


if __name__ == '__main__':
    app.run(debug=True)
