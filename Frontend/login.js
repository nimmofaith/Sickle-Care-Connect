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

    if (!email || !password) {
        showAlert("Please fill in all fields", 'error');
        return;
    }

    try {
        const res = await fetch("http://127.0.0.1:5000/login", {
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
    }
});