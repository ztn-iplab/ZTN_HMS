document.addEventListener("DOMContentLoaded", function () {
  const table = document.getElementById("patientsTable");
  if (!table) return;

  // Initialize basic search and pagination (vanilla JS fallback)
  const rows = Array.from(table.querySelectorAll("tbody tr"));
  const searchInput = document.getElementById("searchInput");

  if (searchInput) {
    searchInput.addEventListener("input", function () {
      const keyword = searchInput.value.toLowerCase();
      rows.forEach(row => {
        const match = row.innerText.toLowerCase().includes(keyword);
        row.style.display = match ? "" : "none";
      });
    });
  }
});
