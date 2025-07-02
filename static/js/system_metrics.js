document.addEventListener("DOMContentLoaded", () => {
  fetch("/auth/system-metrics")
    .then(res => res.json())
    .then(data => {
      document.getElementById("total_users").innerText = data.total_users;
      document.getElementById("weekly_logins").innerText = data.logins_last_7_days;
      document.getElementById("active_users").innerText = data.active_users_today;
      document.getElementById("api_calls").innerText = data.api_calls_24h;

      const totpBar = document.getElementById("totp_bar");
      totpBar.style.width = `${data.totp_percent}%`;
      totpBar.innerText = `${data.totp_percent}%`;

      const webauthnBar = document.getElementById("webauthn_bar");
      webauthnBar.style.width = `${data.webauthn_percent}%`;
      webauthnBar.innerText = `${data.webauthn_percent}%`;
    })
    .catch(err => {
      console.error("Failed to load metrics:", err);
    });
});
