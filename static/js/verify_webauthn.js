document.addEventListener("DOMContentLoaded", async () => {
  const statusDiv = document.getElementById("webauthn-status");

  // 🔧 Utility: Buffer → Base64URL
  function bufferToBase64url(buffer) {
    const bytes = new Uint8Array(buffer);
    let str = "";
    for (let b of bytes) str += String.fromCharCode(b);
    return btoa(str).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  // 🔧 Utility: Base64URL → Buffer
  function base64urlToBuffer(base64url) {
    if (!base64url || typeof base64url !== "string") {
      throw new Error("Invalid base64url input");
    }
    const base64 = base64url.replace(/-/g, "+").replace(/_/g, "/");
    const pad = base64.length % 4 ? 4 - (base64.length % 4) : 0;
    const padded = base64 + "=".repeat(pad);
    const binary = atob(padded);
    const buffer = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      buffer[i] = binary.charCodeAt(i);
    }
    return buffer.buffer;
  }


  try {
    statusDiv.textContent = "⌛ Starting biometric verification...";

    // 🟢 Step 1: Fetch assertion options
    const res = await fetch("/auth/begin-webauthn-verification", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include" // ensures session is used
    });

    const result = await res.json();
    if (!res.ok || !result.public_key || !result.public_key.challenge) {
      throw new Error(result.error || "Invalid WebAuthn response from server.");
    }

    const publicKey = result.public_key;

    // 🔁 Convert challenge & credential IDs
    publicKey.challenge = base64urlToBuffer(publicKey.challenge);
    publicKey.allowCredentials = (publicKey.allowCredentials || []).map(c => ({
      ...c,
      id: base64urlToBuffer(c.id)
    }));

    console.log("🟢 WebAuthn assertion options ready:", publicKey);

    // 👆 Step 2: Prompt for fingerprint or USB key
    const assertion = await navigator.credentials.get({ publicKey });

    console.log("✅ WebAuthn assertion successful:", assertion);

    // 🧾 Step 3: Build payload
    const payload = {
      credentialId: bufferToBase64url(assertion.rawId),
      authenticatorData: bufferToBase64url(assertion.response.authenticatorData),
      clientDataJSON: bufferToBase64url(assertion.response.clientDataJSON),
      signature: bufferToBase64url(assertion.response.signature),
      userHandle: assertion.response.userHandle
        ? bufferToBase64url(assertion.response.userHandle)
        : null
    };

    console.log("🛂 WebAuthn Assertion Payload:", payload);


    const finalRes = await fetch("/auth/complete-webauthn-verification", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      credentials: "include"
    });

    const finalResult = await finalRes.json();
    if (!finalRes.ok) {
      throw new Error(finalResult.error || "WebAuthn verification failed.");
    }

    // 🎉 Success
    statusDiv.textContent = "✅ Verified! Redirecting...";
    statusDiv.style.color = "green";
    window.location.href = finalResult.dashboard_url || "/";
  } catch (err) {
    let readableReason = "Unknown client-side WebAuthn error.";
    switch (err.name) {
      case "NotAllowedError":
        readableReason = "User cancelled or didn’t respond to WebAuthn prompt.";
        break;
      case "AbortError":
        readableReason = "WebAuthn operation was aborted.";
        break;
      case "SecurityError":
        readableReason = "WebAuthn blocked by browser or context.";
        break;
      case "InvalidStateError":
        readableReason = "Authenticator not ready or already used.";
        break;
      case "UnknownError":
        readableReason = "Unknown browser error.";
        break;
    }

    console.warn(`❌ ${readableReason} (${err.name || ""}: ${err.message || ""})`);
    statusDiv.textContent = "❌ " + readableReason;
    statusDiv.style.color = "red";
  }
});
