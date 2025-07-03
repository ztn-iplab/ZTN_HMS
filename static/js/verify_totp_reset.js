document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('verify-totp-reset-form');
  if (!form) return;

  const token = form.querySelector('[name="token"]').value;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const password = form.querySelector('[name="password"]').value;

    try {
      const res = await fetch('/auth/verify-fallback-totp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, password }),
        credentials: 'include'
      });

      const data = await res.json();

      // ✅ WebAuthn required → trigger it and return
      if (res.status === 202 && data.require_webauthn) {
        Toastify({
          text: "🔐 WebAuthn required. Please use your security key...",
          duration: 3500,
          gravity: "top",
          position: "right",
          backgroundColor: "#2962ff"
        }).showToast();

        return await triggerWebAuthnFlow(password);  // Will retry backend once passed
      }

      // ❌ Error
      if (!res.ok) {
        Toastify({
          text: `❌ ${data.error || 'Verification failed.'}`,
          duration: 3000,
          gravity: "top",
          position: "right",
          backgroundColor: "#e53935"
        }).showToast();
        return;
      }

      // ✅ Success
      Toastify({
        text: data.message || "✅ TOTP has been reset.",
        duration: 3000,
        gravity: "top",
        position: "right",
        backgroundColor: "#43a047"
      }).showToast();

      form.reset();
      setTimeout(() => window.location.href = "/api/auth/login_form", 2000);

    } catch (err) {
      console.error("Error during verification:", err);
      Toastify({
        text: "❌ Something went wrong.",
        duration: 3000,
        gravity: "top",
        position: "right",
        backgroundColor: "#e53935"
      }).showToast();
    }
  });

  async function triggerWebAuthnFlow(password) {
    try {
      const challengeRes = await fetch('/auth/reset-webauthn-begin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token }),
        credentials: 'include'
      });

      const beginData = await challengeRes.json();
      if (!challengeRes.ok) throw new Error(beginData.error || "Failed to begin WebAuthn reset.");

      const publicKey = {
        ...beginData.public_key,
        challenge: base64urlToUint8Array(beginData.public_key.challenge),
        allowCredentials: beginData.public_key.allowCredentials.map(cred => ({
          ...cred,
          id: base64urlToUint8Array(cred.id)
        }))
      };

      const assertion = await navigator.credentials.get({ publicKey });

      const responsePayload = {
        credentialId: toBase64Url(assertion.rawId),
        authenticatorData: toBase64Url(assertion.response.authenticatorData),
        clientDataJSON: toBase64Url(assertion.response.clientDataJSON),
        signature: toBase64Url(assertion.response.signature),
        userHandle: assertion.response.userHandle
          ? toBase64Url(assertion.response.userHandle)
          : null
      };

      const verifyRes = await fetch('/auth/reset-webauthn-complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(responsePayload),
        credentials: 'include'
      });

      const result = await verifyRes.json();
      if (!verifyRes.ok) throw new Error(result.error || "WebAuthn reset verification failed.");

      // ✅ Now retry the actual reset
      const retry = await fetch('/auth/verify-fallback-totp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, password }),
        credentials: 'include'
      });

      const retryResult = await retry.json();
      if (!retry.ok) throw new Error(retryResult.error || "Final TOTP reset failed.");

      Toastify({
        text: retryResult.message,
        duration: 3000,
        gravity: "top",
        position: "right",
        backgroundColor: "#43a047"
      }).showToast();

      setTimeout(() => window.location.href = "/auth/login", 2000);

    } catch (err) {
      console.error("WebAuthn Error:", err);
      Toastify({
        text: `❌ ${err.message || 'WebAuthn failed.'}`,
        duration: 3000,
        gravity: "top",
        position: "right",
        backgroundColor: "#e53935"
      }).showToast();
    }
  }

  function base64urlToUint8Array(base64urlString) {
    const padding = '='.repeat((4 - base64urlString.length % 4) % 4);
    const base64 = (base64urlString + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = atob(base64);
    return Uint8Array.from([...rawData].map(c => c.charCodeAt(0)));
  }

  function toBase64Url(buffer) {
    return btoa(String.fromCharCode(...new Uint8Array(buffer)))
      .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }
});
