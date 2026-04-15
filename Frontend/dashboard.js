// ===============================
// SAFE AUTH CHECK
// ===============================
const patientId = localStorage.getItem("patient_id");

if (!ensurePatientSession('login.html')) {
    // If session is missing or expired, ensurePatientSession will redirect.
    throw new Error('Session expired or missing');
}

const user = { id: patientId };

function getAuthHeaders() {
    const token = localStorage.getItem('patient_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
}

// Helper function to handle API responses and check for 401 errors
async function handleApiResponse(response) {
    if (response.status === 401) {
        console.error("DEBUG: Received 401 Unauthorized - token may be expired or invalid");
        clearPatientSession();
        alert('Your session has expired. Please log in again.');
        window.location.href = 'login.html';
        throw new Error('Unauthorized - redirecting to login');
    }
    return response;
}

function getHiddenRescheduleAppointments() {
    try {
        const raw = localStorage.getItem('hidden_reschedule_appointments');
        return raw ? JSON.parse(raw) : [];
    } catch {
        return [];
    }
}

function addHiddenRescheduleAppointment(appointmentId) {
    const hidden = getHiddenRescheduleAppointments();
    if (!hidden.includes(appointmentId)) {
        hidden.push(appointmentId);
        localStorage.setItem('hidden_reschedule_appointments', JSON.stringify(hidden));
    }
}


// ===============================
// DOM ELEMENTS
// ===============================

const medForm = document.getElementById('medForm');
const profileForm = document.getElementById('profileForm');
const profileDisplayGuard = document.getElementById('nameDisplay');


// ===============================
// LOGOUT
// ===============================
document.getElementById('logoutBtn')?.addEventListener('click', () => {
    localStorage.removeItem("patient_id");
    localStorage.removeItem("patient_token");
    window.location.href = 'login.html';
});


// ===============================
// AUTO-COMPLETE PAST APPROVED APPOINTMENTS
// ===============================
async function autoCompletePastAppointments() {
    if (!user.id) return;
    try {
        const res = await fetch(`https://sickle-care-connect.onrender.com/appointments/complete-past/${user.id}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            }
        });
        await handleApiResponse(res);
    } catch (err) {
        if (!err.message.includes('Unauthorized')) {
            console.error("Error auto-completing past appointments:", err);
        }
    }
}


function showAlert(message, type = 'error') {
    const toast = document.createElement('div');
    toast.className = `alert-toast alert-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// ===============================
// DASHBOARD 
// ===============================
async function loadDashboard() {
    try {
        // Auto-complete past approved appointments first
        await autoCompletePastAppointments();

        // Load past appointments for last checkup
        const pastRes = await fetch(`https://sickle-care-connect.onrender.com/appointments/past/${user.id}`, {
            headers: {
                ...getAuthHeaders()
            }
        });

        await handleApiResponse(pastRes);

        if (pastRes.ok) {
            const pastData = await pastRes.json();
            if (pastData.length > 0) {
                document.getElementById('lastCheckup').innerText = pastData[0].preferred_date;
            } else {
                document.getElementById('lastCheckup').innerText = "Not recorded";
            }
        } else {
            document.getElementById('lastCheckup').innerText = "Not recorded";
        }

        // Med count and next appointment are updated in their respective functions
    } catch (err) {
        if (!err.message.includes('Unauthorized')) {
            console.error("Dashboard error:", err);
            showAlert("Unable to load dashboard data.", 'error');
        }
    }
}


// ===============================
// UNIFIED PRESCRIPTION LOGIC
// ===============================

/**
 * Calculate computed status (NOT stored as "Overdue")
 * - Discontinued → "Discontinued"
 * - Active + end_date passed → "Completed"
 * - Otherwise → "Active"
 */
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

/**
 * Check if prescription is overdue (NEVER stored, only calculated)
 * Overdue = has refill_date AND today > refill_date AND status is active
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
 * Get human-readable instruction (NEVER stored, only computed)
 * - If end_date: "Take until {date}"
 * - If refill_date + not overdue: "Refill due {date}"
 * - If refill_date + overdue: "⚠ Refill overdue"
 * - If discontinued: "Discontinued"
 * - Otherwise: "As needed"
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

// ===============================
// LOAD PRESCRIPTIONS (PATIENT VIEW)
// ===============================
async function loadMedications() {
    try {
        const res = await fetch(`https://sickle-care-connect.onrender.com/prescriptions/${user.id}`, {
            headers: {
                ...getAuthHeaders()
            }
        });

        if (!res.ok) {
            console.error("Prescription fetch failed:", res.status);
            document.getElementById('medCount').innerText = `0 active medications`;
            return;
        }

        const data = await res.json();

        // Ensure data is an array
        const prescriptionsArray = Array.isArray(data) ? data : [];

        // Sort by id descending to show latest first
        prescriptionsArray.sort((a, b) => b.id - a.id);

        const container = document.getElementById("medication-list");
        if (!container) return;

        // Filter: only show active prescriptions
        const activePrescriptions = prescriptionsArray.filter(m => calculatePrescriptionStatus(m) === 'active');

        container.innerHTML = "";

        if (activePrescriptions.length === 0) {
            container.innerHTML = `
                <tr>
                    <td colspan="5" style="text-align: center; padding: 20px; color: #666;">No active medications</td>
                </tr>
            `;
            document.getElementById('medCount').innerText = `0 active medications`;
            return;
        }

        activePrescriptions.forEach(m => {
            const instruction = m.duration || getInstructionDisplay(m);
            const isOverdue = isPrescriptionOverdue(m);
            const statusDisplay = isOverdue ? 'Overdue' : 'Active';
            const instructionHtml = isOverdue
                ? `<span style="color: #ff6b6b; font-weight: 600;">${instruction}</span>`
                : instruction;

            // Main medication row
            const rowHtml = `
                <tr>
                    <td>${m.medication_name || ""}</td>
                    <td>${m.dosage || ""}</td>
                    <td>${m.frequency || ""}</td>
                    <td>${instructionHtml}</td>
                    <td>${statusDisplay}</td>
                </tr>
            `;

            container.innerHTML += rowHtml;

            // Notes row for this specific medication (only if notes exist)
            if (m.notes && m.notes.trim()) {
                const notesRowHtml = `
                    <tr style="background-color: #f9f7f4;">
                        <td colspan="5" style="padding: 8px 12px; font-size: 13px; color: #666; border-top: none;">
                            <strong style="color: #800000;">Notes:</strong> ${m.notes}
                        </td>
                    </tr>
                `;
                container.innerHTML += notesRowHtml;
            }
        });

        document.getElementById('medCount').innerText = `${activePrescriptions.length} active medications`;

    } catch (err) {
        console.error("Error loading prescriptions:", err);
        document.getElementById('medCount').innerText = `0 active medications`;
        showAlert("Unable to load medication data.", 'error');
    }
}


// ===============================
// LOAD APPOINTMENTS
// ===============================
async function loadAppointments() {
    try {
        const res = await fetch(`https://sickle-care-connect.onrender.com/appointments/upcoming/${user.id}`, {
            headers: {
                ...getAuthHeaders()
            }
        });

        if (!res.ok) {
            console.error("Appointments fetch failed:", res.status);
            return;
        }

        const data = await res.json();

        // Ensure data is an array
        const appointmentsArray = Array.isArray(data) ? data : [];
        const hiddenIds = getHiddenRescheduleAppointments();
        const visibleAppointments = appointmentsArray.filter(a => !hiddenIds.includes(a.id));

        const container = document.querySelector(".appointment-list");
        if (!container) return;

        container.innerHTML = "";

        if (visibleAppointments.length === 0) {
            container.innerHTML = "<p>No upcoming appointments</p>";
            return;
        }

        visibleAppointments.forEach(a => {
            let actions = "";
            let statusDisplay = a.status || "pending";

            if (a.status === "declined") {
                statusDisplay = `<span style="color: red;">Declined${a.notes ? `: ${a.notes}` : ''}</span>`;
                actions = `<button onclick="rescheduleAppointment(${a.id}, '${encodeURIComponent(a.doctor)}', '${encodeURIComponent(a.hospital)}', '${a.preferred_date}', '${a.preferred_time}', '${a.doctor_id}')">Reschedule</button>`;
            } else if (a.status === "cancelled") {
                statusDisplay = `<span style="color: red;">Cancelled by patient</span>`;
                actions = "";
            } else {
                actions = `<button onclick="cancelAppointment(${a.id})">Cancel</button>`;
            }

            container.innerHTML += `
                <div class="appointment-item">
                    <span>${a.preferred_date}</span>
                    <span>${a.doctor}</span>
                    <span>${a.preferred_time}</span>
                    <span>${statusDisplay}</span>
                    ${actions}
                </div>
            `;
        });

        // Update next appointment using only visible upcoming appointments that are not final
        const upcomingVisible = visibleAppointments.filter(a => a.status !== "declined" && a.status !== "cancelled");
        if (upcomingVisible.length > 0) {
            const next = upcomingVisible[0];
            document.getElementById('nextAppointment').innerText = `${next.preferred_date} with ${next.doctor}`;
        } else {
            document.getElementById('nextAppointment').innerText = "Not scheduled";
        }

    } catch (err) {
        console.error("Error loading appointments:", err);
        showAlert("Unable to load appointment data.", 'error');
    }
}


// ===============================
// RESCHEDULE APPOINTMENT
// ===============================
async function rescheduleAppointment(id, doctor, hospital, date, time, doctorId) {
    if (!confirm("This will remove the declined appointment from your dashboard and open booking with the same doctor. Proceed?")) return;

    addHiddenRescheduleAppointment(id);

    // Save prefill values to make rebooking easier
    localStorage.setItem('reschedule_hospital', decodeURIComponent(hospital));
    localStorage.setItem('reschedule_doctor', decodeURIComponent(doctor));
    localStorage.setItem('reschedule_doctor_id', doctorId);
    localStorage.setItem('reschedule_date', date);
    localStorage.setItem('reschedule_time', time);

    window.location.href = `book appointment.html?hospital=${hospital}&doctor=${doctor}&doctor_id=${doctorId}`;
}


// ===============================
// CANCEL APPOINTMENT
// ===============================
async function cancelAppointment(id) {
    if (!confirm("Are you sure you want to cancel this appointment?")) return;

    try {
        const res = await fetch(`https://sickle-care-connect.onrender.com/appointments`, {
            method: "DELETE",
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify({ appointment_id: id })
        });

        const data = await res.json();
        alert(data.message);

        loadAppointments();

    } catch (err) {
        console.error(err);
    }
}


// ===============================
// LOAD PROFILE 
// ===============================
async function loadProfile() {
    if (!profileDisplayGuard) return;

    try {
        const res = await fetch(`https://sickle-care-connect.onrender.com/profile/${user.id}`, {
            headers: {
                ...getAuthHeaders()
            }
        });

        if (!res.ok) {
            console.error("Profile fetch failed:", res.status);
            return;
        }

        const data = await res.json();

        document.getElementById('nameDisplay').innerText = data.name || "Unknown";
        document.getElementById('emailDisplay').innerText = data.email || "Unknown";
        document.getElementById('genotypeDisplay').innerText = data.genotype || "Not recorded";
        document.getElementById('bloodTypeDisplay').innerText = data.blood_type || "Not recorded";
        document.getElementById('allergiesDisplay').innerText = data.allergies || "Not recorded";
        document.getElementById('complicationsDisplay').innerText = data.complications || "Not recorded";

    } catch (err) {
        console.error(err);
    }
}


// ===============================
// SAVE PROFILE 
// ===============================
if (profileForm) {
    profileForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const data = {
            patient_id: user.id,
            genotype: document.getElementById('genotypeInput').value,
            blood_type: document.getElementById('bloodTypeInput').value,
            allergies: document.getElementById('allergiesInput').value,
            complications: document.getElementById('complicationsInput').value
        };

        console.log("Sending profile data:", data);

        try {
            const res = await fetch('https://sickle-care-connect.onrender.com/profile', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeaders()
                },
                body: JSON.stringify(data)
            });

            console.log("Profile response status:", res.status);

            const result = await res.json();

            console.log("Profile response data:", result);

            if (res.ok) {
                alert(result.message);
                loadProfile();
            } else {
                alert(result.error);
            }

        } catch (err) {
            console.error(err);
            alert("Error saving profile");
        }
    });
}


// ===============================
// INIT
// ===============================
document.addEventListener("DOMContentLoaded", () => {
    loadDashboard();
    loadMedications();
    loadProfile();
    loadAppointments();
});