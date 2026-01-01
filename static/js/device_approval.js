(() => {
  const statusUrl = "/auth/device-approval/status";
  const retryBtn = document.getElementById("retry-approval");
  const cancelBtn = document.getElementById("cancel-approval");
  const resendBtn = document.getElementById("resend-approval");
  const statusEl = document.getElementById("approval-status");
  const countdownEl = document.getElementById("approval-countdown");
  const totpCountdownEl = document.getElementById("totp-countdown");
  const hintEl = document.getElementById("approval-hint");
  let polling = false;
  let lastExpiresIn = null;
  let countdownTimer = null;
  let totpTimer = null;

  const showToast = (text, type = "info") => {
    if (typeof Toastify === "function") {
      Toastify({
        text,
        duration: 3500,
        gravity: "top",
        position: "right",
        style: {
          background:
            type === "error" ? "#dc3545" : type === "success" ? "#198754" : "#0dcaf0",
        },
      }).showToast();
    }
  };

  const handleStatus = (data) => {
    if (!data || !data.status) {
      showToast("Unable to confirm device approval.", "error");
      return;
    }

    if (data.status === "ok") {
      if (countdownTimer) {
        clearInterval(countdownTimer);
      }
      if (totpTimer) {
        clearInterval(totpTimer);
      }
      showToast("Device approved. Redirecting...", "success");
      window.location.href = data.redirect || "/";
      return;
    }

    if (data.status === "pending") {
      if (typeof data.expires_in === "number") {
        lastExpiresIn = data.expires_in;
        if (countdownEl) {
          countdownEl.textContent = `Request expires in ${Math.max(0, data.expires_in)} seconds.`;
        }
      }
      if (statusEl) {
        statusEl.textContent = "Waiting for device approval…";
      }
      return;
    }

    if (data.status === "denied" || data.status === "expired") {
      if (statusEl) {
        statusEl.textContent =
          data.status === "expired"
            ? "This approval request expired."
            : "Device approval was denied.";
      }
      if (countdownEl) {
        countdownEl.textContent = "Request expired.";
      }
      if (totpCountdownEl) {
        totpCountdownEl.textContent = "Current TOTP window ended.";
      }
      if (hintEl) {
        hintEl.textContent = "Start again to generate a fresh TOTP and approval request.";
      }
      if (countdownTimer) {
        clearInterval(countdownTimer);
      }
      if (totpTimer) {
        clearInterval(totpTimer);
      }
      showToast("Device approval was denied or expired.", "error");
      return;
    }

    if (data.status === "none") {
      if (statusEl) {
        statusEl.textContent = "No pending device approval found.";
      }
      showToast("No pending device approval found.", "error");
      return;
    }
  };

  const pollStatus = async () => {
    if (polling) {
      return;
    }
    polling = true;
    try {
      const res = await fetch(statusUrl, { credentials: "same-origin" });
      const data = await res.json();
      handleStatus(data);
    } catch (err) {
      showToast("Device approval check failed.", "error");
    } finally {
      polling = false;
    }
  };

  if (retryBtn) {
    retryBtn.addEventListener("click", pollStatus);
  }

  if (resendBtn) {
    resendBtn.addEventListener("click", async () => {
      try {
        const res = await fetch("/auth/device-approval/resend", {
          method: "POST",
          credentials: "same-origin",
        });
        const data = await res.json();
        if (!res.ok) {
          showToast(data.detail || data.error || "Resend failed.", "error");
          return;
        }
        showToast("Approval request resent.", "success");
        if (statusEl) {
          statusEl.textContent = "Waiting for device approval…";
        }
        if (typeof data.expires_in === "number") {
          lastExpiresIn = data.expires_in;
          if (countdownEl) {
            countdownEl.textContent = `Request expires in ${Math.max(0, data.expires_in)} seconds.`;
          }
        }
        if (hintEl) {
          hintEl.textContent = "Approvals must arrive before the current TOTP code expires.";
        }
      } catch (err) {
        showToast("Resend failed.", "error");
      }
    });
  }

  if (cancelBtn) {
    cancelBtn.addEventListener("click", async () => {
      try {
        await fetch("/auth/device-approval/cancel", {
          method: "POST",
          credentials: "same-origin",
        });
      } finally {
        window.location.href = "/auth/verify-totp";
      }
    });
  }

  countdownTimer = setInterval(() => {
    if (typeof lastExpiresIn === "number" && lastExpiresIn > 0) {
      lastExpiresIn -= 1;
      if (countdownEl) {
        countdownEl.textContent = `Request expires in ${Math.max(0, lastExpiresIn)} seconds.`;
      }
    }
  }, 1000);

  const startTotpCountdown = () => {
    if (!totpCountdownEl) {
      return;
    }
    if (totpTimer) {
      clearInterval(totpTimer);
    }
    totpTimer = setInterval(() => {
      const nowSeconds = Math.floor(Date.now() / 1000);
      const remaining = 30 - (nowSeconds % 30);
      totpCountdownEl.textContent = `Current TOTP window ends in ${remaining} seconds.`;
    }, 1000);
  };

  startTotpCountdown();

  setInterval(pollStatus, 2000);
})();
