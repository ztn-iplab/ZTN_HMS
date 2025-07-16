document.addEventListener("DOMContentLoaded", function () {
  const table = document.getElementById("appointmentsTable");
  const searchInput = document.getElementById("searchInput");

  if (!table || !searchInput) return;

  const rows = Array.from(table.querySelectorAll("tbody tr"));

  searchInput.addEventListener("input", function () {
    const keyword = searchInput.value.toLowerCase();

    rows.forEach(row => {
      const match = row.innerText.toLowerCase().includes(keyword);
      row.style.display = match ? "" : "none";
    });
  });
});
