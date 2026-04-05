// Ensure stale session data is removed before login
localStorage.removeItem('user_id');

const loginForm = document.getElementById("loginForm");

loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    if (!email || !password) {
        alert("Please fill in all fields");
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
            localStorage.setItem("user_id", data.user_id);

            window.location.href = "dashboard.html";
        } else {
            alert(data.message || "Login failed");
        }

    } catch (error) {
        console.error(error);
        alert("Server error. Please try again later.");
    }
});