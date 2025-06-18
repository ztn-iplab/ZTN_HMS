document.getElementById("verify-biometric").onclick = async () => {
  const status = document.getElementById("webauthn-status");
  const error = document.getElementById("webauthn-error");
  status.textContent = "";
  error.textContent = "";

  try {
    // Step 1: Fetch challenge
    const res1 = await fetch("/auth/start-webauthn", { method: "POST" });
    const data1 = await res1.json();
    if (!res1.ok) throw new Error(data1.error || "Failed to start verification");

    const options = data1.public_key;
    options.challenge = Uint8Array.from(atob(options.challenge), c => c.charCodeAt(0));
    options.allowCredentials = options.allowCredentials.map(c => ({
      ...c,
      id: Uint8Array.from(atob(c.id), c => c.charCodeAt(0))
    }));

    // Step 2: Get assertion
    const assertion = await navigator.credentials.get({ publicKey: options });

    const result = {
      credentialId: btoa(String.fromCharCode(...new Uint8Array(assertion.rawId))),
      authenticatorData: btoa(String.fromCharCode(...new Uint8Array(assertion.response.authenticatorData))),
      clientDataJSON: btoa(String.fromCharCode(...new Uint8Array(assertion.response.clientDataJSON))),
      signature: btoa(String.fromCharCode(...new Uint8Array(assertion.response.signature))),
      userHandle: assertion.response.userHandle
        ? btoa(String.fromCharCode(...new Uint8Array(assertion.response.userHandle)))
        : null
    };

    // Step 3: Submit to backend
    const res2 = await fetch("/auth/verify-webauthn", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(result)
    });

    const data2 = await res2.json();
    if (!res2.ok) throw new Error(data2.error || "WebAuthn verification failed");

    // Success: redirect
    status.textContent = "✅ Biometric verified successfully! Redirecting...";
    window.location.href = data2.dashboard_url;

  } catch (err) {
    error.textContent = "❌ " + err.message;
  }
};
