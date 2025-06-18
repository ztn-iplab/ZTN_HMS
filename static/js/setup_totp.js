document.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("qr-container");
  const manualKey = document.getElementById("manual-key");
  const continueBtn = document.getElementById("confirm-totp-btn");

  console.log("📡 Fetching /setup-totp via backend proxy...");

  fetch("/auth/setup-totp", {
    method: "GET",
    credentials: "same-origin",
  })
    .then(async (res) => {
      const rawText = await res.text();
      let data;

      try {
        data = JSON.parse(rawText);
      } catch (err) {
        console.error("❌ Failed to parse JSON:", err);
        console.error("Raw response was:", rawText);
        throw new Error("Invalid response.");
      }

      if (!res.ok) throw new Error(data.error || "Failed to setup TOTP");

      if (data.qr_code) {
        const img = document.createElement("img");
        img.src = data.qr_code;
        img.alt = "TOTP QR Code";
        img.style.maxWidth = "200px";
        img.style.height = "auto";
        img.classList.add("img-fluid", "border", "rounded", "shadow-sm", "mb-2");

        container.innerHTML = "";
        container.appendChild(img);
        manualKey.innerText = data.manual_key;
      } else {
        container.innerHTML = `<p>${data.message || "TOTP already set up."}</p>`;
        manualKey.innerText = "-";
      }
    })
    .catch((err) => {
      console.error("❌ Error:", err);
      container.innerHTML = `<p style="color:red;">${err.message}</p>`;
      manualKey.innerText = "-";
    });

  continueBtn.addEventListener("click", async () => {
    const confirm = window.confirm("✅ Have you scanned the QR or added the key?");
    if (!confirm) return;

    continueBtn.disabled = true;
    continueBtn.textContent = "Confirming...";

    try {
      const res = await fetch("/auth/setup-totp/confirm", {
        method: "POST",
        credentials: "same-origin"
      });

      const data = await res.json();
      if (res.ok) {
        Toastify({
          text: "✅ TOTP setup confirmed!",
          duration: 3000,
          gravity: "top",
          position: "center",
          backgroundColor: "#43a047",
        }).showToast();
        setTimeout(() => {
          window.location.href = "/verify-totp"; // or your protected page
        }, 1500);
      } else {
        throw new Error(data.error || "Confirmation failed");
      }
    } catch (err) {
      Toastify({
        text: err.message,
        duration: 4000,
        gravity: "top",
        position: "center",
        backgroundColor: "red",
      }).showToast();
      continueBtn.disabled = false;
      continueBtn.textContent = "Continue";
    }
  });
});
