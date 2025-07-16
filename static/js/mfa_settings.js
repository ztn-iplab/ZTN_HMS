document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("mfaPreferenceForm");

  //  MFA Preference Update (all users)
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const selected = document.getElementById("preferred_mfa").value;

    try {
      const res = await fetch("/auth/update-mfa-preference", {
        method: "PUT",
        credentials: "include",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ preferred_mfa: selected })
      });

      const result = await res.json();

      if (res.ok) {
        Toastify({
          text: "✅ Preference updated successfully.",
          duration: 3000,
          close: true,
          gravity: "top",
          position: "right",
          backgroundColor: "#28a745"
        }).showToast();
      } else {
        Toastify({
          text: "❌ " + (result.error || "Failed to update."),
          duration: 4000,
          close: true,
          gravity: "top",
          position: "right",
          backgroundColor: "#dc3545"
        }).showToast();
      }

    } catch (err) {
      Toastify({
        text: "❌ Update failed. Please try again.",
        duration: 4000,
        close: true,
        gravity: "top",
        position: "right",
        backgroundColor: "#dc3545"
      }).showToast();
    }
  });

  //  Admin-only: Enforce MFA for all users
  const enforceSwitch = document.getElementById("enforce_mfa_switch");

  if (enforceSwitch) {
    // Load current enforcement state
    fetch("/auth/enforce-mfa-policy", { credentials: "include" })
      .then(res => res.json())
      .then(data => {
        enforceSwitch.checked = data.enforce_strict_mfa;
      })
      .catch(err => {
        console.error("Failed to load MFA policy", err);
      });

    // Handle admin toggle change
    enforceSwitch.addEventListener("change", async () => {
      try {
        const res = await fetch("/auth/enforce-mfa-policy", {
          method: "PUT",
          credentials: "include",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ enforce_strict_mfa: enforceSwitch.checked })
        });

        const result = await res.json();

        if (!res.ok) throw new Error(result.error || "Failed to update policy");

        Toastify({
          text: "✅ MFA enforcement updated.",
          duration: 3000,
          close: true,
          gravity: "top",
          position: "right",
          backgroundColor: "#28a745"
        }).showToast();

      } catch (err) {
        Toastify({
          text: "❌ " + err.message,
          duration: 4000,
          close: true,
          gravity: "top",
          position: "right",
          backgroundColor: "#dc3545"
        }).showToast();
        enforceSwitch.checked = !enforceSwitch.checked;  // revert switch if failed
      }
    });
  }
});
