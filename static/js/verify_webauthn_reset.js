document
  .getElementById("verify-webauthn-reset-form")
  .addEventListener("submit", async (e) => {
    e.preventDefault();

    const form = e.target;
    const token = form.getAttribute("data-token");
    const password = form.password.value.trim();
    const totp = form.totp.value.trim();

    if (!password || !totp) {
      Toastify({
        text: "Password and TOTP code are required.",
        backgroundColor: "#e53935",
        duration: 4000,
      }).showToast();
      return;
    }

    try {
      const response = await fetch("/auth/verify-webauthn-reset", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ token, password, totp }),
        });


      const result = await response.json();

      if (response.ok) {
        Toastify({
          text: result.message || "Passkey reset successful.",
          backgroundColor: "#43a047",
          duration: 4000,
        }).showToast();

        setTimeout(() => {
          window.location.href = "/login";
        }, 1500);
      } else {
        Toastify({
          text: result.error || "Verification failed.",
          backgroundColor: "#e53935",
          duration: 4000,
        }).showToast();
      }
    } catch (err) {
      console.error("Unexpected error:", err);
      Toastify({
        text: "Something went wrong.",
        backgroundColor: "#e53935",
        duration: 4000,
      }).showToast();
    }
  });
