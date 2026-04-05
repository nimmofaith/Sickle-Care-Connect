const signupForm = document.getElementById("signupForm");

signupForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const name = document.getElementById("name").value;
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    const confirmPassword = document.getElementById("confirmPassword").value;
    
     if (password !== confirmPassword) {
        alert("Passwords do not match");
        return;
    }
    const res = await fetch("http://127.0.0.1:5000/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password, confirm_password: confirmPassword })
    });

    const data = await res.json();

    if (res.status === 201) {
        alert("Signup successful! Please login.");
        window.location.href = "login.html";
    } else {
        alert(data.message);
    }
});