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

print(f"DEBUG: DATABASE_URL from environment: {DATABASE_URL}")
print(f"DEBUG: DATABASE_URL exists: {bool(DATABASE_URL)}")

if DATABASE_URL:
    # Convert postgres:// to postgresql:// for SQLAlchemy compatibility
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        print("DEBUG: Converted postgres:// to postgresql://")
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    print(
        f"DEBUG: Using PostgreSQL database: {DATABASE_URL.replace(DATABASE_URL.split('@')[0], '***:***') if '@' in DATABASE_URL else 'No @ found'}")
else:
    print("ERROR: DATABASE_URL environment variable is not set!")
    print("ERROR: This application requires PostgreSQL and cannot fall back to SQLite in production.")
    print("ERROR: Please ensure DATABASE_URL is set in your deployment environment (Render).")
    raise RuntimeError(
        "DATABASE_URL environment variable is required but not set")

print(
    f"DEBUG: Final SQLALCHEMY_DATABASE_URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
print(
    f"DEBUG: Database engine: PostgreSQL")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# JWT Configuration
app.config['JWT_SECRET_KEY'] = os.getenv(
    'JWT_SECRET_KEY', 'your-secret-key-change-in-production')

db.init_app(app)

# Test database connection
with app.app_context():
    try:
        with db.engine.connect() as connection:
            connection.execute(text('SELECT 1'))
            print("DEBUG: Database connection successful")
    except Exception as e:
        print(f"DEBUG: Database connection failed: {e}")

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
    print("DEBUG: Starting database initialization...")

    # Check if tables already exist before creating
    inspector = inspect(db.engine)
    existing_tables = inspector.get_table_names()
    print(f"DEBUG: Existing tables before create_all: {existing_tables}")

    # Only create tables if they don't exist
    db.create_all()

    new_tables = inspector.get_table_names()
    print(f"DEBUG: Tables after create_all: {new_tables}")

    if existing_tables and existing_tables == new_tables:
        print("DEBUG: Tables already existed, no new tables created")
    else:
        print("DEBUG: New tables were created or schema was updated")

    admin_name = os.getenv("ADMIN_NAME")
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")

    print(
        f"DEBUG: Admin env vars - NAME: {admin_name}, EMAIL: {admin_email}, PASSWORD: {'***' if admin_password else None}")

    if admin_name and admin_email and admin_password:
        existing_admin = Admin.query.filter_by(email=admin_email).first()
        print(
            f"DEBUG: Existing admin check: {'Found' if existing_admin else 'Not found'}")
        if not existing_admin:
            hashed_password = generate_password_hash(admin_password)
            admin_user = Admin(
                name=admin_name, email=admin_email, password=hashed_password)
            db.session.add(admin_user)
            db.session.commit()
            print("DEBUG: Admin auto-created successfully")
        else:
            print("DEBUG: Admin already exists, skipping creation")
    else:
        print("DEBUG: Admin environment variables not set")

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
