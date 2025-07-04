document.addEventListener("DOMContentLoaded", () => {
  loadTenantUsers();
  loadAvailableRoles();

  const form = document.getElementById("tenantUserForm");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    await submitTenantUserForm();
  });
});

async function loadTenantUsers() {
  try {
    const response = await fetch("/auth/tenant-users", {
      method: "GET",
      credentials: "include"  // ✅ Send JWT cookie
    });
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
    const response = await fetch("/auth/tenant-roles", {
      method: "GET",
      credentials: "include"  // ✅ Send JWT cookie
    });
    const result = await response.json();

    if (!response.ok) throw new Error(result.error || "Failed to load roles");

    const select = document.getElementById("role_select");
    select.innerHTML = result.roles
      .map(r => `<option value="${r.role_name}">${r.role_name}</option>`)
      .join("");
  } catch (err) {
    Toastify({ text: "Error loading roles: " + err.message, backgroundColor: "#e53935" }).showToast();
  }
}

function openRoleModal() {
  document.getElementById("addRoleForm").reset();
  new bootstrap.Modal(document.getElementById("addRoleModal")).show();
}

document.getElementById("addRoleForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  const roleName = document.getElementById("role_name").value.trim();

  try {
    const res = await fetch("/auth/tenant-roles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",  // ✅ Send JWT cookie
      body: JSON.stringify({ role_name: roleName })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Failed to create role");

    bootstrap.Modal.getInstance(document.getElementById("addRoleModal")).hide();
    Toastify({ text: data.message, backgroundColor: "#43a047" }).showToast();

    loadAvailableRoles();
  } catch (err) {
    Toastify({ text: err.message, backgroundColor: "#e53935" }).showToast();
  }
});

function openUserModal() {
  document.getElementById("tenantUserForm").reset();
  document.getElementById("editingUserId").value = "";
  new bootstrap.Modal(document.getElementById("userModal")).show();
}

async function editTenantUser(userId) {
  try {
    const response = await fetch(`/auth/tenant-users/${userId}`, {
      method: "GET",
      credentials: "include"  // ✅ Send JWT cookie
    });
    const result = await response.json();

    if (!response.ok) throw new Error(result.error);

    document.getElementById("editingUserId").value = userId;
    document.getElementById("mobile_number").value = result.mobile_number;
    const fullName = result.full_name || "";
    const firstName = fullName.trim().split(" ")[0] || "";
    document.getElementById("first_name").value = firstName;
    document.getElementById("email").value = result.email;
    document.getElementById("role_select").value = result.role;
    document.getElementById("preferred_mfa_select").value = result.preferred_mfa || "both";
    document.getElementById("password").value = "";

    new bootstrap.Modal(document.getElementById("userModal")).show();
  } catch (err) {
    Toastify({ text: "Failed to load user details: " + err.message, backgroundColor: "#e53935" }).showToast();
  }
}

async function deleteTenantUser(userId) {
  if (!confirm("Are you sure you want to delete this user?")) return;
  try {
    const res = await fetch(`/auth/tenant-users/${userId}`, {
      method: "DELETE",
      credentials: "include"  // ✅ Send JWT cookie
    });
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
  const role = document.getElementById("role_select").value;

  const payload = {
    mobile_number: document.getElementById("mobile_number").value.trim(),
    first_name: document.getElementById("first_name").value.trim(),
    email: document.getElementById("email").value.trim(),
    role,
    password: document.getElementById("password").value,
    preferred_mfa: document.getElementById("preferred_mfa_select").value
  };

  try {
    const method = userId ? "PUT" : "POST";
    const endpoint = userId ? `/auth/tenant-users/${userId}` : "/auth/tenant-users";

    const res = await fetch(endpoint, {
      method,
      headers: { "Content-Type": "application/json" },
      credentials: "include",  // ✅ Send JWT cookie
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
