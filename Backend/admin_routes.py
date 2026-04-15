from flask import Blueprint, request, jsonify
from db import db
from models import Admin, Patient, Hospital, Doctor, Appointment, Medication, MedicalProfile, DoctorPatient, DoctorAppointment, Prescription, ConsultationNote
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_, and_
from jwt_utils import generate_token, verify_token, extract_token_from_header

admin_routes = Blueprint("admin_routes", __name__, url_prefix="/admin")

# ------------------------------
# Authentication Middleware
# ------------------------------


def require_admin():
    """Middleware to check if user is admin using JWT"""
    if request.method == 'OPTIONS':
        return None, jsonify({}), 200  # Allow preflight CORS requests

    token = extract_token_from_header()
    if not token:
        return None, jsonify({"message": "Authorization header required"}), 401

    payload, error = verify_token(token)
    if error:
        return None, jsonify({"message": error}), 401

    # Check if user type is admin
    if payload.get('user_type') != 'admin':
        return None, jsonify({"message": "Invalid credentials or insufficient permissions"}), 401

    # Fetch the admin from database to return as user object
    admin = Admin.query.get(payload.get('user_id'))
    if not admin:
        return None, jsonify({"message": "Admin not found"}), 401

    return admin, None, None

# ------------------------------
# Admin Login
# ------------------------------


@admin_routes.route("/login", methods=["POST", "OPTIONS"])
def admin_login():
    if request.method == 'OPTIONS':
        return ('', 204)

    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"message": "Invalid JSON payload"}), 400

        email = data.get("email", "").strip()
        password = data.get("password", "")

        if not email or not password:
            return jsonify({"message": "Email and password are required"}), 400

        admin = Admin.query.filter_by(email=email).first()
        if not admin:
            return jsonify({"message": "Invalid admin credentials"}), 401

        if not admin.password or not check_password_hash(admin.password, password):
            return jsonify({"message": "Invalid admin credentials"}), 401

        # Generate JWT token
        token = generate_token(admin.id, 'admin', admin.email)
        return jsonify({
            "message": f"Welcome Admin {admin.name}!",
            "user_id": admin.id,
            "token": token
        }), 200
    except Exception as e:
        return jsonify({"message": f"Server error: {str(e)}"}), 500

# ------------------------------
# Dashboard Stats
# ------------------------------


@admin_routes.route("/dashboard/stats", methods=["GET"])
def get_dashboard_stats():
    user, error, status = require_admin()
    if error:
        return error, status

    from datetime import datetime
    now = datetime.now()

    stats = {
        "total_hospitals": Hospital.query.count(),
        "total_doctors": Doctor.query.count(),
        "total_patients": Patient.query.count(),
        "total_appointments": Appointment.query.count(),
        "pending_appointments": Appointment.query.filter_by(status='pending').count(),
        "active_prescriptions": Prescription.query.filter(
            Prescription.status.notin_(['discontinued', 'completed']),
            (Prescription.end_date.is_(None) | (Prescription.end_date > now))
        ).count()
    }
    return jsonify(stats), 200

# ------------------------------
# Hospital Management
# ------------------------------


@admin_routes.route("/hospitals", methods=["GET"])
def get_hospitals():
    user, error, status = require_admin()
    if error:
        return error, status

    search = request.args.get('search', '')
    hospitals = Hospital.query.filter(
        or_(Hospital.name.contains(search),
            Hospital.city.contains(search),
            Hospital.location.contains(search),
            Hospital.service.contains(search))
    ).all()

    result = [{
        "id": h.id,
        "name": h.name,
        "city": h.city,
        "location": h.location,
        "service": h.service,
        "notes": h.notes,
        "created_at": h.created_at.isoformat() if h.created_at else None
    } for h in hospitals]

    return jsonify(result), 200


@admin_routes.route("/hospitals", methods=["POST"])
def create_hospital():
    user, error, status = require_admin()
    if error:
        return error, status

    data = request.get_json()
    name = data.get("name")
    city = data.get("city")
    location = data.get("location")
    service = data.get("service")
    notes = data.get("notes")

    if not all([name, city, location, service]):
        return jsonify({"message": "Name, city, location, and service are required"}), 400

    if Hospital.query.filter_by(name=name).first():
        return jsonify({"message": "Hospital with this name already exists"}), 400

    new_hospital = Hospital(
        name=name.strip(),
        city=city.strip(),
        location=location.strip(),
        service=service.strip(),
        notes=notes.strip() if notes else None
    )

    db.session.add(new_hospital)
    db.session.commit()

    return jsonify({"message": "Hospital created successfully", "id": new_hospital.id}), 201


@admin_routes.route("/hospitals/<int:hospital_id>", methods=["PUT"])
def update_hospital(hospital_id):
    user, error, status = require_admin()
    if error:
        return error, status

    hospital = Hospital.query.get(hospital_id)
    if not hospital:
        return jsonify({"message": "Hospital not found"}), 404

    data = request.get_json()
    hospital.name = data.get("name", hospital.name).strip()
    hospital.city = data.get("city", hospital.city).strip()
    hospital.location = data.get("location", hospital.location).strip()
    hospital.service = data.get("service", hospital.service).strip()
    hospital.notes = data.get("notes", hospital.notes).strip(
    ) if data.get("notes") else hospital.notes

    db.session.commit()
    return jsonify({"message": "Hospital updated successfully"}), 200


@admin_routes.route("/hospitals/<int:hospital_id>", methods=["DELETE"])
def delete_hospital(hospital_id):
    user, error, status = require_admin()
    if error:
        return error, status

    hospital = Hospital.query.get(hospital_id)
    if not hospital:
        return jsonify({"message": "Hospital not found"}), 404

    # Check if hospital has doctors
    if hospital.doctors:
        return jsonify({"message": "Cannot delete hospital with assigned doctors"}), 400

    db.session.delete(hospital)
    db.session.commit()
    return jsonify({"message": "Hospital deleted successfully"}), 200

# ------------------------------
# Doctor Management
# ------------------------------


@admin_routes.route("/doctors", methods=["GET"])
def get_doctors():
    user, error, status = require_admin()
    if error:
        return error, status

    search = request.args.get('search', '')
    hospital_filter = request.args.get('hospital_id')

    query = Doctor.query.join(Hospital).filter(
        or_(Doctor.name.contains(search),
            Doctor.specialization.contains(search),
            Doctor.license_number.contains(search),
            Hospital.name.contains(search))
    )

    if hospital_filter:
        query = query.filter(Doctor.hospital_id == hospital_filter)

    doctors = query.all()

    result = [{
        "id": d.id,
        "name": d.name,
        "email": d.email,
        "specialization": d.specialization,
        "license_number": d.license_number,
        "hospital_id": d.hospital_id,
        "hospital_name": d.hospital.name if d.hospital else None,
        "created_at": d.created_at.isoformat() if d.created_at else None
    } for d in doctors]

    return jsonify(result), 200


@admin_routes.route("/doctors", methods=["POST"])
def create_doctor():
    user, error, status = require_admin()
    if error:
        return error, status

    data = request.get_json()
    email = data.get("email")
    name = data.get("name")
    specialization = data.get("specialization")
    license_number = data.get("license_number")
    hospital_id = data.get("hospital_id")

    if not all([email, name, specialization, license_number, hospital_id]):
        return jsonify({"message": "All fields are required"}), 400

    if Doctor.query.filter_by(email=email).first():
        return jsonify({"message": "Email already exists"}), 400

    if Doctor.query.filter_by(license_number=license_number).first():
        return jsonify({"message": "License number already exists"}), 400

    hospital = Hospital.query.get(hospital_id)
    if not hospital:
        return jsonify({"message": "Hospital not found"}), 404

    # Create doctor profile
    new_doctor = Doctor(
        email=email,
        name=name.strip(),
        specialization=specialization.strip(),
        license_number=license_number.strip(),
        hospital_id=hospital_id
    )

    db.session.add(new_doctor)
    db.session.commit()

    return jsonify({"message": "Doctor created successfully", "id": new_doctor.id}), 201


@admin_routes.route("/doctors/<int:doctor_id>", methods=["PUT"])
def update_doctor(doctor_id):
    user, error, status = require_admin()
    if error:
        return error, status

    doctor = Doctor.query.get(doctor_id)
    if not doctor:
        return jsonify({"message": "Doctor not found"}), 404

    data = request.get_json()

    # Update user info
    if 'name' in data:
        doctor.name = data.get("name", doctor.name).strip()

    doctor.specialization = data.get(
        "specialization", doctor.specialization).strip()
    doctor.license_number = data.get(
        "license_number", doctor.license_number).strip()

    if 'hospital_id' in data:
        hospital = Hospital.query.get(data['hospital_id'])
        if not hospital:
            return jsonify({"message": "Hospital not found"}), 404
        doctor.hospital_id = data['hospital_id']

    db.session.commit()
    return jsonify({"message": "Doctor updated successfully"}), 200


@admin_routes.route("/doctors/<int:doctor_id>", methods=["DELETE"])
def delete_doctor(doctor_id):
    user, error, status = require_admin()
    if error:
        return error, status

    doctor = Doctor.query.get(doctor_id)
    if not doctor:
        return jsonify({"message": "Doctor not found"}), 404

    # Check if doctor has active appointments
    active_appointments = DoctorAppointment.query.filter(
        DoctorAppointment.doctor_id == doctor_id,
        DoctorAppointment.status.in_(['pending', 'approved'])
    ).count()

    if active_appointments > 0:
        return jsonify({"message": "Cannot delete doctor with active appointments"}), 400

    # Delete doctor profile and any related appointments
    DoctorAppointment.query.filter_by(doctor_id=doctor_id).delete()
    Prescription.query.filter_by(doctor_id=doctor_id).delete()
    ConsultationNote.query.filter_by(doctor_id=doctor_id).delete()
    DoctorPatient.query.filter_by(doctor_id=doctor_id).delete()

    db.session.delete(doctor)
    db.session.commit()

    return jsonify({"message": "Doctor deleted successfully"}), 200

# ------------------------------
# Patient Management
# ------------------------------


@admin_routes.route("/patients", methods=["GET"])
def get_patients():
    user, error, status = require_admin()
    if error:
        return error, status

    search = request.args.get('search', '')
    patients = Patient.query.filter(
        or_(Patient.name.contains(search), Patient.email.contains(search))
    ).all()

    result = [{
        "id": p.id,
        "name": p.name,
        "email": p.email,
        "created_at": p.created_at.isoformat() if p.created_at else None
    } for p in patients]

    return jsonify(result), 200


@admin_routes.route("/patients/<int:patient_id>", methods=["PUT"])
def update_patient(patient_id):
    user, error, status = require_admin()
    if error:
        return error, status

    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({"message": "Patient not found"}), 404

    data = request.get_json() or {}
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    confirm_password = data.get("confirm_password")

    if name is not None:
        patient.name = name.strip()

    if email:
        existing = Patient.query.filter(
            Patient.email == email, Patient.id != patient_id).first()
        if existing:
            return jsonify({"message": "Email is already in use by another patient"}), 400
        patient.email = email.strip()

    if password:
        if password != confirm_password:
            return jsonify({"message": "Passwords do not match"}), 400
        patient.password = generate_password_hash(password)

    db.session.commit()
    return jsonify({"message": "Patient updated successfully"}), 200


@admin_routes.route("/patients/<int:patient_id>", methods=["DELETE"])
def delete_patient(patient_id):
    user, error, status = require_admin()
    if error:
        return error, status

    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({"message": "Patient not found"}), 404

    # Delete all related patient data first to avoid FK constraint issues
    Appointment.query.filter_by(patient_id=patient_id).delete()
    Medication.query.filter_by(patient_id=patient_id).delete()
    MedicalProfile.query.filter_by(patient_id=patient_id).delete()
    DoctorPatient.query.filter_by(patient_id=patient_id).delete()
    DoctorAppointment.query.filter_by(patient_id=patient_id).delete()
    Prescription.query.filter_by(patient_id=patient_id).delete()
    ConsultationNote.query.filter_by(patient_id=patient_id).delete()

    db.session.delete(patient)
    db.session.commit()

    return jsonify({"message": "Patient deleted successfully"}), 200

# ------------------------------
# Appointment Management
# ------------------------------


@admin_routes.route("/appointments", methods=["GET"])
def get_appointments():
    user, error, status = require_admin()
    if error:
        return error, status

    status_filter = request.args.get('status')
    search = request.args.get('search', '')

    query = Appointment.query.filter(
        or_(Appointment.full_name.contains(search),
            Appointment.doctor.contains(search),
            Appointment.hospital.contains(search))
    )

    if status_filter:
        query = query.filter(Appointment.status == status_filter)

    appointments = query.all()

    result = [{
        "id": a.id,
        "full_name": a.full_name,
        "email": a.email,
        "phone": a.phone,
        "hospital": a.hospital,
        "doctor": a.doctor,
        "preferred_date": a.preferred_date,
        "preferred_time": a.preferred_time,
        "status": a.status,
        "notes": a.notes,
        "status_report": a.status_report or ''
    } for a in appointments]

    return jsonify(result), 200


@admin_routes.route("/appointments/<int:appointment_id>/status", methods=["PUT"])
def update_appointment_status(appointment_id):
    user, error, status = require_admin()
    if error:
        return error, status

    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        return jsonify({"message": "Appointment not found"}), 404

    data = request.get_json()
    new_status = data.get("status")
    notes = data.get("notes") or ""

    if new_status not in ['pending', 'approved', 'declined', 'cancelled', 'completed']:
        return jsonify({"message": "Invalid status"}), 400

    if not notes.strip():
        default_notes = {
            'approved': 'Approved by admin',
            'declined': 'Declined by admin',
            'cancelled': 'Cancelled by admin',
            'completed': 'Completed by admin'
        }
        notes = default_notes.get(new_status, notes)

    appointment.status = new_status
    appointment.status_report = notes

    # Update corresponding doctor appointment if exists
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
                best_match.status = new_status
                best_match.status_report = notes
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
                    da.status = new_status
                    da.status_report = notes
                    break
        except:
            pass

    db.session.commit()
    return jsonify({"message": f"Appointment status updated to {new_status}"}), 200

# ------------------------------
# Prescription Management
# ------------------------------


@admin_routes.route("/prescriptions", methods=["GET"])
def get_prescriptions():
    user, error, status = require_admin()
    if error:
        return error, status

    status_filter = request.args.get('status')
    search = request.args.get('search', '')

    query = Prescription.query.join(Doctor).join(Patient).filter(
        or_(Prescription.medication_name.contains(search),
            Doctor.name.contains(search),
            Patient.name.contains(search))
    )

    if status_filter:
        query = query.filter(Prescription.status == status_filter)

    prescriptions = query.all()

    result = [{
        "id": p.id,
        "patient_name": p.patient.name,
        "doctor_name": p.doctor.name,
        "medication_name": p.medication_name,
        "dosage": p.dosage,
        "frequency": p.frequency,
        "refill_date": p.refill_date,
        "start_date": p.start_date.isoformat() if p.start_date else None,
        "end_date": p.end_date.isoformat() if p.end_date else None,
        "status": p.status,
        "notes": p.notes or '',
        "status_report": p.status_report or ''
    } for p in prescriptions]

    return jsonify(result), 200


@admin_routes.route("/prescriptions/<int:prescription_id>/status", methods=["PUT"])
def update_prescription_status(prescription_id):
    user, error, status = require_admin()
    if error:
        return error, status

    prescription = Prescription.query.get(prescription_id)
    if not prescription:
        return jsonify({"message": "Prescription not found"}), 404

    data = request.get_json()
    new_status = data.get("status")

    if new_status not in ['active', 'completed', 'discontinued']:
        return jsonify({"message": "Invalid status"}), 400

    notes = data.get("notes") or ""
    if not notes.strip():
        default_notes = {
            'completed': 'Completed by admin',
            'discontinued': 'Discontinued by admin'
        }
        notes = default_notes.get(new_status, notes)

    prescription.status = new_status
    prescription.status_report = notes
    db.session.commit()

    return jsonify({"message": f"Prescription status updated to {new_status}"}), 200
