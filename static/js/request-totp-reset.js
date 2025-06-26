document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("request-totp-reset-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const identifier = form.querySelector("#identifier").value.trim();
    if (!identifier) {
      showToast("❌ Please enter your email or mobile number.", "error");
      return;
    }

    try {
      const res = await fetch("/auth/request-totp-reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identifier }),
        credentials: "include"
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error);

      showToast("✅ " + data.message, "success");
      form.reset();

    } catch (err) {
      console.error("TOTP Reset Request Error:", err);
      showToast(`❌ ${err.message || "Failed to request TOTP reset."}`, "error");
    }
  });

  function showToast(message, type = "info") {
    Toastify({
      text: message,
      duration: 3000,
      gravity: "top",
      position: "right",
      backgroundColor:
        type === "success"
          ? "#43a047"
          : type === "error"
          ? "#e53935"
          : "#2962ff"
    }).showToast();
  }
});
