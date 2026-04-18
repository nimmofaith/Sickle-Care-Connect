// navigation.js - Dynamic navigation for patient side
document.addEventListener('DOMContentLoaded', function () {
    updateNavigation();
});

function updateNavigation() {
    if (typeof ensurePatientSession === 'function') {
        ensurePatientSession();
    }

    const userId = localStorage.getItem("patient_id");
    const navLinks = document.querySelector('.nav-links');

    if (!navLinks) return;

    // Find the login/logout element
    const authElement = navLinks.querySelector('.auth-btn') || navLinks.querySelector('li:last-child');

    if (userId) {
        // User is logged in - show consistent navigation: Home → About → Find Care → Dashboard

        // Replace login button with logout
        if (authElement) {
            authElement.innerHTML = '<button id="logoutBtn" class="btn">Logout</button>';
        }

        // Add Dashboard link before logout if not already present
        const existingDashboard = navLinks.querySelector('a[href="dashboard.html"]');
        if (!existingDashboard) {
            const dashboardLink = document.createElement('li');
            dashboardLink.innerHTML = '<a href="dashboard.html" class="link">Dashboard</a>';
            // Insert before the logout button (authElement)
            navLinks.insertBefore(dashboardLink, authElement);
        }

        // Add logout functionality
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', function () {
                if (typeof clearPatientSession === 'function') {
                    clearPatientSession();
                } else {
                    localStorage.removeItem('patient_id');
                    localStorage.removeItem('session_expiry');
                }
                window.location.href = 'index.html';
            });
        }
    } else {
        // User is not logged in
        if (authElement) {
            authElement.innerHTML = '<a href="login.html" class="btn">Log in</a>';
        }
    }
}