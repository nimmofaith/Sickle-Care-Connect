const API_BASE = "http://127.0.0.1:5000";
let doctorId = null;
let doctorName = null;
let currentFilter = "pending";
let currentPatientId = null;

function getDoctorAuthHeaders() {
    const token = localStorage.getItem('doctor_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
}

const originalFetch = window.fetch.bind(window);
window.fetch = (input, init = {}) => {
    let url = typeof input === 'string' ? input : input.url;
    if (url && url.startsWith(`${API_BASE}/doctor`)) {
        init = init || {};
        init.headers = {
            ...(init.headers || {}),
            ...getDoctorAuthHeaders()
        };
    }
    return originalFetch(input, init);
};

// ==============================
// Validation Functions
// ==============================

function enforceLogin() {
    // Check session validity
    if (!ensureDoctorSession()) {
        return false;
    }

    // Get current doctor info from session
    const currentDoctor = getCurrentDoctor();
    if (!currentDoctor) {
        showSection("loginSection");
        return false;
    }

    // Update global variables
    doctorId = currentDoctor.id;
    doctorName = currentDoctor.name;

    return true;
}

// ==============================
// UNIFIED PRESCRIPTION LOGIC (SHARED)
// ==============================

/**
 * Calculate computed status (NOT stored as "Overdue")
 */
function calculatePrescriptionStatus(prescription) {
    if (!prescription || !prescription.status) {
        return 'active';  // Default to active if no status
    }

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

/**
 * Check if prescription is overdue (NEVER stored)
 */
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

/**
 * Get human-readable instruction (NEVER stored)
 */
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

// ==============================
// Page Load & Navigation
// ==============================

document.addEventListener("DOMContentLoaded", () => {
    // Ensure navigation is hidden initially
    hideNavigation();

    // Check session validity
    if (ensureDoctorSession()) {
        // Session is valid, show logged in view
        const currentDoctor = getCurrentDoctor();
        if (currentDoctor) {
            doctorId = currentDoctor.id;
            doctorName = currentDoctor.name;
            showLoggedInView();
            showSection("dashboardSection");
            loadDashboard();

            // Auto-refresh appointments every 30 seconds
            setInterval(() => {
                if (document.getElementById("appointmentsSection")?.classList.contains("active")) {
                    loadAppointments();
                }
            }, 30000);
        }
    } else {
        showSection("loginSection");
    }

    document.querySelectorAll(".nav-link").forEach(link => {
        link.addEventListener("click", (e) => {
            e.preventDefault();
            if (!enforceLogin()) return;  // Check login first

            const section = link.getAttribute("data-section");
            showSection(section + "Section");

            // Load section data
            if (section === "dashboard") loadDashboard();
            if (section === "patients") loadPatients();
            if (section === "appointments") {
                loadAppointments();
                loadHistory();
            }
        });
    });
});

async function verifyAuthentication(storedDoctorId) {
    try {
        const token = localStorage.getItem('doctor_token');
        const headers = token ? { Authorization: `Bearer ${token}` } : {};
        const response = await fetch(`${API_BASE}/doctor/dashboard`, {
            headers
        });

        if (response.ok) {
            const data = await response.json();
            // Authentication valid, proceed to logged-in state
            doctorName = data?.doctor_name || localStorage.getItem("doctorName");
            if (doctorName) {
                localStorage.setItem("doctorName", doctorName);
            }
            showLoggedInView();
            showSection("dashboardSection");
            loadDashboard();
        } else {
            // Authentication failed, clear storage and show login
            console.log("Authentication verification failed, clearing session");
            clearDoctorSession();
            localStorage.removeItem("doctorSpecialization");
            localStorage.removeItem("hospitalId");
            doctorId = null;
            doctorName = null;
            hideNavigation();
            showSection("loginSection");
        }
    } catch (error) {
        console.error("Authentication verification error:", error);
        // On network error, show login to be safe
        doctorId = null;
        doctorName = null;
        hideNavigation();
        showSection("loginSection");
    }
}

// ==============================
// Authentication
// ==============================

async function handleDoctorLogin(event) {
    event.preventDefault();

    const email = document.getElementById("loginEmail").value;
    const password = document.getElementById("loginPassword").value;

    try {
        const response = await fetch(`${API_BASE}/doctor/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok) {
            doctorId = data.doctor_id;
            doctorName = data.doctor_name || data.name;

            // Use session management instead of direct localStorage
            setDoctorSession(doctorId, doctorName);
            localStorage.setItem("doctor_token", data.token);
            localStorage.setItem("doctorSpecialization", data.specialization);
            localStorage.setItem("hospitalId", data.hospital_id);

            showLoggedInView();
            showSection("dashboardSection");
            loadDashboard();
            showAlert("Login successful!", "success");
        } else {
            showAlert(data.message || "Login failed", "error");
        }
    } catch (error) {
        console.error("Login error:", error);
        showAlert("Login error: " + error.message, "error");
    }
}

async function handleDoctorRegister(event) {
    event.preventDefault();

    const email = document.getElementById("regEmail").value;
    const password = document.getElementById("regPassword").value;
    const confirmPassword = document.getElementById("regConfirmPassword").value;

    // Check if passwords match
    if (password !== confirmPassword) {
        showAlert("Passwords do not match", "error");
        return;
    }

    const formData = {
        email: email,
        password: password,
        confirm_password: confirmPassword
    };

    try {
        const response = await fetch(`${API_BASE}/doctor/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (response.ok) {
            showAlert("Registration successful! Please login.", "success");
            toggleSection("loginSection");
            document.getElementById("registerForm").reset();
        } else {
            showAlert(data.message || "Registration failed", "error");
        }
    } catch (error) {
        console.error("Registration error:", error);
        showAlert("Registration error: " + error.message, "error");
    }
}

function logout() {
    clearDoctorSession();
    localStorage.removeItem("doctorSpecialization");
    localStorage.removeItem("hospitalId");
    doctorId = null;
    doctorName = null;
    hideNavigation();
    showSection("loginSection");
    showAlert("Logged out successfully", "success");
}

// ==============================
// UI Management
// ==============================

function showLoggedInView() {
    const navMenu = document.querySelector(".nav-menu");
    if (navMenu) {
        navMenu.classList.remove("hidden");
    }

    const doctorNameEl = document.getElementById("doctorName");
    if (doctorNameEl) {
        doctorNameEl.textContent = doctorName;
    }

    const doctorSubtitleEl = document.getElementById("doctorSubtitle");
    if (doctorSubtitleEl) {
        doctorSubtitleEl.textContent =
            `${localStorage.getItem("doctorSpecialization")} | Hospital: ${localStorage.getItem("hospitalId")}`;
    }
}

function hideNavigation() {
    const navMenu = document.querySelector(".nav-menu");
    if (navMenu) {
        navMenu.classList.add("hidden");
    }
}

function showSection(sectionId) {
    document.querySelectorAll(".section").forEach(section => {
        section.classList.remove("active");
    });
    document.getElementById(sectionId).classList.add("active");
}

function toggleSection(sectionId) {
    showSection(sectionId);
}

// ==============================
// Dashboard
// ==============================

async function loadDashboard() {
    try {
        const response = await fetch(`${API_BASE}/doctor/dashboard`, {
            headers: getDoctorAuthHeaders()
        });

        if (response.ok) {
            const data = await response.json();

            document.getElementById("totalPatients").textContent = data.total_patients;
            document.getElementById("pendingAppointments").textContent = data.pending_appointments;
            document.getElementById("upcomingAppointments").textContent = data.approved_appointments;
            document.getElementById("activePrescriptions").textContent = data.active_prescriptions;

        }
    } catch (error) {
        console.error("Error loading dashboard:", error);
        showAlert("Error loading dashboard", "error");
    }
}

// ==============================
// Patients Management
// ==============================

async function loadPatients() {
    try {
        const response = await fetch(`${API_BASE}/doctor/patients`, {
            headers: { "X-Doctor-ID": doctorId }
        });

        if (!response.ok) {
            const errText = await response.text();
            console.error(`Error loading patients: ${response.status} ${response.statusText}`, errText);
            showAlert(`Error loading patients: ${response.status}`, "error");
            return;
        }

        const data = await response.json();
        displayPatients(data.patients);
    } catch (error) {
        console.error("Error loading patients:", error);
        showAlert("Error loading patients (network)", "error");
    }
}

function displayPatients(patients) {
    const container = document.getElementById("patientsContainer");
    if (!container) return;


    const patientsArray = Array.isArray(patients) ? patients : [];

    if (patientsArray.length === 0) {
        container.innerHTML = "<p>No patients assigned yet</p>";
        return;
    }

    container.innerHTML = patientsArray.map(patient => `
        <div class="patient-card">
            <div class="card-header">
                <div class="card-title">${patient.name}</div>
                <div class="patient-id">#${patient.patient_id}</div>
            </div>
            <div class="card-details">
                <div class="detail-item">
                    <span class="detail-label">Email:</span>
                    <span>${patient.email}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Phone:</span>
                    <span>${patient.phone || "N/A"}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Genotype:</span>
                    <span>${patient.genotype}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Blood Type:</span>
                    <span>${patient.blood_type}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Assigned:</span>
                    <span>${new Date(patient.assigned_date).toLocaleDateString()}</span>
                </div>
            </div>
            <div class="card-actions">
                <button class="action-btn action-btn-view view-details-btn" data-patient-id="${patient.patient_id}">View Details</button>
            </div>
        </div>
    `).join("");

    container.querySelectorAll('.view-details-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const pid = btn.dataset.patientId;
            viewPatientDetails(pid);
        });
    });
}

async function viewPatientDetails(patientId) {
    if (!patientId) {
        console.error("Invalid patientId passed to viewPatientDetails", patientId);
        showAlert("Unable to load patient details (missing ID)", "error");
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/doctor/patients/${patientId}`, {
            headers: { "X-Doctor-ID": doctorId }
        });

        if (response.ok) {
            const data = await response.json();
            displayPatientDetailsModal(data);
        } else {
            const errData = await response.json().catch(() => ({}));
            showAlert(errData.message || `Error loading patient details (${response.status})`, "error");
        }
    } catch (error) {
        console.error("Error loading patient details:", error);
        showAlert("Error loading patient details: " + error.message, "error");
    }
}

function displayPatientDetailsModal(data) {
    const modal = document.getElementById("patientDetailsView");
    const content = document.getElementById("patientDetailsContent");

    content.innerHTML = `
        <div class="detail-section">
            <h3>Personal Information</h3>
            <div class="detail-row">
                <strong>Name:</strong> <span>${data.patient.name}</span>
            </div>
            <div class="detail-row">
                <strong>Email:</strong> <span>${data.patient.email}</span>
            </div>
            <div class="detail-row">
                <strong>Phone:</strong> <span>${data.patient.phone}</span>
            </div>
        </div>

        <div class="detail-section">
            <h3>Medical Profile - Sickle Cell</h3>
            <div class="detail-row">
                <strong>Genotype:</strong> <span>${data.medical_profile.genotype || "N/A"}</span>
            </div>
            <div class="detail-row">
                <strong>Blood Type:</strong> <span>${data.medical_profile.blood_type || "N/A"}</span>
            </div>
            <div class="detail-row">
                <strong>Allergies:</strong> <span>${data.medical_profile.allergies || "None listed"}</span>
            </div>
            <div class="detail-row">
                <strong>Complications:</strong> <span>${data.medical_profile.complications || "None listed"}</span>
            </div>
        </div>

        <div class="detail-section">
            <h3>Active Prescriptions</h3>
            ${Array.isArray(data.active_prescriptions) && data.active_prescriptions.length > 0 ? `
                <table class="prescriptions-table" style="width: 100%; border-collapse: collapse; margin-top: 1rem;">
                    <thead style="background: #f8f9fa;">
                        <tr>
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Medication</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Dosage</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Frequency</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Instruction</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Status</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.active_prescriptions.map(p => {
        const instruction = getInstructionDisplay(p);
        const isOverdue = isPrescriptionOverdue(p);
        const computedStatus = calculatePrescriptionStatus(p) || 'unknown';
        const statusClass = computedStatus || 'unknown';
        const instructionHtml = isOverdue
            ? `<span style="color: #ff6b6b; font-weight: 600;">${instruction}</span>`
            : instruction;

        return `
                                <tr style="border-bottom: 1px solid #eee;">
                                    <td style="padding: 10px;">${p.medication || p.medication_name || "N/A"}</td>
                                    <td style="padding: 10px;">${p.dosage || "N/A"}</td>
                                    <td style="padding: 10px;">${p.frequency || "N/A"}</td>
                                    <td style="padding: 10px;">${instructionHtml}</td>
                                    <td style="padding: 10px;">
                                        <span class="status-badge status-${statusClass}" style="display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600;">
                                            ${(statusClass || 'unknown').charAt(0).toUpperCase() + (statusClass || 'unknown').slice(1)}
                                        </span>
                                    </td>
                                    <td style="padding: 10px;">
                                        <button type="button" class="action-btn action-btn-decline" onclick="event.stopPropagation(); removePrescription(${p.id || 0})" style="margin: 0; padding: 6px 10px; font-size: 12px;">Remove</button>
                                    </td>
                                </tr>
                            `;
    }).join("")}
                    </tbody>
                </table>
            ` : "<p>No active prescriptions</p>"}
        </div>

        <div class="detail-section">
            <h3>Recent Consultation Notes</h3>
            ${data.recent_notes.length > 0 ? `
                <div style="margin-top: 1rem;">
                    ${data.recent_notes.map(n => `
                        <div class="note-item">
                            <strong>Visit:</strong> ${new Date(n.visit_date).toLocaleDateString()}<br>
                            <strong>Notes:</strong> ${n.observations}
                        </div>
                    `).join("")}
                </div>
            ` : "<p>No consultation notes</p>"}
        </div>

        <div class="detail-section">
            <h3>Appointment History</h3>
            ${data.previous_appointments.length > 0 ? `
                <div style="margin-top: 1rem;">
                    ${data.previous_appointments.map(apt => `
                        <div class="detail-row">
                            <strong>${new Date(apt.date).toLocaleDateString()}</strong>: ${apt.status} ${apt.notes ? `(${apt.notes})` : ''}
                        </div>
                    `).join("")}
                </div>
            ` : "<p>No previous appointments</p>"}
        </div>

        <div class="detail-section">
            <h3>Upcoming Appointments</h3>
            ${data.upcoming_appointments.length > 0 ? `
                <div style="margin-top: 1rem;">
                    ${data.upcoming_appointments.map(apt => `
                        <div class="detail-row">
                            <strong>${new Date(apt.date).toLocaleDateString()}</strong>: ${apt.status} ${apt.notes ? `(${apt.notes})` : ''}
                        </div>
                    `).join("")}
                </div>
            ` : "<p>No upcoming appointments</p>"}
        </div>

        <div class="card-actions" style="margin-top: 2rem;">
            <button class="action-btn action-btn-approve" onclick="openNewConsultationNote(${data.patient.id})">Add Consultation Note</button>
        </div>
    `;

    currentPatientId = data.patient.id;
    modal.classList.remove("hidden");
}

function closePatientDetails() {
    document.getElementById("patientDetailsView").classList.add("hidden");
}

// ==============================
// Prescription Type Toggle
// ==============================

function togglePrescriptionDateField() {
    const prescriptionType = document.querySelector('input[name="prescriptionType"]:checked').value;
    const endDateGroup = document.getElementById("endDateGroup");
    const refillDateGroup = document.getElementById("refillDateGroup");
    const rxEndDate = document.getElementById("rxEndDate");
    const rxRefillDate = document.getElementById("rxRefillDate");

    if (prescriptionType === "short-term") {
        endDateGroup.style.display = "block";
        refillDateGroup.style.display = "none";
        rxEndDate.required = true;
        rxRefillDate.required = false;
    } else {
        endDateGroup.style.display = "none";
        refillDateGroup.style.display = "block";
        rxEndDate.required = false;
        rxRefillDate.required = true;
    }
}

// ==============================
// Patient Search
// ==============================

async function searchPatients() {
    const query = document.getElementById("patientSearch").value;
    if (query.length < 2) {
        document.querySelectorAll(".patient-card").forEach(card => {
            card.style.display = "block";
        });
        return;
    }

    try {
        const response = await fetch(
            `${API_BASE}/doctor/patients/search?q=${encodeURIComponent(query)}`,
            { headers: { "X-Doctor-ID": doctorId } }
        );

        if (response.ok) {
            const data = await response.json();
            const resultIds = new Set(data.results.map(r => r.patient_id));
            const container = document.getElementById("patientsContainer");
            const allCards = container.querySelectorAll(".patient-card");

            allCards.forEach(card => {
                const idText = card.querySelector(".patient-id")?.textContent || "";
                const patientId = parseInt(idText.replace('#', ''), 10);
                card.style.display = resultIds.has(patientId) ? "block" : "none";
            });
        }
    } catch (error) {
        console.error("Search error:", error);
    }
}

// ==============================
// Appointments Management
// ==============================

async function loadAppointments() {
    try {
        const url = currentFilter
            ? `${API_BASE}/doctor/appointments?status=${currentFilter}`
            : `${API_BASE}/doctor/appointments`;

        const response = await fetch(url, {
            headers: getDoctorAuthHeaders()
        });

        if (!response.ok) {
            const errText = await response.text();
            console.error(`Error loading appointments: ${response.status} ${response.statusText}`, errText);
            showAlert(`Error loading appointments: ${response.status}`, "error");
            return;
        }

        const data = await response.json();
        displayAppointments(data.appointments);
    } catch (error) {
        console.error("Error loading appointments:", error);
        showAlert("Error loading appointments (network)", "error");
    }
}

function displayAppointments(appointments) {
    // Ensure appointments is an array
    const appointmentsArray = Array.isArray(appointments) ? appointments : [];
    const now = new Date();
    const filtered = appointmentsArray.filter(apt => {
        // Only show this status type if viewing that filter
        if (apt.status !== currentFilter) return false;
        return true;
    });

    const container = document.getElementById("appointmentsContainer");
    if (!container) return;

    if (filtered.length === 0) {
        container.innerHTML = "<p>No appointments found</p>";
        return;
    }

    container.innerHTML = filtered.map(apt => `
        <div class="appointment-card">
            <div class="card-header">
                <div class="card-title">${apt.patient_name}</div>
                <div class="card-status status-${apt.status}">${apt.status.toUpperCase()}</div>
            </div>
            <div class="card-details">
                <div class="detail-item">
                    <span class="detail-label">Date & Time:</span>
                    <span>${new Date(apt.appointment_date).toLocaleString()}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Patient ID:</span>
                    <span>#${apt.patient_id}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Phone:</span>
                    <span>${apt.patient_phone || "N/A"}</span>
                </div>
            </div>
            ${apt.status === "pending" ? `
                <div class="card-actions">
                    <button class="action-btn action-btn-approve" onclick="approveAppointment(${apt.id})">Approve</button>
                    <button class="action-btn action-btn-decline" onclick="declineAppointment(${apt.id})">Decline</button>
                </div>
            ` : ""}
        </div>
    `).join("");
}

async function loadHistory() {
    try {
        const url = `${API_BASE}/doctor/appointments?status=approved`;

        const response = await fetch(url, {
            headers: getDoctorAuthHeaders()
        });

        if (!response.ok) {
            const errText = await response.text();
            console.error(`Error loading history: ${response.status} ${response.statusText}`, errText);
            return;
        }

        const data = await response.json();
        displayHistory(data.appointments);
    } catch (error) {
        console.error("Error loading history:", error);
    }
}

function displayHistory(appointments) {
    const now = new Date();
    const history = appointments.filter(apt => new Date(apt.appointment_date) < now);

    const container = document.getElementById("historyContainer");

    if (history.length === 0) {
        container.innerHTML = "<p>No appointment history</p>";
        return;
    }

    container.innerHTML = history.map(apt => `
        <div class="appointment-card history-card" onclick="openHistoryDetails(${apt.id})">
            <div class="card-header">
                <div class="card-title">${apt.patient_name}</div>
                <div class="card-status status-completed">COMPLETED</div>
            </div>
            <div class="card-details">
                <div class="detail-item">
                    <span class="detail-label">Date & Time:</span>
                    <span>${new Date(apt.appointment_date).toLocaleString()}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Patient ID:</span>
                    <span>#${apt.patient_id}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Phone:</span>
                    <span>${apt.patient_phone || "N/A"}</span>
                </div>
            </div>
        </div>
    `).join("");
}

function openHistoryDetails(appointmentId) {
    // For now, just alert; later can open modal
    alert(`Opening details for appointment ${appointmentId}`);
}

function filterAppointments(status, event) {
    currentFilter = status;
    document.querySelectorAll(".filter-btn").forEach(btn => {
        btn.classList.remove("active");
    });
    if (event && event.target) {
        event.target.classList.add("active");
    }
    loadAppointments();
}

async function approveAppointment(appointmentId) {
    try {
        const response = await fetch(`${API_BASE}/doctor/appointments/${appointmentId}/approve`, {
            method: "POST",
            headers: { "X-Doctor-ID": doctorId }
        });

        if (response.ok) {
            showAlert("Appointment approved!", "success");
            loadAppointments();
            loadHistory();
        } else {
            const errData = await response.json().catch(() => ({}));
            showAlert(errData.message || `Error approving appointment (${response.status})`, "error");
        }
    } catch (error) {
        console.error("Error approving appointment:", error);
        showAlert("Network error: " + error.message, "error");
    }
}

async function declineAppointment(appointmentId) {
    const reason = prompt("Enter reason for decline:");
    if (!reason) return;

    try {
        const response = await fetch(`${API_BASE}/doctor/appointments/${appointmentId}/decline`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Doctor-ID": doctorId
            },
            body: JSON.stringify({ reason })
        });

        if (response.ok) {
            showAlert("Appointment declined", "success");
            loadAppointments();
        } else {
            const errData = await response.json().catch(() => ({}));
            showAlert(errData.message || `Error declining appointment (${response.status})`, "error");
        }
    } catch (error) {
        console.error("Error declining appointment:", error);
        showAlert("Network error: " + error.message, "error");
    }
}

// ==============================
// Prescriptions Management
// ==============================

async function loadPrescriptions() {
    // Load list of patients for prescription dropdown
    try {
        const response = await fetch(`${API_BASE}/doctor/patients`, {
            headers: { "X-Doctor-ID": doctorId }
        });

        if (response.ok) {
            const data = await response.json();
            const select = document.getElementById("prescriptionPatient");
            select.innerHTML = '<option value="">Select patient...</option>';
            data.patients.forEach(patient => {
                const option = document.createElement("option");
                option.value = patient.patient_id;
                option.textContent = patient.name;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error("Error loading patients for prescriptions:", error);
    }

    // Show prescriptions list (would need additional endpoint)
    const container = document.getElementById("prescriptionsContainer");
    container.innerHTML = "<p>Prescription management interface ready. Click 'New Prescription' to add.</p>";
}

function openNewPrescriptionForm() {
    document.getElementById("newPrescriptionForm").classList.remove("hidden");
}

function openNewPrescriptionForPatient(patientId) {
    document.getElementById("prescriptionPatient").value = patientId;
    document.getElementById("newPrescriptionForm").classList.remove("hidden");
}

function closeNewPrescriptionForm() {
    document.getElementById("newPrescriptionForm").classList.add("hidden");
    document.getElementById("prescriptionForm").reset();
}

async function handleCreatePrescription(event) {
    event.preventDefault();

    const prescriptionData = {
        patient_id: parseInt(document.getElementById("prescriptionPatient").value),
        medication_name: document.getElementById("medicationName").value,
        dosage: document.getElementById("medicineDosage").value,
        frequency: document.getElementById("medicineFrequency").value,
        duration: document.getElementById("medicineDuration").value,
        notes: document.getElementById("medicineNotes").value
    };

    try {
        const response = await fetch(`${API_BASE}/doctor/prescriptions`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Doctor-ID": doctorId
            },
            body: JSON.stringify(prescriptionData)
        });

        const data = await response.json();

        if (response.ok) {
            showAlert("Prescription created successfully!", "success");
            closeNewPrescriptionForm();
            loadPrescriptions();
        } else {
            showAlert(data.message || "Error creating prescription", "error");
        }
    } catch (error) {
        console.error("Error creating prescription:", error);
        showAlert("Error creating prescription: " + error.message, "error");
    }
}

// ==============================
// Consultation Notes
// ==============================

function openNewConsultationNote(patientId) {
    const textarea = prompt("Enter consultation notes:");
    if (!textarea) return;

    createConsultationNote(patientId, textarea);
}

async function createConsultationNote(patientId, observations) {
    try {
        const response = await fetch(`${API_BASE}/doctor/consultation-notes`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Doctor-ID": doctorId
            },
            body: JSON.stringify({
                patient_id: patientId,
                observations: observations,
                pain_level: 5 // Default, could be prompted
            })
        });

        const data = await response.json();
        if (response.ok) {
            showAlert("Consultation note created!", "success");
        } else {
            showAlert(data.message || "Error creating note", "error");
        }
    } catch (error) {
        console.error("Error creating consultation note:", error);
        showAlert("Error creating note", "error");
    }
}

// ==============================
// Prescription Management (for patients)
// ==============================

async function handleCreatePrescriptionForPatient(event) {
    event.preventDefault();

    if (!currentPatientId) {
        showAlert("No patient selected", "error");
        return;
    }

    const prescriptionType = document.querySelector('input[name="prescriptionType"]:checked').value;
    const medicationName = document.getElementById("rxMedicationName").value;
    const dosage = document.getElementById("rxDosage").value;
    const frequency = document.getElementById("rxFrequency").value;
    const notes = document.getElementById("rxNotes").value;

    const todayDate = new Date().toISOString().split('T')[0];

    // Validate based on prescription type
    if (prescriptionType === "short-term") {
        const endDate = document.getElementById("rxEndDate").value;

        if (!endDate) {
            showAlert("End date is required for short-term prescriptions", "error");
            return;
        }

        if (endDate < todayDate) {
            showAlert("End date cannot be in the past", "error");
            return;
        }

        // Create short-term prescription (with end_date)
        const prescriptionData = {
            patient_id: currentPatientId,
            medication_name: medicationName,
            dosage: dosage,
            frequency: frequency,
            end_date: endDate,
            notes: notes,
            prescription_type: "short-term"
        };

        try {
            const response = await fetch(`${API_BASE}/doctor/prescriptions`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-Doctor-ID": doctorId
                },
                body: JSON.stringify(prescriptionData)
            });

            const data = await response.json();

            if (response.ok) {
                showAlert("Short-term prescription created successfully!", "success");
                document.getElementById("patientPrescriptionForm").reset();
                // Refresh patient details modal to show new prescription
                if (currentPatientId) {
                    const patientResponse = await fetch(`${API_BASE}/doctor/patients/${currentPatientId}`, {
                        headers: { "X-Doctor-ID": doctorId }
                    });
                    if (patientResponse.ok) {
                        const data = await patientResponse.json();
                        displayPatientDetailsModal(data);
                    }
                }
            } else {
                showAlert(data.message || "Error creating prescription", "error");
            }
        } catch (error) {
            console.error("Error creating prescription:", error);
            showAlert("Error creating prescription: " + error.message, "error");
        }

    } else {
        // Long-term prescription
        const refillDate = document.getElementById("rxRefillDate").value;

        if (!refillDate) {
            showAlert("Refill date is required for long-term prescriptions", "error");
            return;
        }

        if (refillDate < todayDate) {
            showAlert("Refill date cannot be in the past", "error");
            return;
        }

        // Create long-term prescription (with refill_date)
        const prescriptionData = {
            patient_id: currentPatientId,
            medication_name: medicationName,
            dosage: dosage,
            frequency: frequency,
            refill_date: refillDate,
            notes: notes,
            prescription_type: "long-term"
        };

        try {
            const response = await fetch(`${API_BASE}/doctor/prescriptions`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-Doctor-ID": doctorId
                },
                body: JSON.stringify(prescriptionData)
            });

            const data = await response.json();

            if (response.ok) {
                showAlert("Long-term prescription created successfully!", "success");
                document.getElementById("patientPrescriptionForm").reset();
                // Refresh patient details modal to show new prescription
                if (currentPatientId) {
                    const patientResponse = await fetch(`${API_BASE}/doctor/patients/${currentPatientId}`, {
                        headers: { "X-Doctor-ID": doctorId }
                    });
                    if (patientResponse.ok) {
                        const data = await patientResponse.json();
                        displayPatientDetailsModal(data);
                    }
                }
            } else {
                showAlert(data.message || "Error creating prescription", "error");
            }
        } catch (error) {
            console.error("Error creating prescription:", error);
            showAlert("Error creating prescription: " + error.message, "error");
        }
    }
}

async function removePrescription(prescriptionId) {
    const confirmed = await showConfirmDialog("Remove this prescription?");
    if (!confirmed) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/doctor/prescriptions/${prescriptionId}/discontinue`, {
            method: "POST",
            headers: { "X-Doctor-ID": doctorId }
        });

        if (response.ok) {
            showAlert("Prescription removed", "success");
            if (currentPatientId) {
                const patientResponse = await fetch(`${API_BASE}/doctor/patients/${currentPatientId}`, {
                    headers: { "X-Doctor-ID": doctorId }
                });
                console.log("Patient details refresh status:", patientResponse.status);

                if (patientResponse.ok) {
                    const data = await patientResponse.json();
                    displayPatientDetailsModal(data);
                    console.log("Patient modal updated with new prescription list");
                } else {
                    console.error("Failed to refresh patient details:", patientResponse.status);
                    showAlert("Prescription removed, but patient details refresh failed", "error");
                }
            }
        } else {
            const errData = await response.json().catch(() => ({}));
            console.error("Error response:", errData);
            showAlert(errData.message || `Error removing prescription (${response.status})`, "error");
        }
    } catch (error) {
        console.error("Exception in removePrescription:", error);
        showAlert("Error removing prescription: " + error.message, "error");
    }
}

// ==============================
// Utility Functions
// ==============================

function showConfirmDialog(message) {
    return new Promise((resolve) => {
        // Create custom confirm dialog
        const overlay = document.createElement('div');
        overlay.className = 'confirm-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 2000;
        `;

        const dialog = document.createElement('div');
        dialog.className = 'confirm-dialog';
        dialog.style.cssText = `
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            max-width: 400px;
            width: 90%;
            text-align: center;
        `;

        dialog.innerHTML = `
            <h3 style="margin: 0 0 1rem 0; color: #333;">Confirm Action</h3>
            <p style="margin: 0 0 2rem 0; color: #666;">${message}</p>
            <div style="display: flex; gap: 1rem; justify-content: center;">
                <button class="confirm-yes" style="
                    padding: 0.5rem 1.5rem;
                    background: #dc3545;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-weight: 500;
                ">Remove</button>
                <button class="confirm-no" style="
                    padding: 0.5rem 1.5rem;
                    background: #6c757d;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-weight: 500;
                ">Cancel</button>
            </div>
        `;

        overlay.appendChild(dialog);
        document.body.appendChild(overlay);

        // Handle button clicks
        dialog.querySelector('.confirm-yes').addEventListener('click', () => {
            document.body.removeChild(overlay);
            resolve(true);
        });

        dialog.querySelector('.confirm-no').addEventListener('click', () => {
            document.body.removeChild(overlay);
            resolve(false);
        });

        // Handle clicking outside
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                document.body.removeChild(overlay);
                resolve(false);
            }
        });
    });
}

function showAlert(message, type) {
    // Create a toast notification instead of blocking alert
    const toast = document.createElement('div');
    toast.className = `alert-toast alert-${type}`;
    toast.textContent = `[${type.toUpperCase()}] ${message}`;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        border-radius: 5px;
        background-color: ${type === 'error' ? '#f8d7da' : '#d4edda'};
        color: ${type === 'error' ? '#721c24' : '#155724'};
        border: 1px solid ${type === 'error' ? '#f5c6cb' : '#c3e6cb'};
        z-index: 9999;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        animation: slideIn 0.3s ease;
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Add CSS animations if not already present
if (!document.getElementById('alert-style')) {
    const style = document.createElement('style');
    style.id = 'alert-style';
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
}

function debounce(func, wait) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// ==============================
// Protected Section Navigation
// ==============================

// Close modals when clicking outside
window.onclick = function (event) {
    const patientModal = document.getElementById("patientDetailsView");
    const prescriptionModal = document.getElementById("newPrescriptionForm");

    if (event.target === patientModal) {
        patientModal.classList.add("hidden");
    }
    if (event.target === prescriptionModal) {
        prescriptionModal.classList.add("hidden");
    }
};
