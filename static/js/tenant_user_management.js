// static/js/tenant_user_management.js

document.addEventListener("DOMContentLoaded", () => {
  loadTenantUsers();
  loadAvailableRoles();

  const form = document.getElementById("tenantUserForm");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    await submitTenantUserForm();
  });

  const roleSelect = document.getElementById("role_select");
  roleSelect.addEventListener("change", () => {
    const otherRoleInput = document.getElementById("custom_role_input");
    if (roleSelect.value === "other") {
      otherRoleInput.classList.remove("d-none");
    } else {
      otherRoleInput.classList.add("d-none");
    }
  });
});

async function loadTenantUsers() {
  try {
    const response = await fetch("/auth/tenant-users");
    const result = await response.json();

    if (!response.ok) throw new Error(result.error || "Failed to fetch users");

    const tableBody = document.getElementById("tenant-user-table-body");
    tableBody.innerHTML = "";
    result.users.forEach((user, index) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${index + 1}</td>
        <td>${user.mobile_number}</td>
        <td>${user.full_name || "-"}</td>
        <td>${user.email}</td>
        <td>${user.role}</td>
        <td>
          <button class="btn btn-sm btn-info" onclick="editTenantUser(${user.user_id})">Edit</button>
          <button class="btn btn-sm btn-danger" onclick="deleteTenantUser(${user.user_id})">Delete</button>
        </td>
      `;
      tableBody.appendChild(row);
    });
  } catch (err) {
    Toastify({ text: "Error loading users: " + err.message, backgroundColor: "#e53935" }).showToast();
  }
}

async function loadAvailableRoles() {
  try {
    const response = await fetch("/auth/tenant-roles");
    const result = await response.json();

    if (!response.ok) throw new Error(result.error || "Failed to load roles");

    const select = document.getElementById("role_select");
    select.innerHTML = result.roles
      .map(r => `<option value="${r.role_name}">${r.role_name}</option>`)
      .join("") + '<option value="other">Other</option>';
  } catch (err) {
    Toastify({ text: "Error loading roles: " + err.message, backgroundColor: "#e53935" }).showToast();
  }
}

function openUserModal() {
  document.getElementById("tenantUserForm").reset();
  document.getElementById("editingUserId").value = "";
  document.getElementById("custom_role_input").classList.add("d-none");
  new bootstrap.Modal(document.getElementById("userModal")).show();
}

async function editTenantUser(userId) {
  try {
    const response = await fetch(`/auth/tenant-users/${userId}`);
    const result = await response.json();

    if (!response.ok) throw new Error(result.error);

    document.getElementById("editingUserId").value = userId;
    document.getElementById("mobile_number").value = result.mobile_number;
    document.getElementById("full_name").value = result.first_name;
    document.getElementById("email").value = result.email;
    document.getElementById("role_select").value = result.role;
    document.getElementById("password").value = "";
    document.getElementById("custom_role_input").classList.add("d-none");

    new bootstrap.Modal(document.getElementById("userModal")).show();
  } catch (err) {
    Toastify({ text: "Failed to load user details: " + err.message, backgroundColor: "#e53935" }).showToast();
  }
}

async function deleteTenantUser(userId) {
  if (!confirm("Are you sure you want to delete this user?")) return;
  try {
    const res = await fetch(`/auth/tenant-users/${userId}`, { method: "DELETE" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    loadTenantUsers();
    Toastify({ text: "User deleted successfully.", backgroundColor: "#43a047" }).showToast();
  } catch (err) {
    Toastify({ text: "Failed to delete user: " + err.message, backgroundColor: "#e53935" }).showToast();
  }
}

async function submitTenantUserForm() {
  const userId = document.getElementById("editingUserId").value;
  let role = document.getElementById("role_select").value;
  if (role === "other") {
    role = document.getElementById("custom_role_name").value.trim();
  }

  const payload = {
    mobile_number: document.getElementById("mobile_number").value.trim(),
    full_name: document.getElementById("full_name").value.trim(),
    email: document.getElementById("email").value.trim(),
    role,
    password: document.getElementById("password").value
  };

  try {
    const method = userId ? "PUT" : "POST";
    const endpoint = userId ? `/auth/tenant-users/${userId}` : "/auth/tenant-users";

    const res = await fetch(endpoint, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (!res.ok) throw new Error(data.error);

    bootstrap.Modal.getInstance(document.getElementById("userModal")).hide();
    loadTenantUsers();
    Toastify({ text: data.message || "User saved successfully.", backgroundColor: "#43a047" }).showToast();
  } catch (err) {
    Toastify({ text: "Failed to save user: " + err.message, backgroundColor: "#e53935" }).showToast();
  }
}
