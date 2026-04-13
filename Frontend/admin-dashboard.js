const API_BASE = 'http://127.0.0.1:5000';
let currentToken = null;
let currentSection = 'dashboard';

document.addEventListener('DOMContentLoaded', function () {
    checkAuth();
    setupEventListeners();
    loadDashboardStats();
});

function checkAuth() {
    if (!ensureAdminSession()) {
        return;
    }
    currentToken = getCurrentAdminToken();
}

function logout() {
    clearAdminSession();
    window.location.href = 'admin-login.html';
}

// Event Listeners
function setupEventListeners() {
    // Navigation tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', () => switchSection(tab.dataset.section));
    });

    // Logout
    document.getElementById('logoutBtn').addEventListener('click', logout);

    // Search inputs
    document.getElementById('hospitalsSearch').addEventListener('input', debounce(() => loadHospitals(), 300));
    document.getElementById('doctorsSearch').addEventListener('input', debounce(() => loadDoctors(), 300));
    document.getElementById('patientsSearch').addEventListener('input', debounce(() => loadPatients(), 300));
    document.getElementById('appointmentsSearch').addEventListener('input', debounce(() => loadAppointments(), 300));
    document.getElementById('prescriptionsSearch').addEventListener('input', debounce(() => loadPrescriptions(), 300));

    // Filters
    document.getElementById('doctorsHospitalFilter').addEventListener('change', () => loadDoctors());
    document.getElementById('appointmentsStatusFilter').addEventListener('change', () => loadAppointments());
    document.getElementById('prescriptionsStatusFilter').addEventListener('change', () => loadPrescriptions());

    // Load filter options
    loadHospitalsForFilter();

    // Add buttons
    document.getElementById('addHospitalBtn').addEventListener('click', () => openHospitalModal());
    document.getElementById('addDoctorBtn').addEventListener('click', () => openDoctorModal());

    // Modal close buttons
    document.querySelectorAll('.close-btn, .cancel-btn').forEach(btn => {
        btn.addEventListener('click', () => closeAllModals());
    });

    // Forms
    document.getElementById('hospitalForm').addEventListener('submit', handleHospitalSubmit);
    document.getElementById('doctorForm').addEventListener('submit', handleDoctorSubmit);
    document.getElementById('patientForm').addEventListener('submit', handlePatientSubmit);
    document.getElementById('statusForm').addEventListener('submit', handleStatusSubmit);

    // Close modals on outside click
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeAllModals();
        });
    });
}


function switchSection(section) {
    document.querySelectorAll('.content-section').forEach(sec => {
        sec.style.display = 'none';
    });

    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
    });

    document.getElementById(section + 'Section').style.display = 'block';
    document.querySelector(`[data-section="${section}"]`).classList.add('active');

    currentSection = section;


    switch (section) {
        case 'dashboard':
            loadDashboardStats();
            break;
        case 'hospitals':
            loadHospitals();
            break;
        case 'doctors':
            loadDoctors();
            break;
        case 'patients':
            loadPatients();
            break;
        case 'appointments':
            loadAppointments();
            break;
        case 'prescriptions':
            loadPrescriptions();
            break;
    }
}

async function apiRequest(endpoint, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${currentToken}`
        }
    };

    const response = await fetch(`${API_BASE}${endpoint}`, { ...defaultOptions, ...options });

    if (response.status === 401) {
        logout();
        return;
    }

    return response;
}

async function loadDashboardStats() {
    try {
        const response = await apiRequest('/admin/dashboard/stats');
        const stats = await response.json();

        document.getElementById('totalHospitals').textContent = stats.total_hospitals;
        document.getElementById('totalDoctors').textContent = stats.total_doctors;
        document.getElementById('totalPatients').textContent = stats.total_patients;
        document.getElementById('totalAppointments').textContent = stats.total_appointments;
        document.getElementById('pendingAppointments').textContent = stats.pending_appointments;
        document.getElementById('activePrescriptions').textContent = stats.active_prescriptions;
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
    }
}

// Hospitals management
async function loadHospitals() {
    const container = document.getElementById('hospitalsTableContainer');
    const search = document.getElementById('hospitalsSearch').value;

    container.innerHTML = '<div class="loading">Loading hospitals...</div>';

    try {
        const response = await apiRequest(`/admin/hospitals?search=${encodeURIComponent(search)}`);
        const hospitals = await response.json();

        container.innerHTML = createHospitalsTable(hospitals);
    } catch (error) {
        container.innerHTML = '<div class="error-message">Error loading hospitals</div>';
        console.error('Error loading hospitals:', error);
    }
}

function createHospitalsTable(hospitals) {
    if (hospitals.length === 0) {
        return '<p>No hospitals found.</p>';
    }

    let html = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>City</th>
                    <th>Location</th>
                    <th>Service</th>
                    <th>Notes</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
    `;

    hospitals.forEach(hospital => {
        html += `
            <tr>
                <td>${hospital.name}</td>
                <td>${hospital.city}</td>
                <td>${hospital.location}</td>
                <td>${hospital.service}</td>
                <td>${hospital.notes || ''}</td>
                <td>
                    <button class="btn-secondary" onclick="editHospital(${hospital.id})">Edit</button>
                    <button class="btn-secondary" onclick="deleteHospital(${hospital.id})" style="background: #dc3545;">Delete</button>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    return html;
}

function openHospitalModal(hospital = null) {
    const modal = document.getElementById('hospitalModal');
    const form = document.getElementById('hospitalForm');
    const title = document.getElementById('hospitalModalTitle');

    if (hospital) {
        title.textContent = 'Edit Hospital';
        document.getElementById('hospitalName').value = hospital.name;
        document.getElementById('hospitalCity').value = hospital.city;
        document.getElementById('hospitalLocation').value = hospital.location;
        document.getElementById('hospitalService').value = hospital.service;
        document.getElementById('hospitalNotes').value = hospital.notes || '';
        form.dataset.hospitalId = hospital.id;
    } else {
        title.textContent = 'Add Hospital';
        form.reset();
        delete form.dataset.hospitalId;
    }

    modal.classList.add('show');
}

async function handleHospitalSubmit(e) {
    e.preventDefault();

    const formData = {
        name: document.getElementById('hospitalName').value,
        city: document.getElementById('hospitalCity').value,
        location: document.getElementById('hospitalLocation').value,
        service: document.getElementById('hospitalService').value,
        notes: document.getElementById('hospitalNotes').value
    };

    const hospitalId = e.target.dataset.hospitalId;
    const method = hospitalId ? 'PUT' : 'POST';
    const endpoint = hospitalId ? `/admin/hospitals/${hospitalId}` : '/admin/hospitals';

    try {
        const response = await apiRequest(endpoint, {
            method: method,
            body: JSON.stringify(formData)
        });

        if (response.ok) {
            closeAllModals();
            loadHospitals();
            loadDashboardStats();
            showMessage('Hospital saved successfully!', 'success');
        } else {
            const error = await response.json();
            showMessage(error.message, 'error');
        }
    } catch (error) {
        showMessage('Error saving hospital', 'error');
        console.error('Error saving hospital:', error);
    }
}

async function deleteHospital(id) {
    if (!confirm('Are you sure you want to delete this hospital?')) return;

    try {
        const response = await apiRequest(`/admin/hospitals/${id}`, { method: 'DELETE' });

        if (response.ok) {
            loadHospitals();
            loadDashboardStats();
            showMessage('Hospital deleted successfully!', 'success');
        } else {
            const error = await response.json();
            showMessage(error.message, 'error');
        }
    } catch (error) {
        showMessage('Error deleting hospital', 'error');
        console.error('Error deleting hospital:', error);
    }
}

// Doctors management
async function loadDoctors() {
    const container = document.getElementById('doctorsTableContainer');
    const search = document.getElementById('doctorsSearch').value;
    const hospitalFilter = document.getElementById('doctorsHospitalFilter').value;

    container.innerHTML = '<div class="loading">Loading doctors...</div>';

    try {
        let url = `/admin/doctors?search=${encodeURIComponent(search)}`;
        if (hospitalFilter) url += `&hospital_id=${hospitalFilter}`;

        const response = await apiRequest(url);
        const doctors = await response.json();

        container.innerHTML = createDoctorsTable(doctors);
    } catch (error) {
        container.innerHTML = '<div class="error-message">Error loading doctors</div>';
        console.error('Error loading doctors:', error);
    }
}

function createDoctorsTable(doctors) {
    if (doctors.length === 0) {
        return '<p>No doctors found.</p>';
    }

    let html = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Specialization</th>
                    <th>Hospital</th>
                    <th>License</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
    `;

    doctors.forEach(doctor => {
        html += `
            <tr>
                <td>${doctor.name}</td>
                <td>${doctor.email}</td>
                <td>${doctor.specialization}</td>
                <td>${doctor.hospital_name}</td>
                <td>${doctor.license_number}</td>
                <td>
                    <button class="btn-secondary" onclick="editDoctor(${doctor.id})">Edit</button>
                    <button class="btn-secondary" onclick="deleteDoctor(${doctor.id})" style="background: #dc3545;">Delete</button>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    return html;
}

async function loadHospitalsForFilter() {
    try {
        const response = await apiRequest('/admin/hospitals');
        const hospitals = await response.json();

        const select = document.getElementById('doctorsHospitalFilter');
        select.innerHTML = '<option value="">All Hospitals</option>';

        hospitals.forEach(hospital => {
            select.innerHTML += `<option value="${hospital.id}">${hospital.name}</option>`;
        });
    } catch (error) {
        console.error('Error loading hospitals for filter:', error);
    }
}

async function loadHospitalsForSelect() {
    try {
        const response = await apiRequest('/admin/hospitals');
        const hospitals = await response.json();

        const select = document.getElementById('doctorHospital');
        select.innerHTML = '<option value="">Select Hospital</option>';

        hospitals.forEach(hospital => {
            select.innerHTML += `<option value="${hospital.id}">${hospital.name}</option>`;
        });
    } catch (error) {
        console.error('Error loading hospitals for doctor select:', error);
    }
}

function openDoctorModal(doctor = null) {
    loadHospitalsForSelect();

    const modal = document.getElementById('doctorModal');
    const form = document.getElementById('doctorForm');
    const title = document.getElementById('doctorModalTitle');

    if (doctor) {
        title.textContent = 'Edit Doctor';
        document.getElementById('doctorName').value = doctor.name;
        document.getElementById('doctorEmail').value = doctor.email;
        document.getElementById('doctorSpecialization').value = doctor.specialization;
        document.getElementById('doctorLicense').value = doctor.license_number;
        document.getElementById('doctorHospital').value = doctor.hospital_id;
        form.dataset.doctorId = doctor.id;
    } else {
        title.textContent = 'Add Doctor';
        form.reset();
        delete form.dataset.doctorId;
    }

    modal.classList.add('show');
}

async function handleDoctorSubmit(e) {
    e.preventDefault();

    const formData = {
        name: document.getElementById('doctorName').value,
        email: document.getElementById('doctorEmail').value,
        specialization: document.getElementById('doctorSpecialization').value,
        license_number: document.getElementById('doctorLicense').value,
        hospital_id: document.getElementById('doctorHospital').value
    };

    const doctorId = e.target.dataset.doctorId;
    const method = doctorId ? 'PUT' : 'POST';
    const endpoint = doctorId ? `/admin/doctors/${doctorId}` : '/admin/doctors';

    try {
        const response = await apiRequest(endpoint, {
            method: method,
            body: JSON.stringify(formData)
        });

        if (response.ok) {
            closeAllModals();
            loadDoctors();
            loadDashboardStats();
            showMessage('Doctor saved successfully!', 'success');
        } else {
            const error = await response.json();
            showMessage(error.message, 'error');
        }
    } catch (error) {
        showMessage('Error saving doctor', 'error');
        console.error('Error saving doctor:', error);
    }
}

async function deleteDoctor(id) {
    if (!confirm('Are you sure you want to delete this doctor? This will also delete their user account.')) return;

    try {
        const response = await apiRequest(`/admin/doctors/${id}`, { method: 'DELETE' });

        if (response.ok) {
            loadDoctors();
            loadDashboardStats();
            showMessage('Doctor deleted successfully!', 'success');
        } else {
            const error = await response.json();
            showMessage(error.message, 'error');
        }
    } catch (error) {
        showMessage('Error deleting doctor', 'error');
        console.error('Error deleting doctor:', error);
    }
}

// Patients management
async function loadPatients() {
    const container = document.getElementById('patientsTableContainer');
    if (!container) return;

    const search = document.getElementById('patientsSearch')?.value || '';

    container.innerHTML = '<div class="loading">Loading patients...</div>';

    try {
        const response = await apiRequest(`/admin/patients?search=${encodeURIComponent(search)}`);

        if (!response.ok) {
            container.innerHTML = '<div class="error-message">Failed to load patients</div>';
            console.error(`Error: ${response.status}`);
            return;
        }

        const patients = await response.json();
        const patientsArray = Array.isArray(patients) ? patients : [];
        container.innerHTML = createPatientsTable(patientsArray);
    } catch (error) {
        container.innerHTML = '<div class="error-message">Error loading patients. Please try again.</div>';
        console.error('Error loading patients:', error);
    }
}

function createPatientsTable(patients) {
    if (patients.length === 0) {
        return '<p>No patients found.</p>';
    }

    let html = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Registered On</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
    `;

    patients.forEach(patient => {
        html += `
            <tr>
                <td>${patient.name}</td>
                <td>${patient.email}</td>
                <td>${patient.created_at ? new Date(patient.created_at).toLocaleDateString() : 'N/A'}</td>
                <td>
                    <button class="btn-secondary" onclick="editPatient(${patient.id})">Edit</button>
                    <button class="btn-secondary" onclick="deletePatient(${patient.id})" style="background: #dc3545;">Delete</button>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    return html;
}

function openPatientModal(patient = null) {
    const modal = document.getElementById('patientModal');
    const form = document.getElementById('patientForm');
    const title = document.getElementById('patientModalTitle');

    if (patient) {
        title.textContent = 'Edit Patient';
        document.getElementById('patientName').value = patient.name;
        document.getElementById('patientEmail').value = patient.email;
        document.getElementById('patientPassword').value = '';
        document.getElementById('patientConfirmPassword').value = '';
        form.dataset.patientId = patient.id;
    } else {
        title.textContent = 'Edit Patient';
        form.reset();
        delete form.dataset.patientId;
    }

    modal.classList.add('show');
}

async function handlePatientSubmit(e) {
    e.preventDefault();

    const patientId = e.target.dataset.patientId;
    const formData = {
        name: document.getElementById('patientName').value.trim(),
        email: document.getElementById('patientEmail').value.trim(),
        password: document.getElementById('patientPassword').value,
        confirm_password: document.getElementById('patientConfirmPassword').value
    };

    if (!patientId) {
        showMessage('Patient ID is missing.', 'error');
        return;
    }

    try {
        const response = await apiRequest(`/admin/patients/${patientId}`, {
            method: 'PUT',
            body: JSON.stringify(formData)
        });

        if (response.ok) {
            closeAllModals();
            loadPatients();
            loadDashboardStats();
            showMessage('Patient updated successfully!', 'success');
        } else {
            const error = await response.json();
            showMessage(error.message, 'error');
        }
    } catch (error) {
        showMessage('Error updating patient', 'error');
        console.error('Error updating patient:', error);
    }
}

async function deletePatient(id) {
    if (!confirm('Are you sure you want to delete this patient? This action cannot be undone.')) return;

    try {
        const response = await apiRequest(`/admin/patients/${id}`, { method: 'DELETE' });

        if (response.ok) {
            loadPatients();
            loadDashboardStats();
            showMessage('Patient deleted successfully!', 'success');
        } else {
            const error = await response.json();
            showMessage(error.message, 'error');
        }
    } catch (error) {
        showMessage('Error deleting patient', 'error');
        console.error('Error deleting patient:', error);
    }
}

// Appointments management
async function loadAppointments() {
    const container = document.getElementById('appointmentsTableContainer');
    if (!container) return;

    const search = document.getElementById('appointmentsSearch')?.value || '';
    const statusFilter = document.getElementById('appointmentsStatusFilter')?.value || '';

    container.innerHTML = '<div class="loading">Loading appointments...</div>';

    try {
        let url = `/admin/appointments?search=${encodeURIComponent(search)}`;
        if (statusFilter) url += `&status=${statusFilter}`;

        const response = await apiRequest(url);

        if (!response.ok) {
            container.innerHTML = '<div class="error-message">Failed to load appointments</div>';
            console.error(`Error: ${response.status}`);
            return;
        }

        const appointments = await response.json();
        const appointmentsArray = Array.isArray(appointments) ? appointments : [];
        container.innerHTML = createAppointmentsTable(appointmentsArray);
    } catch (error) {
        container.innerHTML = '<div class="error-message">Error loading appointments. Please try again.</div>';
        console.error('Error loading appointments:', error);
    }
}

function createAppointmentsTable(appointments) {
    if (appointments.length === 0) {
        return '<p>No appointments found.</p>';
    }

    let html = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Patient</th>
                    <th>Doctor</th>
                    <th>Hospital</th>
                    <th>Date</th>
                    <th>Time</th>
                    <th>Status</th>
                    <th>Notes</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
    `;

    appointments.forEach(appointment => {
        const statusClass = `status-${appointment.status}`;
        html += `
            <tr>
                <td>${appointment.full_name}</td>
                <td>${appointment.doctor}</td>
                <td>${appointment.hospital}</td>
                <td>${appointment.preferred_date}</td>
                <td>${appointment.preferred_time}</td>
                <td><span class="status-badge ${statusClass}">${appointment.status}</span></td>
                <td>${appointment.notes || ''}</td>
                <td>
                    <button class="btn-secondary" onclick="updateAppointmentStatus(${appointment.id}, '${appointment.status}')">Update Status</button>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    return html;
}

function updateAppointmentStatus(appointmentId, currentStatus) {
    const modal = document.getElementById('statusModal');
    const form = document.getElementById('statusForm');
    const statusSelect = document.getElementById('statusSelect');

    // Set available statuses based on current status
    statusSelect.innerHTML = `
        <option value="pending" ${currentStatus === 'pending' ? 'selected' : ''}>Pending</option>
        <option value="approved" ${currentStatus === 'approved' ? 'selected' : ''}>Approved</option>
        <option value="declined" ${currentStatus === 'declined' ? 'selected' : ''}>Declined</option>
        <option value="completed" ${currentStatus === 'completed' ? 'selected' : ''}>Completed</option>
        <option value="cancelled" ${currentStatus === 'cancelled' ? 'selected' : ''}>Cancelled</option>
    `;

    document.getElementById('statusNotes').value = '';
    form.dataset.appointmentId = appointmentId;
    form.dataset.type = 'appointment';

    modal.classList.add('show');
}

// Prescriptions management
async function loadPrescriptions() {
    const container = document.getElementById('prescriptionsTableContainer');
    if (!container) return;

    const search = document.getElementById('prescriptionsSearch')?.value || '';
    const statusFilter = document.getElementById('prescriptionsStatusFilter')?.value || '';

    container.innerHTML = '<div class="loading">Loading prescriptions...</div>';

    try {
        let url = `/admin/prescriptions?search=${encodeURIComponent(search)}`;
        if (statusFilter) url += `&status=${statusFilter}`;

        const response = await apiRequest(url);

        if (!response.ok) {
            container.innerHTML = '<div class="error-message">Failed to load prescriptions</div>';
            console.error(`Error: ${response.status}`);
            return;
        }

        const prescriptions = await response.json();
        const prescriptionsArray = Array.isArray(prescriptions) ? prescriptions : [];
        container.innerHTML = createPrescriptionsTable(prescriptionsArray);
    } catch (error) {
        container.innerHTML = '<div class="error-message">Error loading prescriptions. Please try again.</div>';
        console.error('Error loading prescriptions:', error);
    }
}


function calculatePrescriptionStatus(prescription) {
    if (prescription.status === 'discontinued') {
        return 'discontinued';
    }

    if (prescription.status === 'active' && prescription.end_date) {
        if (new Date(prescription.end_date) <= new Date()) {
            return 'completed';
        }
    }

    return prescription.status === 'active' ? 'active' : prescription.status;
}

function isPrescriptionOverdue(prescription) {
    if (!prescription.refill_date || prescription.status === 'discontinued' || prescription.status === 'completed') {
        return false;
    }

    const computedStatus = calculatePrescriptionStatus(prescription);
    if (computedStatus !== 'active') {
        return false;
    }

    return new Date() > new Date(prescription.refill_date);
}


function getInstructionDisplay(prescription) {
    if (prescription.status === 'discontinued') {
        return 'Discontinued';
    }

    if (prescription.end_date) {
        const endDate = new Date(prescription.end_date);
        return `Take until ${endDate.toLocaleDateString()}`;
    }

    if (prescription.refill_date) {
        if (isPrescriptionOverdue(prescription)) {
            return '⚠ Refill overdue';
        }
        const refillDate = new Date(prescription.refill_date);
        return `Refill due ${refillDate.toLocaleDateString()}`;
    }

    return 'As needed';
}

function createPrescriptionsTable(prescriptions) {

    if (!Array.isArray(prescriptions) || prescriptions.length === 0) {
        return '<p>No prescriptions found.</p>';
    }

    let html = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Patient</th>
                    <th>Doctor</th>
                    <th>Medication</th>
                    <th>Dosage</th>
                    <th>Frequency</th>
                    <th>Instruction</th>
                    <th>Status</th>
                    <th>Notes</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
    `;

    prescriptions.forEach(prescription => {
        // Ensure prescription has required fields
        const patientName = prescription.patient_name || 'N/A';
        const doctorName = prescription.doctor_name || 'N/A';
        const medicationName = prescription.medication_name || 'N/A';
        const dosage = prescription.dosage || 'N/A';
        const frequency = prescription.frequency || 'N/A';

        const computedStatus = calculatePrescriptionStatus(prescription);
        const instruction = getInstructionDisplay(prescription);
        const isOverdue = isPrescriptionOverdue(prescription);

        const statusClass = `status-${computedStatus}`;
        const instructionHtml = isOverdue
            ? `<span style="color: #ff6b6b; font-weight: 600;">${instruction}</span>`
            : instruction;

        html += `
            <tr>
                <td>${patientName}</td>
                <td>${doctorName}</td>
                <td>${medicationName}</td>
                <td>${dosage}</td>
                <td>${frequency}</td>
                <td>${instructionHtml}</td>
                <td><span class="status-badge ${statusClass}">${capitalizeFirst(computedStatus)}</span></td>
                <td>${prescription.notes || ''}</td>
                <td>
                    <button class="btn-secondary" onclick="updatePrescriptionStatus(${prescription.id}, '${prescription.status}')">Change Status</button>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    return html;
}

function capitalizeFirst(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function updatePrescriptionStatus(prescriptionId, currentStatus) {
    const modal = document.getElementById('statusModal');
    const form = document.getElementById('statusForm');
    const statusSelect = document.getElementById('statusSelect');

    // Set available statuses for prescriptions
    statusSelect.innerHTML = `
        <option value="active" ${currentStatus === 'active' ? 'selected' : ''}>Active</option>
        <option value="completed" ${currentStatus === 'completed' ? 'selected' : ''}>Completed</option>
        <option value="discontinued" ${currentStatus === 'discontinued' ? 'selected' : ''}>Discontinued</option>
    `;

    document.getElementById('statusNotes').value = '';
    form.dataset.prescriptionId = prescriptionId;
    form.dataset.type = 'prescription';

    modal.classList.add('show');
}

async function handleStatusSubmit(e) {
    e.preventDefault();

    const type = e.target.dataset.type;
    const id = e.target.dataset.appointmentId || e.target.dataset.prescriptionId;
    const status = document.getElementById('statusSelect').value;
    const notes = document.getElementById('statusNotes').value;

    const endpoint = type === 'appointment'
        ? `/admin/appointments/${id}/status`
        : `/admin/prescriptions/${id}/status`;

    try {
        const response = await apiRequest(endpoint, {
            method: 'PUT',
            body: JSON.stringify({ status, notes })
        });

        if (response.ok) {
            closeAllModals();
            if (type === 'appointment') {
                loadAppointments();
            } else {
                loadPrescriptions();
            }
            loadDashboardStats();
            showMessage('Status updated successfully!', 'success');
        } else {
            const error = await response.json();
            showMessage(error.message, 'error');
        }
    } catch (error) {
        showMessage('Error updating status', 'error');
        console.error('Error updating status:', error);
    }
}

// Utility functions
function closeAllModals() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.classList.remove('show');
    });
}

function showMessage(message, type) {
    // Remove existing messages
    document.querySelectorAll('.success-message, .error-message').forEach(msg => msg.remove());

    const messageDiv = document.createElement('div');
    messageDiv.className = type === 'success' ? 'success-message' : 'error-message';
    messageDiv.textContent = message;

    document.querySelector('.admin-container').insertBefore(messageDiv, document.querySelector('.admin-container').firstChild);

    // Auto remove after 5 seconds
    setTimeout(() => {
        messageDiv.remove();
    }, 5000);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Global functions for onclick handlers
window.editHospital = function (id) {
    // Load hospital data and open modal
    apiRequest(`/admin/hospitals`).then(response => response.json()).then(hospitals => {
        const hospital = hospitals.find(h => h.id === id);
        if (hospital) openHospitalModal(hospital);
    });
};

window.deleteHospital = deleteHospital;

window.editDoctor = function (id) {
    // Load doctor data and open modal
    apiRequest(`/admin/doctors`).then(response => response.json()).then(doctors => {
        const doctor = doctors.find(d => d.id === id);
        if (doctor) openDoctorModal(doctor);
    });
};

window.editPatient = function (id) {
    apiRequest(`/admin/patients`).then(response => response.json()).then(patients => {
        const patient = patients.find(p => p.id === id);
        if (patient) openPatientModal(patient);
    });
};

window.deleteDoctor = deleteDoctor;
window.deletePatient = deletePatient;
window.updateAppointmentStatus = updateAppointmentStatus;
window.updatePrescriptionStatus = updatePrescriptionStatus;