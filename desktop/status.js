const $ = (id) => document.getElementById(id);

function render(status) {
  const failed = status?.state === "failed";
  $("title").textContent = failed ? "Helper could not start" : "Starting local helper";
  $("message").textContent = status?.message || "Preparing the dashboard.";
  $("spinner").classList.toggle("hidden", failed);
  $("failure").classList.toggle("hidden", !failed);

  const diagnostics = status?.diagnostics || {};
  $("baseUrl").textContent = diagnostics.baseUrl || "-";
  $("logPath").textContent = diagnostics.logPath || "-";
  $("errorText").textContent = status?.error || diagnostics.lastError || "-";
}

$("retry").addEventListener("click", () => {
  window.flyingPigDesktop.retryHelper();
});

$("openLogs").addEventListener("click", () => {
  window.flyingPigDesktop.openLogs();
});

window.flyingPigDesktop.onStatus(render);
window.flyingPigDesktop.diagnostics().then(render);
