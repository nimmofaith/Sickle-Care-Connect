from db import db

# ------------------------------
# User Model
# ------------------------------


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    appointments = db.relationship("Appointment", backref="user", lazy=True)


# ------------------------------
# Appointment Model
# ------------------------------
# Appointment Model
# ==============================
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=False)

    hospital = db.Column(db.String(100), nullable=False)
    doctor = db.Column(db.String(100), nullable=False)

    preferred_date = db.Column(db.String(50), nullable=False)
    preferred_time = db.Column(db.String(50), nullable=False)
    # pending, approved, declined, cancelled
    status = db.Column(db.String(50), default='pending')
    notes = db.Column(db.String(300), nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey(
        "doctor.id"), nullable=True)  # Link to doctor


# ------------------------------
# Medication Model
# ------------------------------
class Medication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    doctor_id = db.Column(db.Integer, db.ForeignKey(
        'doctor.id'), nullable=True)  # Only if prescribed by doctor
    medication_name = db.Column(db.String(100))
    dosage = db.Column(db.String(50))
    frequency = db.Column(db.String(50))
    refill_date = db.Column(db.String(50))
    prescribed_by_doctor = db.Column(
        db.Boolean, default=False)  # Track if doctor-prescribed


# ------------------------------
# Symptoms Model
# ------------------------------
class Symptom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    pain_level = db.Column(db.Integer)
    location = db.Column(db.String(100))
    trigger = db.Column(db.String(100))
    relief = db.Column(db.String(100))
    symptoms = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


# ------------------------------
# Medical Profile Model
# ------------------------------
class MedicalProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
    genotype = db.Column(db.String(50))
    blood_type = db.Column(db.String(50))
    allergies = db.Column(db.String(200))
    complications = db.Column(db.String(200))


# ==============================
# DOCTOR PORTAL MODELS
# ==============================

# ------------------------------
# Hospital Model
# ------------------------------
class Hospital(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    address = db.Column(db.String(300), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    doctors = db.relationship("Doctor", backref="hospital", lazy=True)


# ------------------------------
# Doctor Model
# ------------------------------
class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    specialization = db.Column(
        db.String(100), nullable=False)  # e.g., "Hematology"
    license_number = db.Column(db.String(50), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    hospital_id = db.Column(db.Integer, db.ForeignKey(
        'hospital.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Relationships
    doctor_patients = db.relationship(
        "DoctorPatient", backref="doctor", lazy=True, cascade="all, delete-orphan")
    prescriptions = db.relationship(
        "Prescription", backref="doctor", lazy=True)
    consultation_notes = db.relationship(
        "ConsultationNote", backref="doctor", lazy=True)
    doctor_appointments = db.relationship(
        "DoctorAppointment", backref="doctor", lazy=True)


# ------------------------------
# Doctor-Patient Association Model
# (Links patient to multiple doctors)
# ------------------------------
class DoctorPatient(db.Model):
    __tablename__ = 'doctor_patient'
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey(
        'doctor.id'), nullable=False)
    patient_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_date = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Unique constraint: each doctor can only be assigned to a patient once
    __table_args__ = (db.UniqueConstraint(
        'doctor_id', 'patient_id', name='unique_doctor_patient'),)

    patient = db.relationship("User", backref="doctor_assignments")


# ------------------------------
# Doctor Appointment Model (separate from patient appointments)
# (Enhanced appointment scheduling for doctors)
# ------------------------------
class DoctorAppointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey(
        'doctor.id'), nullable=False)
    patient_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    appointment_date = db.Column(db.DateTime, nullable=False)
    # pending, approved, declined, rescheduled, completed
    status = db.Column(db.String(50), default='pending')
    reason = db.Column(db.String(300))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(
    ), onupdate=db.func.current_timestamp())

    patient = db.relationship("User", backref="doctor_appointments")


# ------------------------------
# Prescription Model (Enhanced for doctor tracking)
# ------------------------------
class Prescription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey(
        'doctor.id'), nullable=False)
    patient_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    medication_name = db.Column(db.String(100), nullable=False)
    dosage = db.Column(db.String(50), nullable=False)
    # e.g., "Twice daily"
    frequency = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.String(100), nullable=False)  # e.g., "30 days"
    start_date = db.Column(db.DateTime, default=db.func.current_timestamp())
    end_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    # active, completed, discontinued
    status = db.Column(db.String(50), default='active')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    patient = db.relationship("User", backref="prescriptions")


# ------------------------------
# Consultation Notes Model
# (Doctor observations and follow-ups)
# ------------------------------
class ConsultationNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey(
        'doctor.id'), nullable=False)
    patient_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    visit_date = db.Column(db.DateTime, default=db.func.current_timestamp())
    observations = db.Column(db.Text, nullable=False)
    treatment_plan = db.Column(db.Text)
    pain_level = db.Column(db.Integer)  # 1-10 scale
    physical_exam_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    patient = db.relationship("User", backref="consultation_notes")
