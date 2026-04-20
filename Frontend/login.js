const loginForm = document.getElementById("loginForm");

// If the patient already has a valid session, send them straight to dashboard
if (localStorage.getItem('patient_id') && localStorage.getItem('session_expiry')) {
    const expiry = Number(localStorage.getItem('session_expiry'));
    if (!isNaN(expiry) && Date.now() < expiry) {
        window.location.href = "dashboard.html";
    } else {
        localStorage.removeItem('patient_id');
        localStorage.removeItem('session_expiry');
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

loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    const loginBtn = document.getElementById("loginBtn");

    if (!email || !password) {
        showAlert("Please fill in all fields", 'error');
        return;
    }

    // Disable button and show loading
    loginBtn.disabled = true;
    loginBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Logging in...';

    // Show loading spinner
    const spinner = document.getElementById("loginSpinner");
    spinner.style.display = "block";

    try {
        const res = await fetch("https://sickle-care-connect.onrender.com/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });

        const data = await res.json();

        if (res.ok) {
            // Clear old user's profile data before logging in new user
            const oldPatientId = localStorage.getItem('patient_id');
            if (oldPatientId) {
                localStorage.removeItem(`profileData_${oldPatientId}`);
            }

            localStorage.setItem("patient_id", data.patient_id);
            localStorage.setItem('patient_token', data.token);
            localStorage.setItem('session_expiry', String(Date.now() + 30 * 60 * 1000));
            window.location.href = "dashboard.html";
        } else {
            showAlert(data.message || "Login failed", 'error');
        }

    } catch (error) {
        console.error(error);
        showAlert("Server error. Please try again later.", 'error');
    } finally {
        // Re-enable button and reset text
        loginBtn.disabled = false;
        loginBtn.innerHTML = 'Login';

        // Hide loading spinner
        spinner.style.display = "none";
    }
});