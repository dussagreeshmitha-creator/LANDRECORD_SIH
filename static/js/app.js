const workflows = ["Upload Record", "Image Preprocessing", "OCR & Data Extraction", "Data Structuring", "AI-Based Validation", "GIS Boundary Verification", "Verified Digital Land Record"];
const detailLabels = { owner_name: "Owner Name", survey_number: "Survey Number", patta_number: "Patta Number", land_area: "Land Area", land_classification: "Land Classification", record_date: "Record Date", village: "Village", taluk: "Taluk", district: "District", north_boundary: "North Boundary", south_boundary: "South Boundary", east_boundary: "East Boundary", west_boundary: "West Boundary", latitude: "Latitude", longitude: "Longitude" };
let latestValidation = null;
const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => String(value ?? "—").replace(/[&<>"']/g, (character) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[character]));

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || "The request could not be completed.");
  return response.json();
}
function badge(status) { return `<span class="badge ${status === "VERIFIED" ? "verified" : "issue"}">${escapeHtml(status)}</span>`; }
function renderWorkflow() { $("#workflow").innerHTML = workflows.map((step, index) => `<div class="workflow-step"><span class="step-bullet">${String(index + 1).padStart(2, "0")}</span><span>${step}</span></div>`).join(""); }

async function loadDashboard() {
  const [stats, records] = await Promise.all([api("/api/stats"), api("/api/records")]);
  $("#stats-grid").innerHTML = [["Total Records", stats.total, "+12% this month"], ["Verified Records", stats.verified, "75% of total"], ["Records with Issues", stats.issues, "Requires review"], ["OCR Accuracy", `${stats.ocr_accuracy}%`, "Demo benchmark"]].map(([label, value, note]) => `<article class="stat-card"><span class="stat-label">${label}</span><strong>${value}</strong><small>${note}</small></article>`).join("");
  $("#recent-records").innerHTML = records.map((record) => `<div class="activity-item"><div><strong>${escapeHtml(record.id)} · ${escapeHtml(record.owner)}</strong><small>Survey ${escapeHtml(record.survey_number)} · ${escapeHtml(record.area)}</small></div>${badge(record.status)}</div>`).join("");
}
function renderDetails(details) { $("#ocr-details").innerHTML = Object.entries(details).map(([key, value]) => `<div class="detail-row"><label>${escapeHtml(detailLabels[key] || key)}</label><strong>${escapeHtml(value)}</strong></div>`).join(""); }
function renderValidation(validation) {
  const mismatch = validation.overall_status !== "VERIFIED";
  $("#result-status").className = `result-status ${mismatch ? "issue" : ""}`;
  $("#result-status").innerHTML = `<span class="status-icon">${mismatch ? "!" : "✓"}</span><div><strong>${escapeHtml(validation.headline)}</strong><span>${escapeHtml(validation.message)}</span></div>`;
  $("#validation-checks").innerHTML = validation.checks.map((check) => { const bad = check.status === "MISMATCH"; return `<div class="check-row ${bad ? "mismatched" : ""}"><div class="check-top"><strong>${escapeHtml(check.field)}</strong><span class="check-status ${bad ? "mismatched" : "matched"}">${bad ? "MISMATCHED" : "MATCHED"}</span></div><div class="check-values"><span>OCR Value<b>${escapeHtml(check.ocr)}</b></span><span>Registry Value<b>${escapeHtml(check.registry)}</b></span></div></div>`; }).join("");
}
function showValidation(data) { latestValidation = data; $("#validation-results").classList.remove("hidden"); $("#result-filename").textContent = `${data.filename} · simulated OCR complete`; renderDetails(data.ocr_details); renderValidation(data.validation); $("#validation-results").scrollIntoView({ behavior: "smooth", block: "start" }); }
function showDemoMismatch() {
  if (!latestValidation) return;
  const demo = structuredClone(latestValidation);
  demo.validation = { checks: [{ field: "Owner Name", ocr: "Ravi Kumar", registry: "Ravi Kumar", status: "MATCHED" }, { field: "Survey Number", ocr: "142/3A", registry: "142/3A", status: "MATCHED" }, { field: "Patta Number", ocr: "PT-2024-8765", registry: "PT-2024-8765", status: "MATCHED" }, { field: "Land Area", ocr: "3.20 Acres", registry: "2.50 Acres", status: "MISMATCH" }, { field: "Land Classification", ocr: "Agricultural", registry: "Agricultural", status: "MATCHED" }, { field: "Boundary", ocr: "Canal", registry: "Government Land", status: "MISMATCH" }], overall_status: "MANUAL VERIFICATION REQUIRED", headline: "MANUAL VERIFICATION REQUIRED", message: "Potential inconsistencies were detected in the land record." };
  renderValidation(demo.validation);
}
async function submitValidation() {
  const file = $("#file-input").files[0];
  if (!file) { $("#form-status").textContent = "Select any file to start the demo."; return; }
  $("#submit-btn").disabled = true; $("#loading-panel").classList.remove("hidden"); $("#validation-results").classList.add("hidden");
  const steps = ["Processing land record...", "Preprocessing document...", "Extracting text using OCR...", "Structuring land data...", "Running AI validation...", "Checking GIS boundaries..."];
  $("#processing-steps").innerHTML = steps.map((step) => `<div class="processing-step"><i></i><span>${step}</span></div>`).join("");
  const items = [...document.querySelectorAll(".processing-step")]; items.forEach((item, index) => setTimeout(() => { item.classList.add("active"); if (index) { items[index - 1].classList.remove("active"); items[index - 1].classList.add("done"); } }, index * 350));
  try { const form = new FormData(); form.append("file", file); const data = await api("/api/validate", { method: "POST", body: form }); setTimeout(() => showValidation(data), 2100); $("#form-status").textContent = "Validation complete."; } catch (error) { $("#form-status").textContent = error.message; } finally { setTimeout(() => { $("#submit-btn").disabled = false; $("#loading-panel").classList.add("hidden"); }, 2250); }
}
async function loadRecords() {
  const records = await api("/api/records");
  $("#records-table").innerHTML = records.map((record) => `<tr data-record-id="${escapeHtml(record.id)}"><td><strong>${escapeHtml(record.id)}</strong></td><td>${escapeHtml(record.owner)}</td><td>${escapeHtml(record.survey_number)}</td><td>${escapeHtml(record.area)}</td><td>${badge(record.status)}</td><td class="row-link">Inspect →</td></tr>`).join("");
  document.querySelectorAll("#records-table tr").forEach((row) => row.addEventListener("click", () => openRecord(row.dataset.recordId)));
}
async function openRecord(id) { const record = await api(`/api/records/${encodeURIComponent(id)}`); const detail = $("#record-detail"); detail.classList.remove("hidden"); detail.innerHTML = `<div class="panel-heading"><div><p class="kicker">${escapeHtml(record.id)}</p><h3>${escapeHtml(record.owner)} · Survey ${escapeHtml(record.survey_number)}</h3></div>${badge(record.status)}</div><p class="muted">Local registry detail with the same validation engine used by uploads.</p><div class="details-table">${Object.entries(record.ocr_details).map(([key, value]) => `<div class="detail-row"><label>${escapeHtml(detailLabels[key] || key)}</label><strong>${escapeHtml(value)}</strong></div>`).join("")}</div>`; detail.scrollIntoView({ behavior: "smooth", block: "nearest" }); }
function route() { const name = (location.hash.replace("#", "") || "dashboard").split("/")[0]; const valid = ["dashboard", "validation", "records", "gis", "about"].includes(name) ? name : "dashboard"; document.querySelectorAll(".view").forEach((view) => view.classList.toggle("hidden", view.id !== `view-${valid}`)); document.querySelectorAll("nav a").forEach((link) => link.classList.toggle("active", link.dataset.route === valid)); $("#page-title").textContent = { dashboard: "Command Dashboard", validation: "New Validation", records: "Processed Records", gis: "GIS Parcel Verification", about: "About System" }[valid]; if (valid === "dashboard") loadDashboard().catch(console.error); if (valid === "records") loadRecords().catch(console.error); }

$("#file-input").addEventListener("change", (event) => { $("#file-label").textContent = event.target.files[0]?.name || "No file selected"; });
$("#dropzone").addEventListener("dragover", (event) => { event.preventDefault(); $("#dropzone").classList.add("dragover"); });
$("#dropzone").addEventListener("dragleave", () => $("#dropzone").classList.remove("dragover"));
$("#dropzone").addEventListener("drop", (event) => { event.preventDefault(); $("#dropzone").classList.remove("dragover"); if (event.dataTransfer.files[0]) { $("#file-input").files = event.dataTransfer.files; $("#file-label").textContent = event.dataTransfer.files[0].name; } });
$("#submit-btn").addEventListener("click", submitValidation); $("#mismatch-btn").addEventListener("click", showDemoMismatch); window.addEventListener("hashchange", route); renderWorkflow(); route();
