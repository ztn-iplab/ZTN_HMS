// ✅ Auto-refresh access token silently
const AUTO_REFRESH_INTERVAL = 60 * 60 * 1000; // every 5 mins

setInterval(() => {
  fetch("/auth/refresh", {
    method: "POST",
    credentials: "include"
  })
    .then((res) => {
      if (res.ok) {
        console.log("🔁 Hospital token refreshed");
      } else {
        console.warn("⚠️ Refresh failed, redirecting to login...");
        window.location.href = "/auth/login";
      }
    })
    .catch((err) => {
      console.error("❌ Refresh error:", err);
      window.location.href = "/login";
    });
}, AUTO_REFRESH_INTERVAL);
