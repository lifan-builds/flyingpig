const $ = (id) => document.getElementById(id);

function render(status) {
  const failed = status?.state === "failed";
  $("title").textContent = failed ? "Helper could not start" : "Starting local helper";
  $("message").textContent = status?.message || "Preparing the dashboard.";
  $("spinner").classList.toggle("hidden", failed);
  $("failure").classList.toggle("hidden", !failed);

  const diagnostics = status?.diagnostics || {};
  const build = diagnostics.build || diagnostics.expectedBuild || {};
  $("buildIdentity").textContent = build.identity
    || [build.version, build.revision || build.channel].filter(Boolean).join("+")
    || "development";
  $("startupPhase").textContent = diagnostics.phase || "initializing";
  $("helperPort").textContent = diagnostics.port ? String(diagnostics.port) : "-";
  $("portSelection").textContent = diagnostics.preferredPortOccupied
    ? `Preferred port occupied; selected ${diagnostics.port}`
    : "Preferred port selected";
  $("baseUrl").textContent = diagnostics.baseUrl || "-";
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
