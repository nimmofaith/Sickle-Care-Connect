const DOCTOR_USER_KEY = 'doctor_id';
const DOCTOR_NAME_KEY = 'doctor_name';
const DOCTOR_SESSION_KEY = 'doctor_session_expiry';
const DOCTOR_SESSION_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes

function getDoctorSessionExpiry() {
    const expiry = localStorage.getItem(DOCTOR_SESSION_KEY);
    return expiry ? Number(expiry) : null;
}

function isDoctorSessionExpired() {
    const expiry = getDoctorSessionExpiry();
    return !expiry || Date.now() > expiry;
}

function clearDoctorSession() {
    localStorage.removeItem(DOCTOR_USER_KEY);
    localStorage.removeItem(DOCTOR_NAME_KEY);
    localStorage.removeItem(DOCTOR_SESSION_KEY);
    localStorage.removeItem('doctor_token');
}

function setDoctorSession(doctorId, doctorName, token) {
    localStorage.setItem(DOCTOR_USER_KEY, doctorId);
    localStorage.setItem(DOCTOR_NAME_KEY, doctorName);
    localStorage.setItem(DOCTOR_SESSION_KEY, String(Date.now() + DOCTOR_SESSION_TIMEOUT_MS));
    localStorage.setItem('doctor_token', token);
}

function extendDoctorSession() {
    if (localStorage.getItem(DOCTOR_USER_KEY) && !isDoctorSessionExpired()) {
        localStorage.setItem(DOCTOR_SESSION_KEY, String(Date.now() + DOCTOR_SESSION_TIMEOUT_MS));
    }
}

function ensureDoctorSession(redirectTo = 'doctor-portal.html') {
    const doctorId = localStorage.getItem(DOCTOR_USER_KEY);

    if (!doctorId || isDoctorSessionExpired()) {
        if (doctorId && isDoctorSessionExpired()) {
            alert('Your session has expired. Please log in again.');
        }
        clearDoctorSession();

        if (!window.location.href.includes('doctor-portal.html')) {
            window.location.href = redirectTo;
        }
        return false;
    }

    // Extend session on activity
    extendDoctorSession();
    return true;
}

function getCurrentDoctor() {
    const doctorId = localStorage.getItem(DOCTOR_USER_KEY);
    const doctorName = localStorage.getItem(DOCTOR_NAME_KEY);

    if (!doctorId || isDoctorSessionExpired()) {
        return null;
    }

    return {
        id: doctorId,
        name: doctorName
    };
}