from flask import Blueprint, request, jsonify
from db import db
from models import (
    Doctor, Hospital, DoctorPatient, DoctorAppointment,
    Prescription, ConsultationNote, Patient, MedicalProfile, Appointment
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
from jwt_utils import generate_token, verify_token, extract_token_from_header

doctor_routes = Blueprint("doctor_routes", __name__, url_prefix="/doctor")

# ==============================
# Helper function to verify doctor authentication
# ==============================


def verify_doctor(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'OPTIONS':
            return jsonify({}), 200  # Allow preflight OPTIONS

        token = extract_token_from_header()
        if not token:
            return jsonify({"message": "Authorization header required"}), 401

        payload, error = verify_token(token)
        if error:
            return jsonify({"message": error}), 401

        # Check if user type is doctor
        if payload.get('user_type') != 'doctor':
            return jsonify({"message": "Invalid credentials"}), 401

        return f(doctor_id=payload.get('user_id'), *args, **kwargs)

    return decorated_function


# ==============================
# DOCTOR AUTHENTICATION
# ==============================

@doctor_routes.route('/login', methods=['POST', 'OPTIONS'])
def doctor_login():
    """Doctor login with email and password"""
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

        doctor = Doctor.query.filter_by(email=email).first()

        if not doctor:
            return jsonify({"message": "Doctor not found"}), 404

        if not doctor.password:
            return jsonify({"message": "Doctor account not registered. Please register using your email."}), 403

        if not check_password_hash(doctor.password, password):
            return jsonify({"message": "Invalid email or password"}), 401

        # Generate JWT token
        token = generate_token(doctor.id, 'doctor', doctor.email)

        return jsonify({
            "message": f"Welcome Dr. {doctor.name}!",
            "doctor_id": doctor.id,
            "doctor_name": doctor.name,
            "specialization": doctor.specialization,
            "hospital_id": doctor.hospital_id,
            "token": token
        }), 200
    except Exception as e:
        return jsonify({"message": f"Server error: {str(e)}"}), 500


# ==============================
# HOSPITAL MANAGEMENT
# ==============================

@doctor_routes.route('/hospitals', methods=['GET'])
def get_hospitals():
    """Get all hospitals (for registration dropdown)"""
    hospitals = Hospital.query.all()
    return jsonify([{
        'id': h.id,
        'name': h.name,
        'address': h.address,
        'city': h.city,
        'phone': h.phone
    } for h in hospitals]), 200


@doctor_routes.route('/hospitals', methods=['POST'])
def create_hospital():
    """Create a new hospital (admin only)"""
    return jsonify({"message": "Hospital creation must be performed through the admin API at /admin/hospitals."}), 403


# ==============================
# DOCTOR AUTHENTICATION & REGISTRATION
# NOTE: Doctors are created by admins only (via /admin/doctors endpoint)
# ==============================


# ==============================
# DOCTOR DASHBOARD STATISTICS
# ==============================

@doctor_routes.route('/dashboard', methods=['GET'])
@verify_doctor
def get_dashboard(doctor_id):
    """Get dashboard overview statistics (cached values)"""
    doctor = Doctor.query.get(doctor_id)

    # Count patients
    patient_count = db.session.query(
        DoctorPatient).filter_by(doctor_id=doctor_id).count()

    # Count appointments (pending, future only)
    from datetime import datetime
    now = datetime.now()
    pending_appointments = db.session.query(DoctorAppointment).filter(
        DoctorAppointment.doctor_id == doctor_id,
        DoctorAppointment.status == 'pending',
        DoctorAppointment.appointment_date >= now
    ).count()

    # Count approved appointments (future only)
    from datetime import datetime
    now = datetime.now()
    approved_appointments = db.session.query(DoctorAppointment).filter(
        DoctorAppointment.doctor_id == doctor_id,
        DoctorAppointment.status == 'approved',
        DoctorAppointment.appointment_date >= now
    ).count()

    from datetime import datetime
    now = datetime.now()

    # Count active prescriptions
    active_prescriptions = db.session.query(Prescription).filter(
        Prescription.doctor_id == doctor_id,
        Prescription.status.notin_(['discontinued', 'completed']),
        (Prescription.end_date.is_(None) | (Prescription.end_date > now))
    ).count()

    # Recent consultation notes (last 5)
    recent_notes = db.session.query(ConsultationNote).filter_by(
        doctor_id=doctor_id
    ).order_by(ConsultationNote.created_at.desc()).limit(5).all()

    return jsonify({
        "doctor_name": doctor.name,
        "specialization": doctor.specialization,
        "hospital": doctor.hospital.name,
        "total_patients": patient_count,
        "pending_appointments": pending_appointments,
        "approved_appointments": approved_appointments,
        "active_prescriptions": active_prescriptions,
        "recent_notes_count": len(recent_notes)
    }), 200


# ==============================
# PATIENT MANAGEMENT FOR DOCTORS
# ==============================

@doctor_routes.route('/patients', methods=['GET'])
@verify_doctor
def get_my_patients(doctor_id):
    """Get all patients assigned to this doctor (paginated)"""
    page = request.args.get('page', 1, type=int)
    per_page = 10

    doctor_patients = DoctorPatient.query.filter_by(
        doctor_id=doctor_id
    ).paginate(page=page, per_page=per_page, error_out=False)

    patients_data = []
    for dp in doctor_patients.items:
        patient = Patient.query.get(dp.patient_id)
        if not patient:
            continue
        medical_profile = MedicalProfile.query.filter_by(
            patient_id=dp.patient_id).first()

        # Get phone from latest appointment
        phone = None
        latest_appointment = Appointment.query.filter_by(
            patient_id=dp.patient_id).order_by(Appointment.id.desc()).first()
        if latest_appointment:
            phone = latest_appointment.phone

        patients_data.append({
            "patient_id": patient.id,
            "name": patient.name,
            "email": patient.email,
            "phone": phone,
            "genotype": medical_profile.genotype if medical_profile else "N/A",
            "blood_type": medical_profile.blood_type if medical_profile else "N/A",
            "assigned_date": dp.assigned_date.isoformat()
        })

    return jsonify({
        "patients": patients_data,
        "total": doctor_patients.total,
        "pages": doctor_patients.pages,
        "current_page": page
    }), 200


@doctor_routes.route('/patients/<int:patient_id>', methods=['GET'])
@verify_doctor
def get_patient_details(doctor_id, patient_id):
    """Get detailed patient information"""
    # Verify doctor has access to this patient
    doctor_patient = DoctorPatient.query.filter_by(
        doctor_id=doctor_id,
        patient_id=patient_id
    ).first()

    if not doctor_patient:
        return jsonify({"message": "Access denied. Patient not assigned to you"}), 403

    patient = Patient.query.get(patient_id)
    medical_profile = MedicalProfile.query.filter_by(
        patient_id=patient_id).first()

    from datetime import datetime
    now = datetime.now()

    prescriptions = Prescription.query.filter(
        Prescription.patient_id == patient_id,
        Prescription.doctor_id == doctor_id,
        Prescription.status.notin_(['discontinued', 'completed']),
        (Prescription.end_date.is_(None) | (Prescription.end_date > now))
    ).all()

    notes = ConsultationNote.query.filter_by(
        patient_id=patient_id
    ).order_by(ConsultationNote.created_at.desc()).limit(10).all()

    # Get previous appointments (last 2 months)
    two_months_ago = datetime.now() - timedelta(days=60)
    previous_appointments = DoctorAppointment.query.filter(
        DoctorAppointment.patient_id == patient_id,
        DoctorAppointment.appointment_date < datetime.now(),
        DoctorAppointment.appointment_date >= two_months_ago
    ).order_by(DoctorAppointment.appointment_date.desc()).all()

    # Get upcoming appointments
    upcoming_appointments = DoctorAppointment.query.filter(
        DoctorAppointment.patient_id == patient_id,
        DoctorAppointment.appointment_date >= datetime.now()
    ).order_by(DoctorAppointment.appointment_date).all()

    return jsonify({
        "patient": {
            "id": patient.id,
            "name": patient.name,
            "email": patient.email,
            "phone": patient.appointments[0].phone if patient.appointments else "N/A"
        },
        "medical_profile": {
            "genotype": medical_profile.genotype if medical_profile else "",
            "blood_type": medical_profile.blood_type if medical_profile else "",
            "allergies": medical_profile.allergies if medical_profile else "",
            "complications": medical_profile.complications if medical_profile else ""
        },
        "active_prescriptions": [{
            "id": p.id,
            "medication": p.medication_name,
            "dosage": p.dosage,
            "frequency": p.frequency,
            "duration": p.duration,
            "start_date": p.start_date.isoformat()
        } for p in prescriptions],
        "recent_notes": [{
            "id": n.id,
            "visit_date": n.visit_date.isoformat(),
            "observations": n.observations,
            "pain_level": n.pain_level
        } for n in notes],
        "previous_appointments": [{
            "id": apt.id,
            "date": apt.appointment_date.isoformat(),
            "status": apt.status,
            "notes": apt.notes,
            "status_report": apt.status_report or ''
        } for apt in previous_appointments],
        "upcoming_appointments": [{
            "id": apt.id,
            "date": apt.appointment_date.isoformat(),
            "status": apt.status,
            "notes": apt.notes,
            "status_report": apt.status_report or ''
        } for apt in upcoming_appointments]
    }), 200


@doctor_routes.route('/patients/<int:patient_id>/search', methods=['GET'])
@verify_doctor
def search_patient(doctor_id, patient_id):
    """Quick search for patient (by name or ID)"""
    # Verify doctor has access to this patient
    doctor_patient = DoctorPatient.query.filter_by(
        doctor_id=doctor_id,
        patient_id=patient_id
    ).first()

    if not doctor_patient:
        return jsonify({"message": "Access denied"}), 403

    patient = Patient.query.get(patient_id)
    return jsonify({
        "patient_id": patient.id,
        "name": patient.name,
        "email": patient.email
    }), 200


# ==============================
# APPOINTMENT MANAGEMENT
# ==============================

@doctor_routes.route('/appointments', methods=['GET'])
@verify_doctor
def get_my_appointments(doctor_id):
    """Get all appointments for this doctor with optional filters"""
    try:
        # pending, approved, declined, cancelled
        status_filter = request.args.get('status')
        limit = request.args.get('limit', 20, type=int)

        query = DoctorAppointment.query.filter_by(doctor_id=doctor_id)

        if status_filter:
            query = query.filter_by(status=status_filter)

        appointments = query.order_by(
            DoctorAppointment.appointment_date.asc()
        ).limit(limit).all()

        appointments_data = []
        for a in appointments:
            patient = Patient.query.get(a.patient_id)
            latest_appointment = Appointment.query.filter_by(
                patient_id=a.patient_id).order_by(Appointment.id.desc()).first()
            phone = latest_appointment.phone if latest_appointment else "N/A"

            appointments_data.append({
                "id": a.id,
                "patient_id": a.patient_id,
                "patient_name": patient.name if patient else "Unknown",
                "patient_phone": phone,
                "appointment_date": a.appointment_date.isoformat() if a.appointment_date else None,
                "status": a.status,
                "notes": a.notes or "",
                "status_report": a.status_report or ""
            })

        return jsonify({
            "appointments": appointments_data
        }), 200

    except Exception as e:

        return jsonify({"message": "Error fetching appointments", "details": str(e)}), 500


@doctor_routes.route('/appointments/<int:appointment_id>/approve', methods=['POST'])
@verify_doctor
def approve_appointment(doctor_id, appointment_id):
    """Approve an appointment and auto-add patient to doctor's patient list"""
    appointment = DoctorAppointment.query.get(appointment_id)

    if not appointment or appointment.doctor_id != doctor_id:
        return jsonify({"message": "Appointment not found or access denied"}), 404

    appointment.status = 'approved'
    appointment.updated_at = datetime.now()

    patient_appointment = Appointment.query.filter_by(
        patient_id=appointment.patient_id,
        doctor_id=appointment.doctor_id,
        preferred_date=appointment.appointment_date.date().isoformat(),
        preferred_time=appointment.appointment_date.strftime('%H:%M')
    ).first()
    if patient_appointment:
        patient_appointment.status = 'approved'
        patient_appointment.status_report = 'Approved by doctor'
        db.session.add(patient_appointment)

    existing_assignment = DoctorPatient.query.filter_by(
        doctor_id=doctor_id,
        patient_id=appointment.patient_id
    ).first()

    if not existing_assignment:
        doctor_patient = DoctorPatient(
            doctor_id=doctor_id,
            patient_id=appointment.patient_id
        )
        db.session.add(doctor_patient)

    db.session.commit()

    return jsonify({"message": "Appointment approved and patient added to your list"}), 200


@doctor_routes.route('/appointments/<int:appointment_id>/decline', methods=['POST'])
@verify_doctor
def decline_appointment(doctor_id, appointment_id):
    """Decline an appointment"""
    data = request.get_json()
    reason = data.get('reason', '')

    appointment = DoctorAppointment.query.get(appointment_id)

    if not appointment or appointment.doctor_id != doctor_id:
        return jsonify({"message": "Appointment not found or access denied"}), 404

    appointment.status = 'declined'
    appointment.notes = reason or 'Declined by doctor'
    appointment.updated_at = datetime.now()

    patient_appointment = Appointment.query.filter_by(
        patient_id=appointment.patient_id,
        doctor_id=appointment.doctor_id,
        preferred_date=appointment.appointment_date.date().isoformat(),
        preferred_time=appointment.appointment_date.strftime('%H:%M')
    ).order_by(Appointment.id.desc()).first()

    if patient_appointment:
        patient_appointment.status = 'declined'
        patient_appointment.status_report = 'Declined by doctor'
        db.session.add(patient_appointment)
    else:
        # Create a corresponding patient appointment record for audit (declined)
        patient = Patient.query.get(appointment.patient_id)
        doctor = Doctor.query.get(appointment.doctor_id)

        if patient and doctor:
            new_appointment = Appointment(
                patient_id=appointment.patient_id,
                full_name=patient.name,
                phone=patient.phone or "N/A",
                email=patient.email,
                hospital=doctor.hospital.name if doctor.hospital else "N/A",
                doctor=doctor.name,
                doctor_id=appointment.doctor_id,
                preferred_date=appointment.appointment_date.date().isoformat(),
                preferred_time=appointment.appointment_date.strftime('%H:%M'),
                status='declined',
                status_report='Declined by doctor'
            )
            db.session.add(new_appointment)

    approved_existing = DoctorAppointment.query.filter_by(
        doctor_id=doctor_id,
        patient_id=appointment.patient_id,
        status='approved'
    ).first()

    if not approved_existing:
        doctor_patient_link = DoctorPatient.query.filter_by(
            doctor_id=doctor_id,
            patient_id=appointment.patient_id
        ).first()
        if doctor_patient_link:
            db.session.delete(doctor_patient_link)

    db.session.commit()

    return jsonify({"message": "Appointment declined"}), 200


@doctor_routes.route('/appointments/<int:appointment_id>/reschedule', methods=['POST'])
@verify_doctor
def reschedule_appointment(doctor_id, appointment_id):
    """Reschedule an appointment"""
    data = request.get_json()
    new_date = data.get('new_date')

    if not new_date:
        return jsonify({"message": "New date required"}), 400

    appointment = DoctorAppointment.query.get(appointment_id)

    if not appointment or appointment.doctor_id != doctor_id:
        return jsonify({"message": "Appointment not found or access denied"}), 404

    try:
        appointment.appointment_date = datetime.fromisoformat(new_date)
        appointment.status = 'rescheduled'
        appointment.updated_at = datetime.now()
        db.session.commit()
        return jsonify({"message": "Appointment rescheduled"}), 200
    except ValueError:
        return jsonify({"message": "Invalid date format"}), 400


# ==============================
# PRESCRIPTION MANAGEMENT
# ==============================

@doctor_routes.route('/prescriptions', methods=['POST'])
@verify_doctor
def create_prescription(doctor_id):
    """Create a new prescription for a patient"""
    data = request.get_json()
    patient_id = data.get('patient_id')
    medication_name = data.get('medication_name')
    dosage = data.get('dosage')
    frequency = data.get('frequency')
    prescription_type = data.get(
        'prescription_type', 'long-term')  # short-term or long-term
    end_date = data.get('end_date')  # For short-term
    refill_date = data.get('refill_date')  # For long-term
    notes = data.get('notes', '')

    # Verify doctor has access to this patient
    doctor_patient = DoctorPatient.query.filter_by(
        doctor_id=doctor_id,
        patient_id=patient_id
    ).first()

    if not doctor_patient:
        return jsonify({"message": "Patient not assigned to you"}), 403

    if not all([medication_name, dosage, frequency]):
        return jsonify({"message": "Medication name, dosage, and frequency are required"}), 400

    # Validate based on prescription type
    todayDate = datetime.now().date()

    if prescription_type == "short-term":
        if not end_date:
            return jsonify({"message": "End date is required for short-term prescriptions"}), 400
        try:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
            if end_date_obj < todayDate:
                return jsonify({"message": "End date cannot be in the past"}), 400
        except ValueError:
            return jsonify({"message": "Invalid end date format"}), 400

        new_prescription = Prescription(
            doctor_id=doctor_id,
            patient_id=patient_id,
            medication_name=medication_name,
            dosage=dosage,
            frequency=frequency,
            duration=f"Take until {end_date}",
            end_date=datetime.strptime(end_date, "%Y-%m-%d"),
            notes=notes,
            status='active'
        )
    else:
        # long-term prescription
        if not refill_date:
            return jsonify({"message": "Refill date is required for long-term prescriptions"}), 400
        try:
            refill_obj = datetime.strptime(refill_date, "%Y-%m-%d").date()
            if refill_obj < todayDate:
                return jsonify({"message": "Refill date cannot be in the past"}), 400
        except ValueError:
            return jsonify({"message": "Invalid refill date format"}), 400

        new_prescription = Prescription(
            doctor_id=doctor_id,
            patient_id=patient_id,
            medication_name=medication_name,
            dosage=dosage,
            frequency=frequency,
            duration=f"Refill due {refill_date}",
            refill_date=refill_date,
            notes=notes,
            status='active'
        )

    db.session.add(new_prescription)
    db.session.commit()

    return jsonify({
        "message": "Prescription created successfully",
        "prescription_id": new_prescription.id
    }), 201


@doctor_routes.route('/prescriptions/<int:prescription_id>', methods=['GET'])
@verify_doctor
def get_prescription(doctor_id, prescription_id):
    """Get prescription details"""
    prescription = Prescription.query.get(prescription_id)

    if not prescription or prescription.doctor_id != doctor_id:
        return jsonify({"message": "Prescription not found or access denied"}), 404

    return jsonify({
        "id": prescription.id,
        "medication": prescription.medication_name,
        "dosage": prescription.dosage,
        "frequency": prescription.frequency,
        "duration": prescription.duration,
        "refill_date": prescription.refill_date,
        "status": prescription.status,
        "start_date": prescription.start_date.isoformat(),
        "end_date": prescription.end_date.isoformat() if prescription.end_date else None,
        "notes": prescription.notes,
        "status_report": prescription.status_report or ''
    }), 200


@doctor_routes.route('/prescriptions/<int:prescription_id>/discontinue', methods=['POST'])
@verify_doctor
def discontinue_prescription(doctor_id, prescription_id):
    """Discontinue a prescription and remove from patient's medication list"""
    prescription = Prescription.query.get(prescription_id)

    if not prescription or prescription.doctor_id != doctor_id:
        return jsonify({"message": "Prescription not found or access denied"}), 404

    # Mark prescription as discontinued
    prescription.status = 'discontinued'
    prescription.end_date = datetime.now()
    prescription.status_report = 'Discontinued by doctor'

    db.session.commit()

    return jsonify({"message": "Prescription discontinued"}), 200


@doctor_routes.route('/prescriptions/<int:patient_id>/active', methods=['GET'])
@verify_doctor
def get_active_prescriptions(doctor_id, patient_id):
    """Get all active prescriptions for a patient"""
    # Verify access
    doctor_patient = DoctorPatient.query.filter_by(
        doctor_id=doctor_id,
        patient_id=patient_id
    ).first()

    if not doctor_patient:
        return jsonify({"message": "Access denied"}), 403

    from datetime import datetime
    now = datetime.now()

    prescriptions = Prescription.query.filter(
        Prescription.patient_id == patient_id,
        Prescription.status.notin_(['discontinued', 'completed']),
        (Prescription.end_date.is_(None) | (Prescription.end_date > now))
    ).all()

    return jsonify({
        "prescriptions": [{
            "id": p.id,
            "medication": p.medication_name,
            "dosage": p.dosage,
            "frequency": p.frequency,
            "duration": p.duration,
            "start_date": p.start_date.isoformat(),
            "status_report": p.status_report or ''
        } for p in prescriptions]
    }), 200


# ==============================
# CONSULTATION NOTES
# ==============================

@doctor_routes.route('/consultation-notes', methods=['POST'])
@verify_doctor
def create_consultation_note(doctor_id):
    """Create a consultation note for a patient"""
    data = request.get_json()
    patient_id = data.get('patient_id')
    observations = data.get('observations')
    treatment_plan = data.get('treatment_plan')
    pain_level = data.get('pain_level')
    physical_exam_notes = data.get('physical_exam_notes')

    # Verify access
    doctor_patient = DoctorPatient.query.filter_by(
        doctor_id=doctor_id,
        patient_id=patient_id
    ).first()

    if not doctor_patient:
        return jsonify({"message": "Patient not assigned to you"}), 403

    if not observations:
        return jsonify({"message": "Observations required"}), 400

    new_note = ConsultationNote(
        doctor_id=doctor_id,
        patient_id=patient_id,
        observations=observations,
        treatment_plan=treatment_plan,
        pain_level=pain_level,
        physical_exam_notes=physical_exam_notes
    )

    db.session.add(new_note)
    db.session.commit()

    return jsonify({
        "message": "Consultation note created",
        "note_id": new_note.id
    }), 201


@doctor_routes.route('/consultation-notes/<int:patient_id>', methods=['GET'])
@verify_doctor
def get_consultation_notes(doctor_id, patient_id):
    """Get consultation notes for a patient"""
    # Verify access
    doctor_patient = DoctorPatient.query.filter_by(
        doctor_id=doctor_id,
        patient_id=patient_id
    ).first()

    if not doctor_patient:
        return jsonify({"message": "Access denied"}), 403

    limit = request.args.get('limit', 20, type=int)

    notes = ConsultationNote.query.filter_by(
        patient_id=patient_id
    ).order_by(ConsultationNote.created_at.desc()).limit(limit).all()

    return jsonify({
        "notes": [{
            "id": n.id,
            "visit_date": n.visit_date.isoformat(),
            "observations": n.observations,
            "treatment_plan": n.treatment_plan,
            "pain_level": n.pain_level,
            "physical_exam_notes": n.physical_exam_notes,
            "created_at": n.created_at.isoformat()
        } for n in notes]
    }), 200


# ==============================
# PATIENT SEARCH & FILTER
# ==============================

@doctor_routes.route('/patients/search', methods=['GET'])
@verify_doctor
def search_patients(doctor_id):
    """Search for patients by name or email"""
    query = request.args.get('q', '').strip()

    if len(query) < 2:
        return jsonify({"message": "Search query too short"}), 400

    # Get doctor's patients
    doctor_patients = db.session.query(
        DoctorPatient).filter_by(doctor_id=doctor_id).all()
    doctor_patient_ids = [dp.patient_id for dp in doctor_patients]

    # Search within those patients
    results = Patient.query.filter(
        Patient.id.in_(doctor_patient_ids),
        (Patient.name.ilike(f"%{query}%")) | (
            Patient.email.ilike(f"%{query}%"))
    ).limit(10).all()

    return jsonify({
        "results": [{
            "patient_id": patient.id,
            "name": patient.name,
            "email": patient.email
        } for patient in results]
    }), 200
