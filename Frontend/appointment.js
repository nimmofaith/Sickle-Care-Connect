// Prevent booking in the past
document.addEventListener("DOMContentLoaded", function () {
    const today = new Date().toISOString().split('T')[0];
    document.getElementById("preferred_date").setAttribute("min", today);
});
const appointmentForm = document.getElementById("appointmentForm");

appointmentForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const patient_id = localStorage.getItem("patient_id");

    const full_name = document.getElementById("full_name").value;
    const phone = document.getElementById("phone").value;
    const email = document.getElementById("email").value;
    const hospital = document.getElementById("hospital").value;
    const doctor = document.getElementById("doctor").value;
    const doctor_id = document.getElementById("doctor_id").value;  // NEW: Get doctor_id
    const preferred_date = document.getElementById("preferred_date").value;
    const preferred_time = document.getElementById("preferred_time").value;


    console.log("Sending appointment data:", {
        patient_id,
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
        const authToken = localStorage.getItem('patient_token');
        const headers = {
            "Content-Type": "application/json"
        };
        if (authToken) {
            headers.Authorization = `Bearer ${authToken}`;
        }

        const res = await fetch("https://sickle-care-connect.onrender.com/appointments", {
            method: "POST",
            headers,
            body: JSON.stringify({
                patient_id,
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