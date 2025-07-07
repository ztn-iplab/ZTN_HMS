document.addEventListener("DOMContentLoaded", () => {
  let selectedUpgradePlan = "";

  // Load settings and trust policy on page load
  fetchTenantSettings();
  loadTrustPolicy();

  // Event listeners
  document.getElementById("uploadPolicyForm").addEventListener("submit", handlePolicyUpload);
  document.getElementById("upgradeForm").addEventListener("submit", handleUpgradeSubmit);
  document.getElementById("paymentForm").addEventListener("submit", handleMockPayment);
  document.getElementById("downgradeForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    await downgradePlan();
  });
});

// 🔑 Fetch current API key and plan
async function fetchTenantSettings() {
  try {
    const response = await fetch("/auth/tenant-settings");
    const data = await response.json();
    document.getElementById("tenant_api_key").value = data.api_key || "N/A";
    document.getElementById("tenant_plan").value = data.plan || "Unknown";
  } catch (err) {
    Toastify({ text: "Error loading tenant settings: " + err.message, backgroundColor: "#e53935" }).showToast();
  }
}

// 📋 Copy API key
function copyApiKey() {
  const keyInput = document.getElementById("tenant_api_key");
  keyInput.select();
  document.execCommand("copy");
  Toastify({ text: "API Key copied to clipboard!", backgroundColor: "#43a047" }).showToast();
}

// 📈 Show upgrade modal
function openUpgradeModal() {
  new bootstrap.Modal(document.getElementById("upgradePlanModal")).show();
}

// 📉 Show downgrade modal
function openDowngradeModal() {
  new bootstrap.Modal(document.getElementById("downgradePlanModal")).show();
}

// ⬇️ Perform downgrade to Free
async function downgradePlan() {
  try {
    const res = await fetch("/auth/change-plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan: "Basic" })
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.error);
    document.getElementById("tenant_plan").value = "Basic";
    bootstrap.Modal.getInstance(document.getElementById("downgradePlanModal")).hide();
    Toastify({ text: "Plan downgraded to Basic", backgroundColor: "#ff9800" }).showToast();
  } catch (err) {
    Toastify({ text: "Downgrade failed: " + err.message, backgroundColor: "#e53935" }).showToast();
  }
}

// 🧾 Simulated upgrade + payment flow
function handleUpgradeSubmit(e) {
  e.preventDefault();
  selectedUpgradePlan = document.getElementById("new_plan").value;

  const planCostMap = {
    "Premium": "$29/month",
    "Enterprise": "$99/month"
  };

  document.getElementById("selectedPlanName").innerText = selectedUpgradePlan;
  document.getElementById("planAmountText").innerText = planCostMap[selectedUpgradePlan] || "$0.00";

  bootstrap.Modal.getInstance(document.getElementById("upgradePlanModal")).hide();
  new bootstrap.Modal(document.getElementById("paymentModal")).show();
}

async function handleMockPayment(e) {
  e.preventDefault();
  const mockPayment = document.getElementById("mock_payment_input").value.trim();

  if (!mockPayment) {
    Toastify({ text: "Enter mock payment details.", backgroundColor: "#e53935" }).showToast();
    return;
  }

  const res = await fetch("/auth/change-plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plan: selectedUpgradePlan })
  });

  const result = await res.json();
  if (res.ok) {
    document.getElementById("tenant_plan").value = result.plan;
    bootstrap.Modal.getInstance(document.getElementById("paymentModal")).hide();
    Toastify({ text: `🎉 Upgrade successful to ${result.plan}`, backgroundColor: "#43a047" }).showToast();
  } else {
    Toastify({ text: result.error || "Upgrade failed", backgroundColor: "#e53935" }).showToast();
  }
}

// 📤 Upload trust policy JSON file
async function handlePolicyUpload(e) {
  e.preventDefault();
  const fileInput = document.getElementById("policyFile");
  if (!fileInput.files.length) {
    Toastify({ text: "No file selected", backgroundColor: "#e53935" }).showToast();
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  try {
    const res = await fetch("/auth/trust-policy/upload", {
      method: "POST",
      body: formData
    });

    const result = await res.json();
    if (!res.ok) throw new Error(result.error || "Upload failed");

    Toastify({ text: result.message, backgroundColor: "#43a047" }).showToast();
    loadTrustPolicy();
  } catch (err) {
    Toastify({ text: err.message, backgroundColor: "#e53935" }).showToast();
  }
}

// 📄 Load current policy and preview config
async function loadTrustPolicy() {
  try {
    const res = await fetch("/auth/trust-policy");
    const data = await res.json();

    if (!res.ok) throw new Error(data.error || "Failed to fetch policy");

    document.getElementById("policyFileName").innerText = data.filename || "N/A";

    const utcDate = new Date(data.uploaded_at);

    // ✅ Convert to JST explicitly using toLocaleString with timeZone
    const tokyoTime = utcDate.toLocaleString("en-US", {
      timeZone: "Asia/Tokyo",
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false
    });

    document.getElementById("policyUploadedAt").innerText = tokyoTime + " JST";

    document.getElementById("policyJsonPreview").textContent = JSON.stringify(data.config, null, 2);
    document.getElementById("currentPolicyInfo").classList.remove("d-none");
  } catch (err) {
    console.warn("No policy found or failed to load:", err.message);
  }
}async function clearPolicy() {
  if (!confirm("Are you sure you want to delete the uploaded trust policy? This cannot be undone.")) return;

  try {
    const res = await fetch("/auth/trust-policy/clear", { method: "DELETE" });
    const result = await res.json();

    if (!res.ok) throw new Error(result.error || "Failed to clear policy");

    Toastify({ text: result.message, backgroundColor: "#43a047" }).showToast();

    document.getElementById("policyFileName").innerText = "N/A";
    document.getElementById("policyUploadedAt").innerText = "";
    document.getElementById("policyJsonPreview").textContent = "";
    document.getElementById("currentPolicyInfo").classList.add("d-none");
  } catch (err) {
    Toastify({ text: err.message, backgroundColor: "#e53935" }).showToast();
  }
}

function togglePolicyEdit() {
  const preview = document.getElementById("policyJsonPreview");
  const editor = document.getElementById("policyJsonEditor");
  const editBtn = document.getElementById("editPolicyBtn");
  const saveBtn = document.getElementById("savePolicyBtn");
  const cancelBtn = document.getElementById("cancelPolicyBtn");

  editor.value = preview.textContent;
  editor.classList.remove("d-none");
  preview.classList.add("d-none");

  editBtn.classList.add("d-none");
  saveBtn.classList.remove("d-none");
  cancelBtn.classList.remove("d-none");
}

function cancelPolicyEdit() {
  const preview = document.getElementById("policyJsonPreview");
  const editor = document.getElementById("policyJsonEditor");
  const editBtn = document.getElementById("editPolicyBtn");
  const saveBtn = document.getElementById("savePolicyBtn");
  const cancelBtn = document.getElementById("cancelPolicyBtn");

  editor.classList.add("d-none");
  preview.classList.remove("d-none");

  editBtn.classList.remove("d-none");
  saveBtn.classList.add("d-none");
  cancelBtn.classList.add("d-none");
}

async function saveEditedPolicy() {
  const editor = document.getElementById("policyJsonEditor");
  const raw = editor.value;

  try {
    const parsed = JSON.parse(raw); // Validate JSON

    const response = await fetch("/auth//trust-policy/edit", {
      method: "PUT",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(parsed)
    });

    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Failed to save policy");

    document.getElementById("policyJsonPreview").textContent = JSON.stringify(parsed, null, 2);
    Toastify({ text: "✅ Policy saved successfully!", style: { background: "green" } }).showToast();
    cancelPolicyEdit();
  } catch (err) {
    Toastify({ text: `❌ Error: ${err.message}`, style: { background: "red" } }).showToast();
  }
}

