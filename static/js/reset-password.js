document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('reset-password-form');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const newPassword = form.querySelector('[name="new_password"]').value.trim();
    const confirmPassword = form.querySelector('[name="confirm_password"]').value.trim();
    const token = form.querySelector('[name="token"]').value.trim();

    if (newPassword !== confirmPassword) {
      showToast("❌ Passwords do not match.", "error");
      return;
    }

    if (!isStrongPassword(newPassword)) {
      showToast("❌ Password too weak. Must be at least 8 characters with uppercase, lowercase, digit, and special character.", "error");
      return;
    }

    try {
      const res = await fetch('/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: newPassword, confirm_password: confirmPassword }),
      });

      const data = await res.json();

      if (res.status === 202 && data.require_webauthn) {
        showToast("🔐 WebAuthn verification required before reset.", "info");
        return await verifyWithWebAuthn(token, newPassword, confirmPassword);
      }

      if (res.status === 202 && data.require_totp) {
        showToast("🔐 TOTP verification required before reset.", "info");
        return await verifyWithTotp(token, newPassword, confirmPassword);
      }

      if (!res.ok) {
        showToast(`❌ ${data.error || 'Password reset failed.'}`, "error");
        return;
      }

      showToast("✅ " + data.message, "success");
      form.reset();
      setTimeout(() => {
        window.location.href = "/login";
      }, 2000);

    } catch (err) {
      console.error("Password Reset Error:", err);
      showToast("❌ Something went wrong. Please try again.", "error");
    }
  });

  async function verifyWithWebAuthn(token, newPassword, confirmPassword) {
    try {
      const beginRes = await fetch('/auth/reset-webauthn-begin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token }),
        credentials: 'include'
      });

      const beginData = await beginRes.json();
      if (!beginRes.ok) throw new Error(beginData.error);

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

      const completeRes = await fetch('/auth/reset-webauthn-complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, ...responsePayload }),
        credentials: 'include'
      });

      const completeData = await completeRes.json();
      if (!completeRes.ok) throw new Error(completeData.error);

      return await retryPasswordReset(token, newPassword, confirmPassword);

    } catch (err) {
      console.error("WebAuthn Verification Error:", err);
      showToast(`❌ ${err.message || 'WebAuthn failed.'}`, "error");
    }
  }

  async function verifyWithTotp(token, newPassword, confirmPassword) {
    const code = prompt("Enter your TOTP code to confirm your identity:");
    if (!code) return;

    try {
      const res = await fetch('/auth/verify-fallback-totp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, code }),
        credentials: 'include'
      });

      const result = await res.json();
      if (!res.ok) throw new Error(result.error || "TOTP verification failed.");

      return await retryPasswordReset(token, newPassword, confirmPassword);

    } catch (err) {
      console.error("TOTP Verification Error:", err);
      showToast(`❌ ${err.message || 'TOTP verification failed.'}`, "error");
    }
  }

  async function retryPasswordReset(token, newPassword, confirmPassword) {
    const retryRes = await fetch('/auth/reset-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, new_password: newPassword, confirm_password: confirmPassword }),
    });

    const retryData = await retryRes.json();
    if (!retryRes.ok) throw new Error(retryData.error || "Final password reset failed.");

    showToast(retryData.message || "✅ Password reset complete.", "success");

    form.reset();
    setTimeout(() => {
      window.location.href = "/login";
    }, 2000);
  }

  function isStrongPassword(password) {
    const minLength = 8;
    const upperCase = /[A-Z]/;
    const lowerCase = /[a-z]/;
    const digit = /\d/;
    const specialChar = /[^A-Za-z0-9]/;

    return (
      password.length >= minLength &&
      upperCase.test(password) &&
      lowerCase.test(password) &&
      digit.test(password) &&
      specialChar.test(password)
    );
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
