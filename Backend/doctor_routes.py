from flask import Blueprint, request, jsonify
from db import db
from models import (
    Doctor, Hospital, DoctorPatient, DoctorAppointment,
    Prescription, ConsultationNote, User, MedicalProfile, Appointment
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps

doctor_routes = Blueprint("doctor_routes", __name__, url_prefix="/doctor")

# ==============================
# Helper function to verify doctor authentication 
# ==============================


def verify_doctor(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        doctor_id_header = request.headers.get('X-Doctor-ID')
        if not doctor_id_header:
            return jsonify({"message": "Doctor ID required in headers"}), 401

        try:
            doctor_id = int(doctor_id_header)
        except ValueError:
            return jsonify({"message": "Invalid Doctor ID"}), 400

        doctor = Doctor.query.get(doctor_id)
        if not doctor:
            return jsonify({"message": "Doctor not found"}), 401

        return f(doctor_id=doctor_id, *args, **kwargs)
    return decorated_function


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
    data = request.get_json()
    name = data.get('name')
    address = data.get('address')
    phone = data.get('phone')
    city = data.get('city')
    state = data.get('state')

    if not all([name, address, phone, city, state]):
        return jsonify({"message": "All fields required"}), 400

    if Hospital.query.filter_by(name=name).first():
        return jsonify({"message": "Hospital already exists"}), 400

    new_hospital = Hospital(
        name=name,
        address=address,
        phone=phone,
        city=city,
        state=state
    )
    db.session.add(new_hospital)
    db.session.commit()

    return jsonify({
        "message": "Hospital created successfully",
        "hospital_id": new_hospital.id
    }), 201


# ==============================
# DOCTOR AUTHENTICATION & REGISTRATION
# ==============================

@doctor_routes.route('/register', methods=['POST'])
def doctor_register():
    """Register a new doctor"""
    data = request.get_json()

    email = data.get('email')
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    license_number = data.get('license_number')
    phone = data.get('phone')
    hospital_name = data.get('hospital_name')

    # Validate required fields
    if not all([email, password, confirm_password, first_name, last_name,
                license_number, phone, hospital_name]):
        return jsonify({"message": "All fields required"}), 400

    # Find or create hospital by name
    hospital = Hospital.query.filter_by(name=hospital_name).first()
    if not hospital:
        # Create new hospital if it doesn't exist
        hospital = Hospital(
            name=hospital_name,
            address="To be updated",
            phone="To be updated",
            city="To be updated",
            state="To be updated"
        )
        db.session.add(hospital)
        db.session.commit()

    # Validate Kenyan phone number
    if not validate_kenyan_phone(phone):
        return jsonify({"message": "Invalid Kenyan phone number. Use format +254XXXXXXXXX or 07XXXXXXXX"}), 400

    if password != confirm_password:
        return jsonify({"message": "Passwords do not match"}), 400

    if Doctor.query.filter_by(email=email).first():
        return jsonify({"message": "Doctor already exists with this email"}), 400

    if Doctor.query.filter_by(license_number=license_number).first():
        return jsonify({"message": "License number already registered"}), 400

    hashed_password = generate_password_hash(password)
    new_doctor = Doctor(
        email=email,
        password=hashed_password,
        first_name=first_name,
        last_name=last_name,
        specialization="Sickle Cell Doctor",  # Fixed specialization
        license_number=license_number,
        phone=phone,
        hospital_id=hospital.id
    )

    db.session.add(new_doctor)
    db.session.commit()

    return jsonify({
        "message": "Doctor registered successfully",
        "doctor_id": new_doctor.id
    }), 201


def validate_kenyan_phone(phone):
    """Validate Kenyan phone number format"""
    import re
    # Accept +254XXXXXXXXX or 07XXXXXXXX format
    pattern = r'^(\+254|0)(7|1|2)[0-9]{8}$'
    return re.match(pattern, phone) is not None
    return jsonify({"message": "Email and password required"}), 400

    doctor = Doctor.query.filter_by(email=email).first()
    if not doctor or not check_password_hash(doctor.password, password):
        return jsonify({"message": "Invalid email or password"}), 401

    return jsonify({
        "message": f"Welcome Dr. {doctor.first_name}!",
        "doctor_id": doctor.id,
        "name": f"{doctor.first_name} {doctor.last_name}",
        "specialization": doctor.specialization,
        "hospital_id": doctor.hospital_id
    }), 200


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

    # Count appointments (pending)
    pending_appointments = db.session.query(DoctorAppointment).filter_by(
        doctor_id=doctor_id,
        status='pending'
    ).count()

    # Count approved appointments
    approved_appointments = db.session.query(DoctorAppointment).filter_by(
        doctor_id=doctor_id,
        status='approved'
    ).count()

    # Count active prescriptions
    active_prescriptions = db.session.query(Prescription).filter_by(
        doctor_id=doctor_id,
        status='active'
    ).count()

    # Recent consultation notes (last 5)
    recent_notes = db.session.query(ConsultationNote).filter_by(
        doctor_id=doctor_id
    ).order_by(ConsultationNote.created_at.desc()).limit(5).all()

    return jsonify({
        "doctor_name": f"{doctor.first_name} {doctor.last_name}",
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
        patient = User.query.get(dp.patient_id)
        if not patient:
            continue
        medical_profile = MedicalProfile.query.filter_by(
            user_id=dp.patient_id).first()

        # Get phone from latest appointment
        phone = None
        latest_appointment = Appointment.query.filter_by(
            user_id=dp.patient_id).order_by(Appointment.id.desc()).first()
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

    patient = User.query.get(patient_id)
    medical_profile = MedicalProfile.query.filter_by(
        user_id=patient_id).first()

    # Get active prescriptions
    prescriptions = Prescription.query.filter_by(
        patient_id=patient_id,
        status='active'
    ).all()

    # Get consultation notes (last 10)
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
            "notes": apt.notes
        } for apt in previous_appointments],
        "upcoming_appointments": [{
            "id": apt.id,
            "date": apt.appointment_date.isoformat(),
            "status": apt.status,
            "notes": apt.notes
        } for apt in upcoming_appointments]
    }), 200


@doctor_routes.route('/patients/<int:patient_id>/search', methods=['GET'])
@verify_doctor
def search_patient(doctor_id, patient_id):
    """Quick search for patient (by name or ID)"""
    # Verify doctor has access
    doctor_patient = DoctorPatient.query.filter_by(
        doctor_id=doctor_id,
        patient_id=patient_id
    ).first()

    if not doctor_patient:
        return jsonify({"message": "Access denied"}), 403

    patient = User.query.get(patient_id)
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
            patient = User.query.get(a.patient_id)
            latest_appointment = Appointment.query.filter_by(
                user_id=a.patient_id).order_by(Appointment.id.desc()).first()
            phone = latest_appointment.phone if latest_appointment else "N/A"

            appointments_data.append({
                "id": a.id,
                "patient_id": a.patient_id,
                "patient_name": patient.name if patient else "Unknown",
                "patient_phone": phone,
                "appointment_date": a.appointment_date.isoformat() if a.appointment_date else None,
                "status": a.status,
                "notes": a.notes or ""
            })

        return jsonify({
            "appointments": appointments_data
        }), 200

    except Exception as e:
        # Return JSON error (CORS decorator still applies on response)
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

    # Mirror status into patient appointment record (if exists)
    patient_appointment = Appointment.query.filter_by(
        user_id=appointment.patient_id,
        doctor_id=appointment.doctor_id,
        preferred_date=appointment.appointment_date.date().isoformat(),
        preferred_time=appointment.appointment_date.strftime('%H:%M')
    ).first()
    if patient_appointment:
        patient_appointment.status = 'approved'
        patient_appointment.notes = 'Approved by doctor'
        db.session.add(patient_appointment)

    # Auto-add patient to doctor's patient list if not already there
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

    # Mirror status into patient appointment record (if exists)
    patient_appointment = Appointment.query.filter_by(
        user_id=appointment.patient_id,
        doctor_id=appointment.doctor_id,
        preferred_date=appointment.appointment_date.date().isoformat(),
        preferred_time=appointment.appointment_date.strftime('%H:%M')
    ).first()

    if patient_appointment:
        patient_appointment.status = 'declined'
        patient_appointment.notes = reason or 'Declined by doctor'
        db.session.add(patient_appointment)
    else:
        # Create a corresponding patient appointment record for audit (declined)
        patient = User.query.get(appointment.patient_id)
        doctor = Doctor.query.get(appointment.doctor_id)

        if patient and doctor:
            new_appointment = Appointment(
                user_id=appointment.patient_id,
                full_name=patient.name,
                phone=patient.phone or "N/A",
                email=patient.email,
                hospital=doctor.hospital_name if doctor.hospital_name else "N/A",
                doctor=f"{doctor.first_name} {doctor.last_name}",
                doctor_id=appointment.doctor_id,
                preferred_date=appointment.appointment_date.date().isoformat(),
                preferred_time=appointment.appointment_date.strftime('%H:%M'),
                status='declined',
                notes=reason or 'Declined by doctor'
            )
            db.session.add(new_appointment)

    # If this doctor has no approved relationship with this patient, remove doctor-patient mapping
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
    refill_date = data.get('refill_date')  # Patient can see refill date
    notes = data.get('notes', '')

    # Verify doctor has access to this patient
    doctor_patient = DoctorPatient.query.filter_by(
        doctor_id=doctor_id,
        patient_id=patient_id
    ).first()

    if not doctor_patient:
        return jsonify({"message": "Patient not assigned to you"}), 403

    if not all([medication_name, dosage, frequency, refill_date]):
        return jsonify({"message": "All fields required"}), 400

    # Validate refill date is not in the past
    try:
        from datetime import datetime as dt, date
        refill_obj = dt.strptime(refill_date, "%Y-%m-%d").date()
        if refill_obj < date.today():
            return jsonify({"message": "Refill date cannot be in the past"}), 400
    except ValueError:
        return jsonify({"message": "Invalid refill date format"}), 400

    new_prescription = Prescription(
        doctor_id=doctor_id,
        patient_id=patient_id,
        medication_name=medication_name,
        dosage=dosage,
        frequency=frequency,
        duration=refill_date,  # Using as refill reference
        notes=notes,
        status='active'
    )

    db.session.add(new_prescription)
    db.session.flush()

    # Also create Medication record visible to patient
    from models import Medication
    medication_record = Medication(
        user_id=patient_id,
        doctor_id=doctor_id,
        medication_name=medication_name,
        dosage=dosage,
        frequency=frequency,
        refill_date=refill_date,
        prescribed_by_doctor=True
    )
    db.session.add(medication_record)
    print(
        f"Created medication record for prescription {new_prescription.id}: {medication_name}, {dosage}, {frequency}")
    db.session.commit()

    return jsonify({
        "message": "Prescription created and sent to patient",
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
        "status": prescription.status,
        "start_date": prescription.start_date.isoformat(),
        "end_date": prescription.end_date.isoformat() if prescription.end_date else None,
        "notes": prescription.notes
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

    # Also remove the corresponding Medication record from patient's view
    from models import Medication
    medication = Medication.query.filter_by(
        user_id=prescription.patient_id,
        medication_name=prescription.medication_name,
        doctor_id=doctor_id,
        prescribed_by_doctor=True
    ).first()

    if medication:
        db.session.delete(medication)

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

    prescriptions = Prescription.query.filter_by(
        patient_id=patient_id,
        status='active'
    ).all()

    return jsonify({
        "prescriptions": [{
            "id": p.id,
            "medication": p.medication_name,
            "dosage": p.dosage,
            "frequency": p.frequency,
            "start_date": p.start_date.isoformat()
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
    results = User.query.filter(
        User.id.in_(doctor_patient_ids),
        (User.name.ilike(f"%{query}%")) | (User.email.ilike(f"%{query}%"))
    ).limit(10).all()

    return jsonify({
        "results": [{
            "patient_id": u.id,
            "name": u.name,
            "email": u.email
        } for u in results]
    }), 200


# ==============================
# DOCTOR LOGIN
# ==============================

@doctor_routes.route('/login', methods=['POST'])
def doctor_login():
    """Login for doctors"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Email and password required"}), 400

    doctor = Doctor.query.filter_by(email=email).first()
    if not doctor or not check_password_hash(doctor.password, password):
        return jsonify({"message": "Invalid email or password"}), 401

    return jsonify({
        "message": f"Welcome Dr. {doctor.first_name}!",
        "doctor_id": doctor.id,
        "name": f"{doctor.first_name} {doctor.last_name}",
        "specialization": doctor.specialization,
        "hospital_id": doctor.hospital_id
    }), 200
