const ADMIN_TOKEN_KEY = 'adminToken';
const ADMIN_SESSION_KEY = 'admin_session_expiry';
const ADMIN_SESSION_TIMEOUT_MS = 60 * 60 * 1000; // 60 minutes (admins get longer sessions)

function getAdminSessionExpiry() {
    const expiry = localStorage.getItem(ADMIN_SESSION_KEY);
    return expiry ? Number(expiry) : null;
}

function isAdminSessionExpired() {
    const expiry = getAdminSessionExpiry();
    return !expiry || Date.now() > expiry;
}

function clearAdminSession() {
    localStorage.removeItem(ADMIN_TOKEN_KEY);
    localStorage.removeItem(ADMIN_SESSION_KEY);
}

function setAdminSession(token) {
    localStorage.setItem(ADMIN_TOKEN_KEY, token);
    localStorage.setItem(ADMIN_SESSION_KEY, String(Date.now() + ADMIN_SESSION_TIMEOUT_MS));
}

function extendAdminSession() {
    if (localStorage.getItem(ADMIN_TOKEN_KEY) && !isAdminSessionExpired()) {
        localStorage.setItem(ADMIN_SESSION_KEY, String(Date.now() + ADMIN_SESSION_TIMEOUT_MS));
    }
}

function ensureAdminSession(redirectTo = 'admin-login.html') {
    const token = localStorage.getItem(ADMIN_TOKEN_KEY);

    if (!token || isAdminSessionExpired()) {
        if (token && isAdminSessionExpired()) {
            alert('Your session has expired. Please log in again.');
        }
        clearAdminSession();

        if (!window.location.href.includes('admin-login.html')) {
            window.location.href = redirectTo;
        }
        return false;
    }

    // Extend session on activity
    extendAdminSession();
    return true;
}

function getCurrentAdminToken() {
    const token = localStorage.getItem(ADMIN_TOKEN_KEY);

    if (!token || isAdminSessionExpired()) {
        return null;
    }

    return token;
}