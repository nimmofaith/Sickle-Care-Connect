const appointmentForm = document.getElementById("appointmentForm");

appointmentForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const user_id = localStorage.getItem("user_id");

    const full_name = document.getElementById("full_name").value;
    const phone = document.getElementById("phone").value;
    const email = document.getElementById("email").value;
    const hospital = document.getElementById("hospital").value;
    const doctor = document.getElementById("doctor").value;
    const doctor_id = document.getElementById("doctor_id").value;  // NEW: Get doctor_id
    const preferred_date = document.getElementById("preferred_date").value;
    const preferred_time = document.getElementById("preferred_time").value;

    // Prevent booking in the past
    const todayDate = new Date().toISOString().split('T')[0];
    if (preferred_date < todayDate) {
        alert('Preferred appointment date cannot be in the past');
        return;
    }

    console.log("Sending appointment data:", {
        user_id,
        full_name,
        phone,
        email,
        hospital,
        doctor,
        doctor_id,  // NEW
        preferred_date,
        preferred_time
    });

    try {
        const res = await fetch("http://127.0.0.1:5000/appointments", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                user_id,
                full_name,
                phone,
                email,
                hospital,
                doctor,
                doctor_id,  // NEW: Send doctor_id
                preferred_date,
                preferred_time
            })
        });

        console.log("Response status:", res.status);

        const data = await res.json();

        console.log("Response data:", data);
        if (!res.ok) {
            throw new Error(data.message || "Error occurred");
        }

        alert(data.message);

        appointmentForm.reset();
    } catch (err) {
        console.error("ERROR:", err);
        alert("Failed to book appointment");
    }
});