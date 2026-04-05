// navigation.js - Dynamic navigation for patient side
document.addEventListener('DOMContentLoaded', function () {
    updateNavigation();
});

function updateNavigation() {
    const userId = localStorage.getItem("user_id");
    const navLinks = document.querySelector('.nav-links');

    if (!navLinks) return;

    // Find the login/logout element
    const authElement = navLinks.querySelector('.auth-btn') || navLinks.querySelector('li:last-child');

    if (userId) {
        // User is logged in
        const dashboardLink = document.createElement('li');
        dashboardLink.innerHTML = '<a href="dashboard.html" class="link">Dashboard</a>';

        // Replace login button with dashboard and logout
        if (authElement) {
            authElement.innerHTML = '<button id="logoutBtn" class="btn">Logout</button>';
        }

        // Add dashboard link if not already present
        const existingDashboard = navLinks.querySelector('a[href="dashboard.html"]');
        if (!existingDashboard) {
            // Insert dashboard link before the last item (logout)
            navLinks.insertBefore(dashboardLink, authElement);
        }

        // Add logout functionality
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', function () {
                // Clear all session-local data to avoid stale profile carryover
                localStorage.clear();
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