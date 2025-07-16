
document.addEventListener("DOMContentLoaded", () => {
  console.log("📦 WebAuthn script loaded");

  const enrollBtn = document.getElementById("register-passkey-btn");
  const statusDiv = document.getElementById("biometric-status");

  if (!enrollBtn) {
    console.error("❌ Button with ID 'register-passkey-btn' not found.");
    return;
  }

  if (!statusDiv) {
    console.warn("⚠️ 'biometric-status' not found, injecting dynamically.");
    const div = document.createElement("div");
    div.id = "biometric-status";
    div.className = "text-center mt-3 fw-semibold";
    enrollBtn.parentElement.appendChild(div);
  }

  const status = document.getElementById("biometric-status");

  if (!window.PublicKeyCredential) {
    status.textContent = "❌ This browser does not support WebAuthn.";
    status.style.color = "red";
    return;
  }

  enrollBtn.addEventListener("click", async () => {

    try {
      enrollBtn.disabled = true;
      status.textContent = "⌛ Waiting for biometric or passkey...";
      status.style.color = "gray";

      // Step 1: Get options from your proxy endpoint
      const res = await fetch("/auth/begin-webauthn-registration", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
      });

      const json = await res.json();
      const options = json.public_key;

      if (!res.ok || !options) {
        throw new Error(json.error || "❌ Invalid registration options.");
      }
      // Decode binary fields
      options.challenge = base64urlToBuffer(options.challenge);
      options.user.id = base64urlToBuffer(options.user.id);
      if (options.excludeCredentials) {
        options.excludeCredentials = options.excludeCredentials.map((c) => ({
          ...c,
          id: base64urlToBuffer(c.id),
        }));
      }

      options.authenticatorSelection = {
        userVerification: "required",
      };

      // Step 2: Prompt user for passkey
      const credential = await navigator.credentials.create({
        publicKey: options,
      });

      const transports = credential.response.getTransports?.() || [];

      // Step 3: Prepare payload with `state` included
      const payload = {
        id: credential.id,
        rawId: bufferToBase64url(credential.rawId),
        type: credential.type,
        response: {
          attestationObject: bufferToBase64url(
            credential.response.attestationObject
          ),
          clientDataJSON: bufferToBase64url(credential.response.clientDataJSON),
        },
        transports,
        state: json.state, // ✅ Include state from /register-begin
      };

      // Step 4: Send to complete registration
      const completeRes = await fetch("/auth/complete-webauthn-registration", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        credentials: "include",
      });

      const result = await completeRes.json();

      if (!completeRes.ok) {
        throw new Error(result.error || "❌ Registration failed.");
      }
      // Feedback
      let methodUsed = "passkey";
      if (transports.includes("usb")) methodUsed = "USB key";
      else if (transports.includes("internal")) methodUsed = "fingerprint";
      else if (transports.includes("hybrid"))
        methodUsed = "cross-device passkey";

      status.textContent = `✅ ${methodUsed} registered successfully!`;
      status.style.color = "green";

      if (result.redirect) {
        setTimeout(() => {
          window.location.href = result.redirect;
        }, 1200);
      }
    } catch (err) {
      console.error("❌ WebAuthn registration failed:", err);
      status.textContent = "❌ " + err.message;
      status.style.color = "red";
      enrollBtn.disabled = false;
    }
  });

  // Helpers
  function base64urlToBuffer(base64url) {
    const base64 = base64url.replace(/-/g, "+").replace(/_/g, "/");
    const pad = base64.length % 4 ? 4 - (base64.length % 4) : 0;
    const padded = base64 + "=".repeat(pad);
    const binary = atob(padded);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
  }

  function bufferToBase64url(buffer) {
    const bytes = new Uint8Array(buffer);
    let str = "";
    for (let byte of bytes) str += String.fromCharCode(byte);
    return btoa(str).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }
});
