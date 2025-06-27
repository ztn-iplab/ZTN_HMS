document
  .getElementById("request-webauthn-reset-form")
  .addEventListener("submit", async function (e) {
    e.preventDefault();

    const identifier = this.identifier.value.trim();

    if (!identifier) {
      Toastify({
        text: "Please enter a mobile number or email.",
        backgroundColor: "orange",
        duration: 4000,
      }).showToast();
      return;
    }

    try {
      const res = await fetch("/auth/request-webauthn-reset", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ identifier }),
      });

      const data = await res.json();

      if (res.ok) {
        Toastify({
          text: data.message || "Reset link sent.",
          backgroundColor: "green",
          duration: 4000,
        }).showToast();
        this.reset();
      } else {
        Toastify({
          text: data.error || "Something went wrong.",
          backgroundColor: "red",
          duration: 4000,
        }).showToast();
      }
    } catch (err) {
      Toastify({
        text: "Network error. Please try again.",
        backgroundColor: "red",
        duration: 4000,
      }).showToast();
    }
  });
