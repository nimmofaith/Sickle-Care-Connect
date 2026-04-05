// ===============================
// SAFE AUTH CHECK
// ===============================
const userId = localStorage.getItem("user_id");

if (!userId) {
    alert("User not logged in");
    window.location.href = "sign in.html";
}

// simple user object
const user = { id: userId };


// ===============================
// DOM ELEMENTS
// ===============================
const medForm = document.getElementById('medForm');
const profileForm = document.getElementById('profileForm');


// ===============================
// LOGOUT
// ===============================
document.getElementById('logoutBtn')?.addEventListener('click', () => {
    localStorage.removeItem("user_id");
    window.location.href = 'sign in.html';
});


// ===============================
// AUTO-DELETE PAST APPOINTMENTS
// ===============================
async function autoDeletePastAppointments() {
    try {
        const res = await fetch(`http://127.0.0.1:5000/appointments/${user.id}`);
        if (!res.ok) return;

        const allAppointments = await res.json();
        const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD format

        for (const appt of allAppointments) {
            if (appt.preferred_date < today) {
                // Auto-delete past appointment silently
                await fetch(`http://127.0.0.1:5000/appointments`, {
                    method: "DELETE",
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ appointment_id: appt.id })
                });
            }
        }
    } catch (err) {
        console.error("Error auto-deleting past appointments:", err);
    }
}


// ===============================
// DASHBOARD 
// ===============================
async function loadDashboard() {
    try {
        // Auto-delete past appointments first
        await autoDeletePastAppointments();

        // Load past appointments for last checkup
        const pastRes = await fetch(`http://127.0.0.1:5000/appointments/past/${user.id}`);
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
        console.error("Dashboard error:", err);
    }
}


// ===============================
// ADD MEDICATION - DISABLED
// ===============================
// Medications are now managed by doctors only
// Patients cannot add their own medications


// ===============================
// LOAD PRESCRIPTIONS 
// ===============================
async function loadMedications() {
    try {
        const res = await fetch(`http://127.0.0.1:5000/prescriptions/${user.id}`);

        if (!res.ok) {
            console.error("Prescription fetch failed:", res.status);
            return;
        }

        const data = await res.json();

        // Sort by id descending to show latest first
        data.sort((a, b) => b.id - a.id);

        const container = document.getElementById("medication-list");
        if (!container) return;

        container.innerHTML = "";

        if (!Array.isArray(data) || data.length === 0) {
            container.innerHTML = "<p>No prescriptions yet</p>";
            return;
        }

        data.forEach(m => {
            container.innerHTML += `
        <tr>
            <td>${m.medication_name || ""}</td>
            <td>${m.dosage || ""}</td>
            <td>${m.frequency || ""}</td>
            <td>${m.duration || ""}</td>
        </tr>
        ${m.notes ? `<tr class="notes-row"><td colspan="4" class="notes-cell"><strong>Notes:</strong> ${m.notes}</td></tr>` : ''}
       `;
        });

        // Update med count
        document.getElementById('medCount').innerText = `${data.length} medications`;

    } catch (err) {
        console.error("Error loading prescriptions:", err);
    }
}


// ===============================
// LOAD APPOINTMENTS
// ===============================
async function loadAppointments() {
    try {
        const res = await fetch(`http://127.0.0.1:5000/appointments/upcoming/${user.id}`);

        if (!res.ok) {
            console.error("Appointments fetch failed:", res.status);
            return;
        }

        const data = await res.json();

        const container = document.querySelector(".appointment-list");
        if (!container) return;

        container.innerHTML = "";

        if (!data || data.length === 0) {
            container.innerHTML = "<p>No appointments yet</p>";
            return;
        }

        data.forEach(a => {
            let actions = "";
            let statusDisplay = a.status;

            if (a.status === "declined") {
                statusDisplay = `<span style="color: red;">Declined${a.notes ? `: ${a.notes}` : ''}</span>`;
                actions = `<button onclick="rescheduleAppointment(${a.id}, '${encodeURIComponent(a.doctor)}', '${encodeURIComponent(a.hospital)}', '${a.preferred_date}', '${a.preferred_time}', '${a.doctor_id}')">Reschedule</button>`;
            } else if (a.status === "cancelled") {
                // Cancelled by patient should not show in upcoming (filtered backend), but just in case
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

        // Update next appointment (only if approved or pending)
        const upcomingApproved = data.filter(a => a.status !== "declined");
        if (upcomingApproved.length > 0) {
            const next = upcomingApproved[0]; // Assuming sorted by date
            document.getElementById('nextAppointment').innerText = `${next.preferred_date} with ${next.doctor}`;
        } else {
            document.getElementById('nextAppointment').innerText = "Not scheduled";
        }

    } catch (err) {
        console.error("Error loading appointments:", err);
    }
}


// ===============================
// RESCHEDULE APPOINTMENT
// ===============================
async function rescheduleAppointment(id, doctor, hospital, date, time, doctorId) {
    if (!confirm("This will cancel the declined appointment and open booking with the same doctor. Proceed?")) return;

    try {
        // Cancel old declined appointment
        await fetch(`http://127.0.0.1:5000/appointments`, {
            method: "DELETE",
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ appointment_id: id })
        });

        // Save prefill values to make rebooking easier
        localStorage.setItem('reschedule_hospital', decodeURIComponent(hospital));
        localStorage.setItem('reschedule_doctor', decodeURIComponent(doctor));
        localStorage.setItem('reschedule_doctor_id', doctorId);
        localStorage.setItem('reschedule_date', date);
        localStorage.setItem('reschedule_time', time);

        window.location.href = `book appointment.html?hospital=${hospital}&doctor=${doctor}&doctor_id=${doctorId}`;
    } catch (err) {
        console.error(err);
        alert('Failed to reschedule appointment');
    }
}


// ===============================
// CANCEL APPOINTMENT
// ===============================
async function cancelAppointment(id) {
    if (!confirm("Are you sure you want to cancel this appointment?")) return;

    try {
        const res = await fetch(`http://127.0.0.1:5000/appointments`, {
            method: "DELETE",
            headers: { 'Content-Type': 'application/json' },
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
    try {
        const res = await fetch(`http://127.0.0.1:5000/profile/${user.id}`);

        if (!res.ok) {
            console.error("Profile fetch failed:", res.status);
            return;
        }

        const data = await res.json();

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
            user_id: user.id,
            genotype: document.getElementById('genotypeInput').value,
            blood_type: document.getElementById('bloodTypeInput').value,
            allergies: document.getElementById('allergiesInput').value,
            complications: document.getElementById('complicationsInput').value
        };

        console.log("Sending profile data:", data);

        try {
            const res = await fetch('http://127.0.0.1:5000/profile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
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