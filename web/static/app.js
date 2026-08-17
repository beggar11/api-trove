// api-scout frontend: search + live verify, vanilla JS (no build step).
const $ = (id) => document.getElementById(id);

let lastHits = []; // most recent search results, used by the verify button

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

async function loadCategories() {
  const res = await fetch("/api/categories");
  const cats = await res.json();
  const sel = $("category");
  for (const c of cats) {
    const opt = document.createElement("option");
    opt.value = c.name;
    opt.textContent = `${c.name} (${c.count})`;
    sel.appendChild(opt);
  }
}

function statusBadge(status) {
  const cls = (status || "").toLowerCase();
  return `<span class="badge ${cls}">${escapeHtml(status || "—")}</span>`;
}

function render(entries, results) {
  const tbody = $("tbody");
  tbody.innerHTML = "";
  if (!entries.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="empty">No APIs match your filters.</td></tr>';
    return;
  }
  for (const e of entries) {
    const r = results ? results[e.url] : null;
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><a href="${escapeHtml(e.url)}" target="_blank" rel="noopener">${escapeHtml(e.name)}</a></td>
      <td>${escapeHtml(e.category)}</td>
      <td>${escapeHtml(e.auth)}</td>
      <td>${escapeHtml(e.https)}</td>
      <td>${escapeHtml(e.cors)}</td>
      <td>${r ? statusBadge(r.status) : "—"}</td>
      <td>${r ? r.ms : "—"}</td>
      <td>${r ? escapeHtml(r.note) : ""}</td>`;
    tbody.appendChild(tr);
  }
}

async function search() {
  const params = new URLSearchParams();
  const kw = $("keyword").value.trim();
  if (kw) params.set("keyword", kw);
  if ($("category").value) params.set("category", $("category").value);
  if ($("auth").value) params.set("auth", $("auth").value);
  if ($("cors").value) params.set("cors", $("cors").value);
  if ($("limit").value) params.set("limit", $("limit").value);

  const res = await fetch(`/api/apis?${params}`);
  const hits = await res.json();
  lastHits = hits;
  $("stats").textContent = `${hits.length} API(s) found`;
  render(hits, null);
}

async function verify() {
  if (!lastHits.length) {
    alert("Search first, then verify.");
    return;
  }
  const urls = lastHits.map((e) => e.url).slice(0, 100); // server caps at 100
  $("progress").classList.remove("hidden");
  try {
    const res = await fetch("/api/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ urls }),
    });
    const results = await res.json();
    render(lastHits, results);
    const ok = Object.values(results).filter((r) => r.status === "OK").length;
    $("stats").textContent =
      `${lastHits.length} API(s) · verified ${Object.keys(results).length}, OK=${ok}`;
  } finally {
    $("progress").classList.add("hidden");
  }
}

$("search").addEventListener("click", search);
$("verify").addEventListener("click", verify);
$("keyword").addEventListener("keydown", (e) => { if (e.key === "Enter") search(); });

loadCategories();
