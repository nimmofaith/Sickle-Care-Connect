# routes.py for Sickle Care Connect
from datetime import date, datetime
from flask import Blueprint, request, jsonify
from db import db
from sqlalchemy import inspect, text
from models import User, Appointment, Medication, Symptom, MedicalProfile, Doctor, DoctorPatient, DoctorAppointment, Hospital, Prescription
from werkzeug.security import generate_password_hash, check_password_hash

routes = Blueprint("routes", __name__)
# ------------------------------
# User Routes
# ------------------------------

# Helper for DB migration compatibility


def ensure_appointment_notes_column():
    inspector = inspect(db.engine)
    cols = [c['name'] for c in inspector.get_columns('appointment')]
    if 'notes' not in cols:
        db.session.execute(
            text('ALTER TABLE appointment ADD COLUMN notes TEXT'))
        db.session.commit()


# Signup route


@routes.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    confirm_password = data.get("confirm_password")

    # Check all fields exist
    if not name or not email or not password or not confirm_password:
        return jsonify({"message": "All fields are required"}), 400

    #  Check passwords match
    if password != confirm_password:
        return jsonify({"message": "Passwords do not match"}), 400

    # Check if user already exists
    if User.query.filter_by(email=email).first():
        return jsonify({"message": "User already exists"}), 400

    # Hash password and create user
    hashed_password = generate_password_hash(password)
    new_user = User(name=name, email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User created successfully"}), 201

# Login route


@routes.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"message": "User does not exist"}), 404

    if not check_password_hash(user.password, password):
        return jsonify({"message": "Invalid email or password"}), 401

    return jsonify({"message": f"Welcome {user.name}!", "user_id": user.id}), 200


# Get all users
@routes.route('/users', methods=['GET'])
def get_all_users():
    users = User.query.all()

    result = []
    for u in users:
        phone = None
        # if user has appointment(s), use first phone as fallback
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

# Create appointment (allow preflight)
@routes.route("/appointments", methods=["POST", "OPTIONS"])
def create_appointment():
    if request.method == 'OPTIONS':
        return ('', 204)
    # Ensure schema has notes column before create to support doctor/patient status tracking
    ensure_appointment_notes_column()
    data = request.get_json()

    print("Incoming:", data)  # 👈 DEBUG

    try:
        user_id = data.get("user_id")
        full_name = data.get("full_name")
        phone = data.get("phone")
        email = data.get("email")
        hospital = data.get("hospital")
        doctor = data.get("doctor")
        doctor_id = data.get("doctor_id")  # NEW: Get doctor_id directly
        preferred_date = data.get("preferred_date")
        preferred_time = data.get("preferred_time")

        # Validate all required fields
        if not user_id:
            return jsonify({"message": "User ID required"}), 400
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
            # NEW: Validate doctor_id
            return jsonify({"message": "Doctor ID required"}), 400

        # Prevent booking past dates
        from datetime import date, datetime as dt
        try:
            pref_date_obj = dt.strptime(preferred_date, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"message": "Invalid preferred_date format"}), 400

        today = date.today()
        if pref_date_obj < today:
            return jsonify({"message": "Preferred appointment date cannot be in the past"}), 400

        new_appointment = Appointment(
            user_id=int(user_id),
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
        db.session.flush()  # Get the ID without committing

        # NEW: Use doctor_id directly instead of fuzzy name matching
        doctor_obj = Doctor.query.get(int(doctor_id))

        if doctor_obj:
            # Link appointment to doctor
            new_appointment.doctor_id = doctor_obj.id

            # Auto-assign patient to doctor if not already assigned
            existing_assignment = DoctorPatient.query.filter_by(
                doctor_id=doctor_obj.id,
                patient_id=int(user_id)
            ).first()

            if not existing_assignment:
                doctor_patient = DoctorPatient(
                    doctor_id=doctor_obj.id,
                    patient_id=int(user_id)
                )
                db.session.add(doctor_patient)

            # Create DoctorAppointment record
            from datetime import datetime as dt
            apt_datetime = dt.strptime(
                f"{preferred_date} {preferred_time}", "%Y-%m-%d %H:%M")

            doctor_appointment = DoctorAppointment(
                doctor_id=doctor_obj.id,
                patient_id=int(user_id),
                appointment_date=apt_datetime,
                status='pending',
                reason=f"Appointment with {doctor_obj.first_name} {doctor_obj.last_name}"
            )
            db.session.add(doctor_appointment)

        db.session.commit()

        return jsonify({"message": "Appointment confirmed"}), 201

    except Exception as e:
        print("ERROR:", e)
        db.session.rollback()
        return jsonify({"message": f"Server error: {str(e)}"}), 500

# Get all appointments for a user


@routes.route("/appointments/<int:user_id>", methods=["GET", "OPTIONS"])
def get_appointments(user_id):
    appointments = Appointment.query.filter_by(user_id=user_id).all()
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
    data = request.get_json()
    appointment_id = data.get("appointment_id")
    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        return jsonify({"message": "Appointment not found"}), 404

    # Mark appointment as cancelled instead of hard delete
    appointment.status = 'cancelled'
    appointment.notes = 'Cancelled by patient'
    db.session.add(appointment)

    # If a doctor appointment exists, mark it cancelled too
    doctor_appointment = DoctorAppointment.query.filter_by(
        patient_id=appointment.user_id,
        appointment_date=datetime.strptime(
            f"{appointment.preferred_date} {appointment.preferred_time}", "%Y-%m-%d %H:%M")
    ).first()

    if doctor_appointment:
        doctor_appointment.status = 'cancelled'
        doctor_appointment.notes = 'Cancelled by patient'
        db.session.add(doctor_appointment)

        # If the patient has no approved doctor appointments with this doctor, remove doctor-patient mapping
        approved_appointment = DoctorAppointment.query.filter_by(
            doctor_id=doctor_appointment.doctor_id,
            patient_id=doctor_appointment.patient_id,
            status='approved'
        ).first()

        if not approved_appointment:
            doctor_patient_link = DoctorPatient.query.filter_by(
                doctor_id=doctor_appointment.doctor_id,
                patient_id=doctor_appointment.patient_id
            ).first()
            if doctor_patient_link:
                db.session.delete(doctor_patient_link)

    db.session.commit()
    return jsonify({"message": "Appointment cancelled successfully"}), 200


@routes.route('/appointments/upcoming/<int:user_id>', methods=['GET'])
def get_upcoming(user_id):
    today = date.today().isoformat()  # Get today's date in 'YYYY-MM-DD' format

    appointments = Appointment.query.filter(
        Appointment.user_id == user_id,
        Appointment.preferred_date >= today,
        Appointment.status != 'cancelled'
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


@routes.route('/appointments/past/<int:user_id>', methods=['GET'])
def get_past(user_id):
    today = date.today().isoformat()  # Get today's date in 'YYYY-MM-DD' format

    appointments = Appointment.query.filter(
        Appointment.user_id == user_id,
        Appointment.preferred_date < today
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


# Clear all appointments for a user
@routes.route('/appointments/clear/<int:user_id>', methods=['DELETE'])
def clear_all_appointments(user_id):
    """Clear all appointments (upcoming and history) for a user"""
    try:
        # Delete all appointments for this user
        appointments = Appointment.query.filter_by(user_id=user_id).all()
        count = len(appointments)

        for appointment in appointments:
            db.session.delete(appointment)

        # Also clear any related doctor appointments
        doctor_appointments = DoctorAppointment.query.filter_by(
            patient_id=user_id).all()
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
# Medication Routes
# ------------------------------


@routes.route('/medications', methods=['POST', 'OPTIONS'])
def add_medication():
    """Patients cannot add their own medications - only doctors can via prescriptions"""
    if request.method == 'OPTIONS':
        return ('', 204)

    return jsonify({"message": "Patients cannot add medications. Please consult your doctor for prescriptions."}), 403

# Get medications for user


@routes.route('/medications/<int:user_id>', methods=['GET'])
def get_medications(user_id):
    # Only show doctor-prescribed medications
    meds = Medication.query.filter_by(
        user_id=user_id, prescribed_by_doctor=True).all()

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
@routes.route('/prescriptions/<int:user_id>', methods=['GET'])
def get_prescriptions(user_id):
    prescriptions = Prescription.query.filter_by(patient_id=user_id).all()

    return jsonify([
        {
            "id": p.id,
            "medication_name": p.medication_name,
            "dosage": p.dosage,
            "frequency": p.frequency,
            "duration": p.duration,
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
    med = Medication.query.get(medication_id)
    if not med:
        return jsonify({"message": "Medication not found"}), 404

    db.session.delete(med)
    db.session.commit()
    return jsonify({"message": "Medication removed successfully"}), 200

# -------------------------------
# Symptoms Routes
# -------------------------------


@routes.route('/symptoms', methods=['POST', 'OPTIONS'])
def add_symptom():
    data = request.json

    sym = Symptom(
        user_id=data['user_id'],
        pain_level=data['painLevel'],
        location=data['location'],
        trigger=data['trigger'],
        relief=data['relief'],
        symptoms=",".join(data['symptoms'])
    )

    db.session.add(sym)
    db.session.commit()

    return jsonify({"message": "Symptom logged"})


@routes.route('/symptoms/<int:user_id>')
def get_symptoms(user_id):
    data = Symptom.query.filter_by(user_id=user_id).all()

    return jsonify([
        {
            "pain_level": s.pain_level,
            "location": s.location,
            "trigger": s.trigger,
            "relief": s.relief,
            "symptoms": s.symptoms,
            "date": s.created_at
        } for s in data
    ])

# -------------------------------
# Medical Profile Routes
# -------------------------------


@routes.route('/profile', methods=['POST', 'OPTIONS'])
def save_profile():
    if request.method == 'OPTIONS':
        return ('', 204)

    try:
        data = request.json

        if not data.get('user_id'):
            return jsonify({"message": "User ID required"}), 400

        profile = MedicalProfile.query.filter_by(
            user_id=data['user_id']).first()

        if profile:
            profile.genotype = data.get('genotype')
            profile.blood_type = data.get('blood_type')
            profile.allergies = data.get('allergies')
            profile.complications = data.get('complications')
        else:
            profile = MedicalProfile(
                user_id=int(data['user_id']),
                genotype=data.get('genotype'),
                blood_type=data.get('blood_type'),
                allergies=data.get('allergies'),
                complications=data.get('complications')
            )
            db.session.add(profile)

        db.session.commit()
        return jsonify({"message": "Profile saved"}), 201
    except Exception as e:
        print("ERROR saving profile:", e)
        db.session.rollback()
        return jsonify({"message": f"Error saving profile: {str(e)}"}), 500


@routes.route('/profile/<int:user_id>')
def get_profile(user_id):
    p = MedicalProfile.query.filter_by(user_id=user_id).first()

    if not p:
        return jsonify({})

    return jsonify({
        "genotype": p.genotype,
        "blood_type": p.blood_type,
        "allergies": p.allergies,
        "complications": p.complications
    })
