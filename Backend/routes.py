from datetime import date, datetime
from flask import Blueprint, request, jsonify
from db import db
from sqlalchemy import inspect, text
from models import Admin, Patient, Appointment, Medication, MedicalProfile, Doctor, DoctorPatient, DoctorAppointment, Hospital, Prescription
from werkzeug.security import generate_password_hash, check_password_hash
from jwt_utils import generate_token, verify_token, extract_token_from_header
import re

routes = Blueprint("routes", __name__)
# ------------------------------
# User Routes
# ------------------------------


def ensure_appointment_notes_column():
    inspector = inspect(db.engine)
    cols = [c['name'] for c in inspector.get_columns('appointment')]
    if 'notes' not in cols:
        db.session.execute(
            text('ALTER TABLE appointment ADD COLUMN notes TEXT'))
        db.session.commit()


def validate_password(password):
    """Validate password against security requirements"""
    # Common passwords to reject
    common_passwords = [
        "password", "12345678", "qwerty", "abc123", "password123",
        "admin", "letmein", "welcome", "monkey", "123456789",
        "iloveyou", "princess", "rockyou", "1234567", "1234567890",
        "password1", "123123", "football", "baseball", "welcome1"
    ]

    if password.lower() in common_passwords:
        return False, "Password is too common. Please choose a more unique password."

    if len(password) < 8:
        return False, "Password must be at least 8 characters long."

    if not re.search(r'[A-Z]', password):
        return False, "Password must include at least one uppercase letter."

    if not re.search(r'[a-z]', password):
        return False, "Password must include at least one lowercase letter."

    if not re.search(r'[0-9]', password):
        return False, "Password must include at least one number."

    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
        return False, "Password must include at least one special character (e.g. !@#$%^&*)."

    return True, "Password is valid."


def require_patient():
    if request.method == 'OPTIONS':
        return None, jsonify({}), 200  # Allow preflight OPTIONS

    token = extract_token_from_header()
    if not token:
        return None, jsonify({"message": "Authorization header required"}), 401

    payload, error = verify_token(token)
    if error:
        return None, jsonify({"message": error}), 401

    # Check if user type is patient
    if payload.get('user_type') != 'patient':
        return None, jsonify({"message": "Invalid credentials or insufficient permissions"}), 401

    # Fetch the patient from database
    patient = Patient.query.get(payload.get('user_id'))
    if not patient:
        return None, jsonify({"message": "Patient not found"}), 401

    return patient, None, None


def require_admin():
    if request.method == 'OPTIONS':
        return None, jsonify({}), 200  # Allow preflight OPTIONS

    token = extract_token_from_header()
    if not token:
        return None, jsonify({"message": "Authorization header required"}), 401

    payload, error = verify_token(token)
    if error:
        return None, jsonify({"message": error}), 401

    # Check if user type is admin
    if payload.get('user_type') != 'admin':
        return None, jsonify({"message": "Invalid credentials or insufficient permissions"}), 401

    # Fetch the admin from database
    admin = Admin.query.get(payload.get('user_id'))
    if not admin:
        return None, jsonify({"message": "Admin not found"}), 401

    return admin, None, None

# Signup route


@routes.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"message": "Invalid JSON payload"}), 400

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    confirm_password = data.get("confirm_password")

    if not name or not email or not password or not confirm_password:
        return jsonify({"message": "All fields are required"}), 400

    if password != confirm_password:
        return jsonify({"message": "Passwords do not match"}), 400

    # Validate password requirements
    is_valid, message = validate_password(password)
    if not is_valid:
        return jsonify({"message": message}), 400

    if Patient.query.filter_by(email=email).first():
        return jsonify({"message": "User already exists"}), 400

    hashed_password = generate_password_hash(password)
    new_user = Patient(name=name, email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User created successfully"}), 201

# Login route


@routes.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for debugging"""
    try:
        # Test database connectivity
        db.session.execute(text('SELECT 1'))
        patient_count = Patient.query.count()
        admin_count = Admin.query.count()
        doctor_count = Doctor.query.count()

        return jsonify({
            "status": "healthy",
            "database": "connected",
            "patients": patient_count,
            "admins": admin_count,
            "doctors": doctor_count
        }), 200
    except Exception as e:
        print(f"DEBUG: Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }), 500


@routes.route("/login", methods=["POST", "OPTIONS"])
def login():
    if request.method == 'OPTIONS':
        return ('', 204)

    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            print(f"DEBUG: Invalid JSON payload received")
            return jsonify({"message": "Invalid JSON payload"}), 400

        email = data.get("email", "").strip()
        password = data.get("password", "")

        if not email or not password:
            print(f"DEBUG: Missing email or password")
            return jsonify({"message": "Email and password are required"}), 400

        print(f"DEBUG: Login attempt for email: {email}")

        # Query user
        user = Patient.query.filter_by(email=email).first()
        if not user:
            print(f"DEBUG: User not found for email: {email}")
            print(
                f"DEBUG: Total patients in database: {Patient.query.count()}")
            return jsonify({"message": "Invalid email or password"}), 401

        print(f"DEBUG: User found: {user.name} (ID: {user.id})")

        # Check password
        password_matches = check_password_hash(user.password, password)
        print(f"DEBUG: Password verification result: {password_matches}")

        if not password_matches:
            print(f"DEBUG: Password mismatch for user: {email}")
            return jsonify({"message": "Invalid email or password"}), 401

        # Generate JWT token
        print(f"DEBUG: Generating token for user: {user.id}")
        token = generate_token(user.id, 'patient', user.email)
        print(f"DEBUG: Token generated successfully")

        return jsonify({
            "message": f"Welcome {user.name}!",
            "patient_id": user.id,
            "token": token
        }), 200
    except Exception as e:
        print(f"DEBUG: Login error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"message": f"Server error: {str(e)}"}), 500


@routes.route("/doctor/register", methods=["POST"])
def doctor_register():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"message": "Invalid JSON payload"}), 400

    email = data.get("email")
    password = data.get("password")
    confirm_password = data.get("confirm_password")

    if not email or not password or not confirm_password:
        return jsonify({"message": "Email and password are required"}), 400

    if password != confirm_password:
        return jsonify({"message": "Passwords do not match"}), 400

    # Validate password requirements
    is_valid, message = validate_password(password)
    if not is_valid:
        return jsonify({"message": message}), 400

    doctor = Doctor.query.filter_by(email=email).first()
    if not doctor:
        return jsonify({"message": "Doctor not found. Please contact admin to be added first."}), 404

    if doctor.password:
        return jsonify({"message": "Account already exists"}), 400

    hashed_password = generate_password_hash(password)
    doctor.password = hashed_password
    db.session.commit()

    return jsonify({"message": "Doctor account created successfully"}), 201


@routes.route('/users', methods=['GET'])
def get_all_users():
    admin, error, status = require_admin()
    if error:
        return error, status

    users = Patient.query.all()

    result = []
    for u in users:
        phone = None
        if u.appointments and len(u.appointments) > 0:
            phone = u.appointments[0].phone

        result.append({
            'id': u.id,
            'name': u.name,
            'email': u.email,
            'phone': phone
        })

    return jsonify(result), 200


# ------------------------------
# Appointment Routes
# ------------------------------

@routes.route("/appointments", methods=["POST", "OPTIONS"])
def create_appointment():
    if request.method == 'OPTIONS':
        return ('', 204)
    ensure_appointment_notes_column()
    patient, error, status = require_patient()
    if error:
        return error, status

    data = request.get_json()

    try:
        patient_id = data.get("patient_id")
        if not patient_id or int(patient_id) != patient.id:
            return jsonify({"message": "Patient ID mismatch or unauthorized"}), 403

        full_name = data.get("full_name")
        phone = data.get("phone")
        email = data.get("email")
        hospital = data.get("hospital")
        doctor = data.get("doctor")
        doctor_id = data.get("doctor_id")
        preferred_date = data.get("preferred_date")
        preferred_time = data.get("preferred_time")

        if not patient_id:
            return jsonify({"message": "Patient ID required"}), 400
        if not full_name or not full_name.strip():
            return jsonify({"message": "Full name required"}), 400
        if not phone or not phone.strip():
            return jsonify({"message": "Phone required"}), 400
        if not email or not email.strip():
            return jsonify({"message": "Email required"}), 400
        if not hospital or not hospital.strip():
            return jsonify({"message": "Hospital required"}), 400
        if not doctor or not doctor.strip():
            return jsonify({"message": "Doctor required"}), 400
        if not preferred_date:
            return jsonify({"message": "Date required"}), 400
        if not preferred_time:
            return jsonify({"message": "Time required"}), 400
        if not doctor_id:
            return jsonify({"message": "Doctor ID required"}), 400

        from datetime import date, datetime as dt
        try:
            pref_date_obj = dt.strptime(preferred_date, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"message": "Invalid preferred_date format"}), 400

        today = date.today()
        if pref_date_obj < today:
            return jsonify({"message": "Preferred appointment date cannot be in the past"}), 400

        new_appointment = Appointment(
            patient_id=int(patient_id),
            full_name=full_name.strip(),
            phone=phone.strip(),
            email=email.strip(),
            hospital=hospital.strip(),
            doctor=doctor.strip(),
            preferred_date=preferred_date,
            preferred_time=preferred_time,
            status='pending'
        )

        db.session.add(new_appointment)
        db.session.flush()

        doctor_obj = Doctor.query.get(int(doctor_id))

        if doctor_obj:
            new_appointment.doctor_id = doctor_obj.id

            existing_assignment = DoctorPatient.query.filter_by(
                doctor_id=doctor_obj.id,
                patient_id=int(patient_id)
            ).first()

            if not existing_assignment:
                doctor_patient = DoctorPatient(
                    doctor_id=doctor_obj.id,
                    patient_id=int(patient_id)
                )
                db.session.add(doctor_patient)

            from datetime import datetime as dt
            apt_datetime = dt.strptime(
                f"{preferred_date} {preferred_time}", "%Y-%m-%d %H:%M")

            doctor_appointment = DoctorAppointment(
                doctor_id=doctor_obj.id,
                patient_id=int(patient_id),
                appointment_date=apt_datetime,
                status='pending',
                reason=f"Appointment with {doctor_obj.name}"
            )
            db.session.add(doctor_appointment)

        db.session.commit()

        return jsonify({"message": "Appointment confirmed"}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Server error: {str(e)}"}), 500

# Get all appointments for a user


@routes.route("/appointments/<int:patient_id>", methods=["GET", "OPTIONS"])
def get_appointments(patient_id):
    patient, error, status = require_patient()
    if error:
        return error, status
    if patient.id != patient_id:
        return jsonify({"message": "Unauthorized access"}), 403

    appointments = Appointment.query.filter_by(patient_id=patient_id).all()
    result = [
        {
            "id": a.id,
            "full_name": a.full_name,
            "phone": a.phone,
            "email": a.email,
            "hospital": a.hospital,
            "doctor": a.doctor,
            "preferred_date": a.preferred_date,
            "preferred_time": a.preferred_time,
            "status": a.status,
            "notes": a.notes if hasattr(a, 'notes') else ""
        }
        for a in appointments
    ]
    return jsonify(result), 200


# Cancel appointment
@routes.route("/appointments", methods=["DELETE"])
def cancel_appointment():
    patient, error, status = require_patient()
    if error:
        return error, status

    data = request.get_json() or {}
    appointment_id = data.get("appointment_id")
    if not appointment_id:
        return jsonify({"message": "appointment_id is required"}), 400

    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        return jsonify({"message": "Appointment not found"}), 404

    if appointment.patient_id != patient.id:
        return jsonify({"message": "Unauthorized access"}), 403

    appointment.status = 'cancelled'
    appointment.notes = 'Cancelled by patient'
    db.session.add(appointment)

    if appointment.doctor_id:
        from datetime import datetime as dt, timedelta
        try:
            apt_datetime = dt.strptime(
                f"{appointment.preferred_date} {appointment.preferred_time}",
                "%Y-%m-%d %H:%M"
            )
            doctor_appointments = DoctorAppointment.query.filter_by(
                doctor_id=appointment.doctor_id,
                patient_id=appointment.patient_id
            ).order_by(DoctorAppointment.appointment_date.desc()).all()

            best_match = None
            best_diff = timedelta(hours=24)  # Within 24 hours

            for da in doctor_appointments:
                if da.appointment_date:
                    diff = abs(
                        (da.appointment_date - apt_datetime).total_seconds())
                    if diff < best_diff.total_seconds():
                        best_match = da
                        best_diff = timedelta(seconds=diff)

            if best_match:
                best_match.status = 'cancelled'
                best_match.notes = 'Cancelled by patient'
                db.session.add(best_match)

                approved_existing = DoctorAppointment.query.filter_by(
                    doctor_id=appointment.doctor_id,
                    patient_id=appointment.patient_id,
                    status='approved'
                ).first()

                if not approved_existing:
                    doctor_patient_link = DoctorPatient.query.filter_by(
                        doctor_id=appointment.doctor_id,
                        patient_id=appointment.patient_id
                    ).first()
                    if doctor_patient_link:
                        db.session.delete(doctor_patient_link)
        except Exception as e:
            pass  # If matching fails, continue without updating doctor appointment
    else:
        from datetime import datetime as dt, timedelta
        try:
            apt_datetime = dt.strptime(
                f"{appointment.preferred_date} {appointment.preferred_time}",
                "%Y-%m-%d %H:%M"
            )
            doctor_appointments = DoctorAppointment.query.filter_by(
                patient_id=appointment.patient_id
            ).all()

            for da in doctor_appointments:
                # Within 1 hour
                if da.appointment_date and abs((da.appointment_date - apt_datetime).total_seconds()) < 3600:
                    da.status = 'cancelled'
                    da.notes = 'Cancelled by patient'
                    db.session.add(da)
                    break
        except Exception as e:
            pass  # If matching fails, continue without updating doctor appointment

    db.session.commit()
    return jsonify({"message": "Appointment cancelled successfully"}), 200


def complete_past_approved_appointments(patient_id):
    today = date.today().isoformat()
    past_approved = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.preferred_date < today,
        Appointment.status == 'approved'
    ).all()

    for appt in past_approved:
        appt.status = 'completed'
        appt.notes = appt.notes or 'Marked complete after appointment date'
        db.session.add(appt)
        if appt.doctor_id:
            from datetime import datetime as dt, timedelta
            try:
                apt_datetime = dt.strptime(
                    f"{appt.preferred_date} {appt.preferred_time}",
                    "%Y-%m-%d %H:%M"
                )
                doctor_appointments = DoctorAppointment.query.filter_by(
                    doctor_id=appt.doctor_id,
                    patient_id=appt.patient_id,
                    status='approved'
                ).order_by(DoctorAppointment.appointment_date.desc()).all()

                best_match = None
                best_diff = timedelta(hours=24)  # Within 24 hours

                for da in doctor_appointments:
                    if da.appointment_date:
                        diff = abs(
                            (da.appointment_date - apt_datetime).total_seconds())
                        if diff < best_diff.total_seconds():
                            best_match = da
                            best_diff = timedelta(seconds=diff)

                if best_match:
                    best_match.status = 'completed'
                    best_match.notes = best_match.notes or 'Marked complete after appointment date'
                    db.session.add(best_match)
            except Exception as e:
                pass  # If matching fails, continue without updating doctor appointment

    if past_approved:
        db.session.commit()


@routes.route('/appointments/upcoming/<int:patient_id>', methods=['GET', 'OPTIONS'])
def get_upcoming(patient_id):
    patient, error, status = require_patient()
    if error:
        return error, status
    if patient.id != patient_id:
        return jsonify({"message": "Unauthorized access"}), 403

    complete_past_approved_appointments(patient_id)

    today = date.today().isoformat()

    appointments = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.preferred_date >= today,
        Appointment.status.notin_(['cancelled', 'completed'])
    ).order_by(Appointment.preferred_date).all()

    result = []
    for a in appointments:
        status = a.status or 'pending'
        notes = a.notes or ''

        result.append({
            "id": a.id,
            "full_name": a.full_name,
            "phone": a.phone,
            "email": a.email,
            "hospital": a.hospital,
            "doctor": a.doctor,
            "doctor_id": a.doctor_id,
            "preferred_date": a.preferred_date,
            "preferred_time": a.preferred_time,
            "status": status,
            "notes": notes
        })

    return jsonify(result)
# ------------------------------
# Past Appointments
# ------------------------------


@routes.route('/appointments/past/<int:patient_id>', methods=['GET', 'OPTIONS'])
def get_past(patient_id):
    patient, error, status = require_patient()
    if error:
        return error, status
    if patient.id != patient_id:
        return jsonify({"message": "Unauthorized access"}), 403

    appointments = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.status == 'completed'
    ).order_by(Appointment.preferred_date.desc()).all()

    return jsonify([
        {
            "id": a.id,
            "full_name": a.full_name,
            "phone": a.phone,
            "email": a.email,
            "hospital": a.hospital,
            "doctor": a.doctor,
            "preferred_date": a.preferred_date,
            "preferred_time": a.preferred_time
        }
        for a in appointments
    ])


@routes.route('/appointments/complete-past/<int:patient_id>', methods=['PATCH', 'OPTIONS'])
def complete_past_appointments(patient_id):
    patient, error, status = require_patient()
    if error:
        return error, status
    if patient.id != patient_id:
        return jsonify({"message": "Unauthorized access"}), 403

    complete_past_approved_appointments(patient_id)
    return jsonify({"message": "Past approved appointments marked completed"}), 200


# Clear all appointments for a patient
@routes.route('/appointments/clear/<int:patient_id>', methods=['DELETE', 'OPTIONS'])
def clear_all_appointments(patient_id):
    """Clear all appointments (upcoming and history) for a patient"""
    patient, error, status = require_patient()
    if error:
        return error, status
    if patient.id != patient_id:
        return jsonify({"message": "Unauthorized access"}), 403

    try:
        # Delete all appointments for this patient
        appointments = Appointment.query.filter_by(patient_id=patient_id).all()
        count = len(appointments)

        for appointment in appointments:
            db.session.delete(appointment)

        # Also clear any related doctor appointments
        doctor_appointments = DoctorAppointment.query.filter_by(
            patient_id=patient_id).all()
        for doc_apt in doctor_appointments:
            db.session.delete(doc_apt)

        db.session.commit()

        return jsonify({
            "message": f"Successfully cleared {count} appointments",
            "cleared_count": count
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Error clearing appointments: {str(e)}"}), 500


# ------------------------------
# Public Hospitals Route
# ------------------------------
@routes.route('/hospitals', methods=['GET'])
def get_public_hospitals():
    """Get all hospitals for public access (find care page)"""
    search = request.args.get('search', '')
    hospitals = Hospital.query.filter(
        Hospital.name.contains(search) |
        Hospital.city.contains(search) |
        Hospital.location.contains(search) |
        Hospital.service.contains(search)
    ).all()

    result = []
    for h in hospitals:
        # Get doctors for this hospital
        doctors = Doctor.query.filter_by(hospital_id=h.id).all()
        doctor_list = []
        first_doctor_id = None
        for d in doctors:
            doctor_list.append(f"Dr. {d.name}")
            if not first_doctor_id:
                first_doctor_id = d.id

        result.append({
            "id": h.id,
            "name": h.name,
            "city": h.city,
            "location": h.location,
            "service": h.service,
            "notes": h.notes,
            "doctors": doctor_list,
            "first_doctor_id": first_doctor_id
        })

    return jsonify(result)


# ------------------------------
# Medication Routes
# ------------------------------


@routes.route('/medications', methods=['POST', 'OPTIONS'])
def add_medication():
    """Patients cannot add their own medications - only doctors can via prescriptions"""
    if request.method == 'OPTIONS':
        return ('', 204)

    return jsonify({"message": "Patients cannot add medications. Please consult your doctor for prescriptions."}), 403

# Get medications for patient


@routes.route('/medications/<int:patient_id>', methods=['GET'])
def get_medications(patient_id):
    patient, error, status = require_patient()
    if error:
        return error, status
    if patient.id != patient_id:
        return jsonify({"message": "Unauthorized access"}), 403

    meds = Medication.query.filter_by(
        patient_id=patient_id, prescribed_by_doctor=True).all()

    return jsonify([
        {
            "id": m.id,
            "medication_name": m.medication_name,
            "dosage": m.dosage,
            "frequency": m.frequency,
            "refill_date": m.refill_date,
            "doctor_id": m.doctor_id
        }
        for m in meds
    ])


# Get prescriptions for patient (including notes from doctor)
@routes.route('/prescriptions/<int:patient_id>', methods=['GET'])
def get_prescriptions(patient_id):
    patient, error, status = require_patient()
    if error:
        return error, status
    if patient.id != patient_id:
        return jsonify({"message": "Unauthorized access"}), 403

    prescriptions = Prescription.query.filter_by(patient_id=patient_id).all()

    return jsonify([
        {
            "id": p.id,
            "medication_name": p.medication_name,
            "dosage": p.dosage,
            "frequency": p.frequency,
            "duration": p.duration,
            "refill_date": p.refill_date,
            "start_date": p.start_date.isoformat() if p.start_date else None,
            "end_date": p.end_date.isoformat() if p.end_date else None,
            "notes": p.notes,
            "status": p.status,
            "doctor_id": p.doctor_id
        }
        for p in prescriptions
    ])


# Delete medication
@routes.route('/medications/<int:medication_id>', methods=['DELETE'])
def delete_medication(medication_id):
    patient, error, status = require_patient()
    if error:
        return error, status

    med = Medication.query.get(medication_id)
    if not med:
        return jsonify({"message": "Medication not found"}), 404

    if med.patient_id != patient.id:
        return jsonify({"message": "Unauthorized access"}), 403

    db.session.delete(med)
    db.session.commit()
    return jsonify({"message": "Medication removed successfully"}), 200


# -------------------------------
# Medical Profile Routes
# -------------------------------


@routes.route('/profile', methods=['POST', 'OPTIONS'])
def save_profile():
    if request.method == 'OPTIONS':
        return ('', 204)

    patient, error, status = require_patient()
    if error:
        return error, status

    try:
        data = request.json

        if not data.get('patient_id'):
            return jsonify({"message": "Patient ID required"}), 400

        if int(data['patient_id']) != patient.id:
            return jsonify({"message": "Unauthorized access"}), 403

        profile = MedicalProfile.query.filter_by(
            patient_id=data['patient_id']).first()

        if profile:
            profile.genotype = data.get('genotype')
            profile.blood_type = data.get('blood_type')
            profile.allergies = data.get('allergies')
            profile.complications = data.get('complications')
        else:
            profile = MedicalProfile(
                patient_id=int(data['patient_id']),
                genotype=data.get('genotype'),
                blood_type=data.get('blood_type'),
                allergies=data.get('allergies'),
                complications=data.get('complications')
            )
            db.session.add(profile)

        db.session.commit()
        return jsonify({"message": "Profile saved"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Error saving profile: {str(e)}"}), 500


@routes.route('/profile/<int:patient_id>')
def get_profile(patient_id):
    patient, error, status = require_patient()
    if error:
        return error, status
    if patient.id != patient_id:
        return jsonify({"message": "Unauthorized access"}), 403

    profile = MedicalProfile.query.filter_by(patient_id=patient_id).first()

    if not patient:
        return jsonify({}), 404

    return jsonify({
        "patient_id": patient.id,
        "name": patient.name,
        "email": patient.email,
        "genotype": profile.genotype if profile else None,
        "blood_type": profile.blood_type if profile else None,
        "allergies": profile.allergies if profile else None,
        "complications": profile.complications if profile else None
    })


@routes.route('/profile/password', methods=['PUT'])
def change_password():
    patient, error, status = require_patient()
    if error:
        return error, status

    data = request.get_json() or {}
    patient_id = data.get('patient_id')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')

    if not patient_id or not new_password or not confirm_password:
        return jsonify({'message': 'Patient ID, new password, and confirmation are required'}), 400

    if int(patient_id) != patient.id:
        return jsonify({"message": "Unauthorized access"}), 403

    if new_password != confirm_password:
        return jsonify({'message': 'Passwords do not match'}), 400

    # Validate new password requirements
    is_valid, message = validate_password(new_password)
    if not is_valid:
        return jsonify({"message": message}), 400

    patient.password = generate_password_hash(new_password)
    db.session.commit()

    return jsonify({'message': 'Password changed successfully'}), 200
