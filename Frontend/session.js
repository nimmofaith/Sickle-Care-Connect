const PATIENT_USER_KEY = 'patient_id';
const PATIENT_SESSION_KEY = 'session_expiry';
const SESSION_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes

function getPatientSessionExpiry() {
    const expiry = localStorage.getItem(PATIENT_SESSION_KEY);
    return expiry ? Number(expiry) : null;
}

function isPatientSessionExpired() {
    const expiry = getPatientSessionExpiry();
    return !expiry || Date.now() > expiry;
}

function clearPatientSession() {
    const patientId = localStorage.getItem(PATIENT_USER_KEY);

    localStorage.removeItem(PATIENT_USER_KEY);
    localStorage.removeItem(PATIENT_SESSION_KEY);
    localStorage.removeItem('patient_token');
    localStorage.removeItem('reschedule_hospital');
    localStorage.removeItem('reschedule_doctor');
    localStorage.removeItem('reschedule_doctor_id');
    localStorage.removeItem('reschedule_date');
    localStorage.removeItem('reschedule_time');

    // Clear profile data for the current patient
    if (patientId) {
        localStorage.removeItem(`profileData_${patientId}`);
    }
}

function setPatientSession(patientId) {
    localStorage.setItem(PATIENT_USER_KEY, patientId);
    localStorage.setItem(PATIENT_SESSION_KEY, String(Date.now() + SESSION_TIMEOUT_MS));
}

function extendPatientSession() {
    if (localStorage.getItem(PATIENT_USER_KEY) && !isPatientSessionExpired()) {
        localStorage.setItem(PATIENT_SESSION_KEY, String(Date.now() + SESSION_TIMEOUT_MS));
    }
}

function ensurePatientSession(redirectTo = 'login.html') {
    const patientId = localStorage.getItem(PATIENT_USER_KEY);

    if (!patientId || isPatientSessionExpired()) {
        if (patientId && isPatientSessionExpired()) {
            alert('Your session has expired. Please log in again.');
        }
        clearPatientSession();

        if (!window.location.href.includes('login.html') && !window.location.href.includes('sign in.html')) {
            window.location.href = redirectTo;
        }
        return false;
    }

    extendPatientSession();
    return true;
}

function logoutPatient() {
    clearPatientSession();
    window.location.href = 'sign in.html';
}

// Apply session enforcement when patient-protected pages load.
document.addEventListener('DOMContentLoaded', () => {
    if (!window.location.href.includes('login.html')) {
        ensurePatientSession();
    }
});
