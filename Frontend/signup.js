const signupForm = document.getElementById("signupForm");

function showAlert(message, type = 'error') {
    const toast = document.createElement('div');
    toast.className = `alert-toast alert-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 30000);
}

signupForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const name = document.getElementById("name").value.trim();
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const confirmPassword = document.getElementById("confirmPassword").value;

    if (!name || !email || !password || !confirmPassword) {
        showAlert("Please fill in all fields", 'error');
        return;
    }

    if (password !== confirmPassword) {
        showAlert("Passwords do not match", 'error');
        return;
    }

    try {
        const res = await fetch("https://sickle-care-connect.onrender.com/signup", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, email, password, confirm_password: confirmPassword })
        });

        const data = await res.json();

        if (res.ok) {
            // Clear any old user's profile data from localStorage
            localStorage.removeItem('patient_id');

            // Clear all profile data for any patient
            const keysToRemove = [];
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key && key.startsWith('profileData_')) {
                    keysToRemove.push(key);
                }
            }
            keysToRemove.forEach(key => localStorage.removeItem(key));

            showAlert("Signup successful! Redirecting...", 'success');
            window.location.replace("login.html");
        } else {
            showAlert(data.message || "Signup failed. Please check your input.", 'error');
        }
    } catch (error) {
        console.error("Signup error:", error);
        showAlert("Server unavailable. Please try again later.", 'error');
    }
});