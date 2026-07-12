import {
  attentionForRequest,
  checkpointCustomAnswer,
  checkpointOptionAnswer,
  fallbackPendingRequest,
  formatTime,
  isUserAttentionRequest,
  progressMessage,
  readableRunStatus,
  requestKey,
  siteLabel,
  statusForPendingRequest,
} from "./dashboard_protocol.js";

const $ = (id) => document.getElementById(id);

const state = {
  socket: null,
  connected: false,
  activeUrl: "",
  activeTabId: null,
  activeSite: "generic",
  selectedSite: "generic",
  sites: [],
  running: false,
  browserConnected: false,
  browserLaunching: false,
  browserStatusTimer: null,
  currentCheckpoint: null,
  helperUrl: "http://127.0.0.1:8765",
  notifySound: true,
  notifyOs: true,
  notifiedRequestKey: null,
  preflightFailures: [],
  timingSpans: [],
  runStatus: "ready_to_start",
  modelSettings: null,
  modelSavedLocally: false,
  lastResult: null,
  activationSignals: {},
  browserBackend: "browser_use",
  mcpConnected: false,
  mcpPages: [],
  selectedMcpPage: null,
  mcpReady: false,
  settingsOpen: false,
  workflowStage: "ready",
  activityOpen: false,
};

const betaScorecardsKey = "betaScorecards";
const activationSignalsKey = "activationSignals";
const outcomeLabels = {
  solved: "Solved",
  partial: "Partial",
  failed: "Failed",
};

const attentionTitles = {
  missing_information: "Information needed",
  otp_required: "OTP / MFA code needed",
  auth_required: "Authentication needed",
  manual_login_required: "Manual login needed",
  account_access_blocked: "Account access blocked",
  resume_after_auth: "Ready to resume?",
  attachment_required: "Attachment needed",
  irreversible_action_pending: "Approval needed",
  offer_received: "Offer received",
  recovery_pending: "Recovery decision",
};

function extensionApi() {
  return typeof chrome !== "undefined" ? chrome : null;
}

async function storageGet(keys) {
  const api = extensionApi();
  if (api?.storage?.local) {
    return api.storage.local.get(keys);
  }
  const out = {};
  for (const key of keys) {
    const raw = window.localStorage.getItem(`flyingpig.${key}`);
    if (raw !== null) {
      try {
        out[key] = JSON.parse(raw);
      } catch {
        out[key] = raw;
      }
    }
  }
  return out;
}

function storageSet(values) {
  const api = extensionApi();
  if (api?.storage?.local) {
    api.storage.local.set(values);
    return;
  }
  for (const [key, value] of Object.entries(values)) {
    window.localStorage.setItem(`flyingpig.${key}`, JSON.stringify(value));
  }
}

function dashboardUrl(path) {
  return new URL(path, window.location.href).toString();
}

function browserEndpoint() {
  return $("cdpUrl").value.trim() || "http://127.0.0.1:9222";
}

function browserEndpointPort() {
  try {
    return Number(new URL(browserEndpoint()).port || "9222");
  } catch {
    return 9222;
  }
}

function log(kind, text) {
  const first = $("log").firstElementChild;
  if (first?.dataset.kind === kind && first?.dataset.text === text) {
    const count = Number(first.dataset.count || "1") + 1;
    first.dataset.count = String(count);
    const title = first.querySelector("strong");
    if (title) title.textContent = `${kind} x${count}`;
    return;
  }

  const item = document.createElement("li");
  const title = document.createElement("strong");
  const body = document.createElement("span");
  item.dataset.kind = kind;
  item.dataset.text = text;
  item.dataset.count = "1";
  title.textContent = kind;
  body.textContent = text;
  item.append(title, body);
  $("log").prepend(item);
}

function playAttentionSound() {
  if (!state.notifySound) return;
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    const context = new AudioContext();
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime(880, context.currentTime);
    oscillator.frequency.setValueAtTime(660, context.currentTime + 0.12);
    gain.gain.setValueAtTime(0.001, context.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.08, context.currentTime + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.001, context.currentTime + 0.32);
    oscillator.connect(gain);
    gain.connect(context.destination);
    oscillator.start();
    oscillator.stop(context.currentTime + 0.34);
  } catch {
    log("notice", "Could not play attention sound.");
  }
}

function notifyAttention(title, message) {
  playAttentionSound();
  if (!state.notifyOs) return;
  const api = extensionApi();
  if (api?.notifications) {
    api.notifications.create({
      type: "basic",
      iconUrl: "assets/app-icon-64.png",
      title,
      message,
    });
    return;
  }
  if (!("Notification" in window)) return;
  if (Notification.permission === "granted") {
    new Notification(title, { body: message, icon: dashboardUrl("assets/app-icon-64.png") });
  } else if (Notification.permission !== "denied") {
    Notification.requestPermission().then((permission) => {
      if (permission === "granted") {
        new Notification(title, { body: message, icon: dashboardUrl("assets/app-icon-64.png") });
      }
    });
  }
}

function maybeNotifyRequest(request) {
  const key = requestKey(request);
  if (!key || key === state.notifiedRequestKey) return;
  state.notifiedRequestKey = key;
  const attention = attentionForRequest(request);
  if (attention) notifyAttention(attention.title, attention.message);
}

function setConnection(connected) {
  state.connected = connected;
  $("runtimeStatus").textContent = connected ? "Helper Online" : "Helper Offline";
  $("runtimeStatus").className = `pill ${connected ? "connected" : "disconnected"}`;
  $("helperSetupPanel").classList.toggle("hidden", connected);
  if (!connected) {
    setBrowserConnection(false, "Work Window Offline");
  }
  updateReadiness();
  updateButtons();
  updateModelSettingsView();
  updateExperienceMode();
}

function setBrowserConnection(connected, label) {
  state.browserConnected = connected;
  if (!connected && state.browserBackend !== "mcp") state.mcpReady = false;
  $("browserStatus").textContent = label || (connected ? "Work Window Connected" : "Work Window Offline");
  $("browserStatus").className = `pill ${connected ? "connected" : "disconnected"}`;
  $("currentUrlLabel").textContent = connected ? "Work Window URL" : "Launch URL";
  updateReadiness();
  updateButtons();
}

function setRunState(message) {
  state.running = Boolean(message.running);
  if (message.site) {
    state.activeSite = message.site;
    $("siteStatus").textContent = siteLabel(message.site, state.sites);
  }
  const pendingRequest = message.pending_request || fallbackPendingRequest(message);
  const status = message.status || (state.running ? "running" : "ready");
  state.runStatus = status;
  $("agentStatus").textContent = formatAgentStatus(status);
  $("stepStatus").textContent = message.step ? String(message.step) : "-";
  $("runMessage").textContent = pendingRequest
    ? pendingRunMessage(pendingRequest)
    : message.message || "Ready";
  $("startedAt").textContent = formatTime(message.started_at);
  $("updatedAt").textContent = formatTime(message.updated_at);
  if (message.permission_mode) {
    $("permissionMode").textContent = permissionModeLabel(message.permission_mode);
  }
  if (Array.isArray(message.preflight_failures) && message.preflight_failures.length) {
    state.preflightFailures = message.preflight_failures;
    renderPreflightFailures(message.preflight_failures);
  } else if (Array.isArray(message.preflight_failures)) {
    state.preflightFailures = [];
  }
  if (Array.isArray(message.timing_spans)) {
    renderTimingSpans(message.timing_spans);
  }
  if (message.result) {
    renderResult(message.result);
  }

  if (pendingRequest) {
    renderPendingRequest(pendingRequest);
    maybeNotifyRequest(pendingRequest);
  } else if (!message.needs_input) {
    $("questionPanel").classList.add("hidden");
    $("checkpointPanel").classList.add("hidden");
    state.currentCheckpoint = null;
    state.notifiedRequestKey = null;
  }
  updateReadiness();
  updateButtons();
  updateWorkflowView();
}

function updateButtons() {
  const hasTask = Boolean($("taskText").value.trim());
  const canLaunchBrowser = state.connected && !state.running && !state.browserLaunching;
  const startReason = startDisabledReason({ hasTask });
  $("startTask").disabled = Boolean(startReason);
  $("hucaTask").disabled = !state.connected || !state.browserConnected || !hasTask;
  $("cancelTask").disabled = !state.connected || !state.running;
  $("hucaTask").classList.toggle("hidden", !state.running && !state.lastResult);
  $("cancelTask").classList.toggle("hidden", !state.running);
  $("launchChrome").disabled = !canLaunchBrowser;
  $("attachChrome").disabled = !canLaunchBrowser;
  $("autoConnectChrome").disabled = !canLaunchBrowser;
  $("refreshTab").disabled = !state.connected || !state.browserConnected;
  $("statusLaunchChrome").classList.toggle("hidden", !state.connected || state.browserConnected);
  $("statusLaunchChrome").disabled = !canLaunchBrowser;
  $("startDisabledReason").textContent = startReason;
  $("startDisabledReason").classList.toggle("hidden", !startReason);
  updateReadiness();
  updateWorkflowView();
}

function updateExperienceMode() {
  const configured = modelReady();
  const showSetup = !configured || state.settingsOpen;
  $("firstRunPanel").classList.toggle("hidden", !showSetup);
  $("readinessStrip").classList.toggle("compact", configured);
  $("modelSettingsToggle").setAttribute("aria-expanded", String(state.settingsOpen));
  $("modelSettingsToggle").textContent = state.settingsOpen ? "Done" : "Settings";
  const configurationBecameInvalid = Boolean(state.activationSignals.model_configured) && !configured;
  $("modelSetupHeading").textContent = configurationBecameInvalid
    ? "Configuration needs attention"
    : "Choose the model Flying Pig will use";
  document.body.classList.toggle("configured", configured);
  updateGuideView();
}

function updateGuideView() {
  const firstRunComplete = Boolean(state.activationSignals.first_run_started);
  const showGuide = modelReady()
    && !firstRunComplete
    && !state.settingsOpen
    && state.workflowStage === "ready";
  $("firstUseGuide").classList.toggle("hidden", !showGuide);
  document.body.classList.toggle("has-first-use-guide", showGuide);
  $("guideConfigureStatus").textContent = modelReady() ? "Model ready" : "Needs attention";
  const websiteReady = state.browserConnected && Boolean(state.activeUrl);
  $("guideWebsiteStatus").textContent = websiteReady ? "Website ready" : "Use the work window";
  $("guideOpenWebsite").textContent = websiteReady ? "Review" : "Open";
  for (const item of $("firstUseGuide").querySelectorAll("[data-guide-step]")) {
    const step = item.dataset.guideStep;
    const ready = step === "configure" ? modelReady() : step === "website" ? websiteReady : false;
    item.dataset.ready = ready ? "true" : "false";
  }
}

function updateWorkflowView() {
  const attentionVisible = !$('questionPanel').classList.contains('hidden')
    || !$('checkpointPanel').classList.contains('hidden');
  let stage = state.workflowStage;
  if (state.lastResult && !state.running) stage = "result";
  if (state.running) stage = attentionVisible ? "attention" : "running";
  if (!state.running && !state.lastResult && stage !== "preparing") stage = "ready";
  state.workflowStage = stage;
  document.body.dataset.workflow = stage;
  document.body.classList.toggle("activity-open", state.activityOpen);
  $("preparationPanel").classList.toggle("hidden", stage !== "preparing");
  $("runningFocus").classList.toggle("hidden", stage !== "running");
  $("activityToggle").setAttribute("aria-expanded", String(state.activityOpen));
  $("activityToggle").textContent = state.activityOpen ? "Hide activity" : "View activity";
  $("focusedRunTitle").textContent = state.activeSite && state.activeSite !== "generic"
    ? `Talking to ${siteLabel(state.activeSite, state.sites)}`
    : "Talking to customer service";
  $("focusedRunMessage").textContent = $("runMessage").textContent
    || "Flying Pig is working. You only need to return when a decision is required.";
  updateGuideView();
}

function startDisabledReason({ hasTask } = { hasTask: Boolean($("taskText").value.trim()) }) {
  if (!state.connected) return "Reconnect the Flying Pig helper before starting.";
  if (!modelReady()) return "Configure the selected model before starting.";
  if (state.browserLaunching) return "Wait for the work window to finish opening.";
  if (!hasTask) return "Add a problem brief before starting.";
  if (state.running) return "A run is already active.";
  return "";
}

function readinessItem(id, ready, text) {
  const element = $(id);
  if (!element) return;
  element.textContent = text;
  element.closest(".readiness-item")?.setAttribute("data-ready", ready);
}

function updateReadiness() {
  const taskReady = Boolean($("taskText")?.value.trim());
  const hasUrl = Boolean(state.activeUrl);
  const pendingAuth = state.running && ["waiting_on_login", "waiting_on_auth"].includes(
    state.runStatus,
  );
  readinessItem("readyHelper", state.connected ? "true" : "false", state.connected ? "Online" : "Offline");
  readinessItem("readyModel", modelReady() ? "true" : "false", modelReadinessText());
  readinessItem(
    "readyWorkWindow",
    state.browserConnected ? "true" : "false",
    state.browserConnected ? "Connected" : "Open it",
  );
  readinessItem(
    "readyChatSurface",
    state.browserConnected && hasUrl ? "true" : "false",
    state.browserConnected && hasUrl ? "Selected" : "Prepare tab",
  );
  readinessItem("readyTaskBrief", taskReady ? "true" : "false", taskReady ? "Ready" : "Needed");
  readinessItem("readyAuth", pendingAuth ? "warn" : "true", pendingAuth ? "Action needed" : "Browser only");
  readinessItem(
    "readySafetyGate",
    state.preflightFailures.length ? "false" : "true",
    state.preflightFailures.length ? `${state.preflightFailures.length} blocked` : "Ready",
  );
  updateQuickstart();
}

function updateSetupDiagnostic() {
  $("setupDiagnostic").textContent = `${state.helperUrl} unavailable`;
}

function providerForModel(model) {
  if (model === "claude-opus") return "claude";
  if (model === "gemini-pro") return "gemini-flash";
  if (model === "gpt-5.5" || model === "cliproxy") return "cliproxyapi";
  return model || "cliproxyapi";
}

function selectedProviderSettings() {
  const providerId = providerForModel($("model").value);
  const providers = state.modelSettings?.providers || [];
  return providers.find((provider) => provider.id === providerId) || {
    id: providerId,
    label: modelLabel($("model").value),
    configured: false,
    help: "Save an API key for this provider before live model runs.",
  };
}

function modelReady() {
  if (!state.connected || !state.modelSettings) return false;
  return Boolean(selectedProviderSettings().configured);
}

function modelReadinessText() {
  if (!state.connected) return "Check key";
  if (!state.modelSettings) return "Checking";
  return modelReady() ? "Configured" : "Add key";
}

function modelLabel(model) {
  const option = $("model")?.querySelector(`option[value="${CSS.escape(model || "")}"]`);
  return option?.textContent || model || "Model";
}

function updateModelSettingsView() {
  const provider = selectedProviderSettings();
  $("modelKeyTitle").textContent = `${provider.label} API key`;
  if (!state.connected) {
    $("modelKeyStatus").textContent = "Connect the helper to check credential status.";
  } else if (!state.modelSettings) {
    $("modelKeyStatus").textContent = "Credential status unavailable.";
  } else {
    $("modelKeyStatus").textContent = provider.configured
      ? `${provider.label} key is configured.`
      : `${provider.label} key is not configured.`;
  }
  $("modelKeyHelp").textContent = provider.help
    || "Keys are stored only in your local Flying Pig env file.";
  if (provider.configured) {
    recordActivationSignal("model_configured");
  }
  updateReadiness();
  updateExperienceMode();
}

async function loadModelSettings() {
  if (!state.connected) {
    state.modelSettings = null;
    updateModelSettingsView();
    return;
  }
  try {
    const response = await fetch(`${state.helperUrl}/model/settings`);
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || "Model settings unavailable.");
    state.modelSettings = payload;
    if (!state.modelSavedLocally && payload.default_model) {
      const option = $("model").querySelector(`option[value="${CSS.escape(payload.default_model)}"]`);
      if (option) $("model").value = payload.default_model;
    }
    updateModelSettingsView();
  } catch {
    state.modelSettings = null;
    updateModelSettingsView();
  }
}

async function saveModelSettings({ clearKey = false } = {}) {
  if (!state.connected) {
    $("modelKeyStatus").textContent = "Reconnect the helper before saving model settings.";
    return;
  }
  const model = $("model").value || "cliproxyapi";
  const provider = providerForModel(model);
  const apiKey = $("modelApiKey").value.trim();
  storageSet({ model });
  state.modelSavedLocally = true;
  try {
    const response = await fetch(`${state.helperUrl}/model/settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        default_model: model,
        provider,
        api_key: clearKey ? "" : apiKey,
        clear_key: clearKey,
      }),
    });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || "Could not save model settings.");
    $("modelApiKey").value = "";
    state.modelSettings = payload;
    updateModelSettingsView();
    if (!clearKey && selectedProviderSettings().configured) {
      recordActivationSignal("model_configured");
      state.settingsOpen = false;
    }
    updateExperienceMode();
    log("settings", clearKey ? "Cleared saved model key." : "Saved model settings.");
  } catch (error) {
    $("modelKeyStatus").textContent = error.message || "Could not save model settings.";
    log("error", error.message || "Could not save model settings.");
  }
}

function siteForAction() {
  if (state.selectedSite) return state.selectedSite;
  if (state.activeSite && state.activeSite !== "unknown") {
    return state.activeSite;
  }
  return "generic";
}

function formatAgentStatus(status) {
  return readableRunStatus(status);
}

function permissionModeLabel(mode) {
  if (mode === "supervised_browser") return "Supervised browser only";
  return mode || "Supervised browser only";
}

function pendingRunMessage(request) {
  if (request?.type === "decision_checkpoint" || request?.original_type === "decision_checkpoint") {
    return "Choose how Flying Pig should proceed below.";
  }
  if (request?.type === "manual_login_required") {
    return "Complete login in the visible work window. Flying Pig will resume after you confirm.";
  }
  if (request?.type === "otp_required" || request?.type === "auth_required") {
    return "Complete verification in the visible work window or provide only the requested code.";
  }
  if (request?.type === "account_access_blocked") {
    return "Account access is blocked. Review the visible browser state before continuing.";
  }
  return "Answer the prompt below so Flying Pig can continue.";
}

function setTaskUrl(url, { workWindow = false } = {}) {
  const previousUrl = state.activeUrl;
  state.activeUrl = url || "";
  state.activeTabId = workWindow ? null : state.activeTabId;
  $("currentUrl").value = state.activeUrl;
  storageSet({ activeUrl: state.activeUrl });
  if (state.connected && state.activeUrl && state.activeUrl !== previousUrl) {
    state.socket?.send(JSON.stringify({ type: "resolve", url: state.activeUrl }));
  }
  if (state.activeUrl) {
    recordActivationSignal("chat_surface_selected");
  }
  updateReadiness();
  updateButtons();
}

function quickstartReady(step) {
  const hasTask = Boolean($("taskText")?.value.trim());
  if (step === "model") return modelReady();
  if (step === "work_window") return state.browserConnected;
  if (step === "chat_surface") return Boolean(state.activeUrl);
  if (step === "task_brief") return hasTask;
  if (step === "start") return state.running || Boolean(state.activationSignals.first_run_started);
  return false;
}

function updateQuickstart() {
  const list = $("quickstartList");
  if (!list) return;
  for (const item of list.querySelectorAll("[data-step]")) {
    item.dataset.ready = quickstartReady(item.dataset.step) ? "true" : "false";
  }
  updateGuideView();
}

async function loadActivationSignals() {
  const saved = await storageGet([activationSignalsKey]);
  state.activationSignals = saved[activationSignalsKey] && typeof saved[activationSignalsKey] === "object"
    ? saved[activationSignalsKey]
    : {};
  updateQuickstart();
}

function recordActivationSignal(name) {
  if (!name || state.activationSignals[name]) {
    updateQuickstart();
    return;
  }
  state.activationSignals = {
    ...state.activationSignals,
    [name]: new Date().toISOString(),
  };
  storageSet({ [activationSignalsKey]: state.activationSignals });
  updateQuickstart();
}

async function openWebsiteGuide() {
  state.workflowStage = "preparing";
  $("preparationMessage").textContent = state.browserConnected
    ? "Navigate to the customer-service chat in the work window, then return here."
    : "Opening a work window. Log in and navigate to the customer-service chat.";
  updateWorkflowView();
  if (!state.browserConnected) {
    const opened = await launchChrome();
    $("preparationMessage").textContent = opened
      ? "Log in and navigate to the customer-service chat, then return here."
      : "The work window could not be opened. Try again or check Settings.";
    updateWorkflowView();
  }
}

function applyBrowserPayload(payload) {
  if (!payload?.connected || !payload.current_url) return;
  setTaskUrl(payload.current_url, { workWindow: true });
}

function formatDuration(ms) {
  const value = Number(ms || 0);
  if (value >= 1000) return `${(value / 1000).toFixed(1)}s`;
  return `${Math.round(value)}ms`;
}

function renderTimingSpans(spans) {
  state.timingSpans = Array.isArray(spans) ? spans.slice(-16) : [];
  const total = state.timingSpans.reduce((sum, span) => sum + Number(span.duration_ms || 0), 0);
  $("timingTotal").textContent = formatDuration(total);
  const list = $("timingList");
  list.replaceChildren();
  for (const span of state.timingSpans.slice().reverse()) {
    const item = document.createElement("li");
    const title = document.createElement("strong");
    const body = document.createElement("span");
    title.textContent = `${span.label || span.name || "Timing"} · ${formatDuration(span.duration_ms)}`;
    body.textContent = span.status && span.status !== "ok" ? span.status : span.name || "";
    item.append(title, body);
    list.append(item);
  }
}

function addTimingSpan(span) {
  if (!span) return;
  const key = `${span.name}:${span.timestamp}:${span.duration_ms}`;
  const existing = new Set(state.timingSpans.map((item) => `${item.name}:${item.timestamp}:${item.duration_ms}`));
  const spans = existing.has(key) ? state.timingSpans : [...state.timingSpans, span];
  renderTimingSpans(spans);
  log("timing", `${span.label || span.name}: ${formatDuration(span.duration_ms)}`);
}

function renderSites(items) {
  state.sites = Array.isArray(items) ? items : [];
  const picker = $("sitePicker");
  const previous = state.selectedSite || picker.value || "generic";
  const siteOptions = state.sites.length
    ? state.sites
    : [{ id: "generic", label: "Generic chat" }];
  const options = siteOptions.map((item) => ({
      id: item.id,
      label: item.label || siteLabel(item.id),
    }));
  picker.replaceChildren();
  for (const option of options) {
    const element = document.createElement("option");
    element.value = option.id;
    element.textContent = option.label;
    picker.append(element);
  }
  state.selectedSite = options.some((option) => option.id === previous) ? previous : "generic";
  picker.value = state.selectedSite;
  $("siteStatus").textContent = siteLabel(state.activeSite, state.sites);
  updateButtons();
}

async function refreshTab() {
  const overrideUrl = new URLSearchParams(window.location.search).get("targetUrl");
  if (overrideUrl && !state.browserConnected) {
    state.activeUrl = overrideUrl;
    state.activeTabId = null;
  } else {
    const browserReady = await refreshBrowserStatus();
    if (browserReady) return;
  }
  $("currentUrl").value = state.activeUrl;
  storageSet({ activeUrl: state.activeUrl });
  if (state.connected) {
    state.socket?.send(JSON.stringify({ type: "resolve", url: state.activeUrl }));
  }
}

async function workWindowPlacement() {
  const fallback = {
    window_width: 1120,
    window_height: 900,
    window_left: 560,
    window_top: 80,
  };
  const api = extensionApi();
  if (!api?.windows?.getCurrent || !api?.windows?.update) return fallback;

  const availableWidth = window.screen?.availWidth || 0;
  const availableHeight = window.screen?.availHeight || 0;
  if (availableWidth < 1500 || availableHeight < 720) return fallback;

  const cockpitWidth = Math.min(580, Math.max(500, Math.floor(availableWidth * 0.34)));
  const gap = 8;
  const workWidth = Math.max(900, availableWidth - cockpitWidth - gap);
  const workHeight = Math.max(720, availableHeight);
  try {
    const current = await api.windows.getCurrent();
    await api.windows.update(current.id, {
      left: 0,
      top: 0,
      width: cockpitWidth,
      height: workHeight,
      focused: true,
    });
    return {
      window_width: workWidth,
      window_height: workHeight,
      window_left: cockpitWidth + gap,
      window_top: 0,
    };
  } catch {
    return fallback;
  }
}

async function launchChrome() {
  if (!state.connected || state.running || state.browserLaunching) return false;
  state.browserBackend = "browser_use";
  state.mcpReady = false;
  state.browserLaunching = true;
  updateButtons();
  $("agentStatus").textContent = "launching";
  $("runMessage").textContent = "Launching Flying Pig work window.";
  log("browser", "Launch requested.");

  try {
    const site = siteForAction();
    const initialUrl = site === "generic" && state.activeUrl ? state.activeUrl : undefined;
    const placement = await workWindowPlacement();
    const chromeProfile = $("chromeProfile").value || "dedicated";
    storageSet({ chromeProfile });
    const response = await fetch(`${state.helperUrl}/browser/launch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        site,
        cdp_port: browserEndpointPort(),
        chrome_profile: chromeProfile,
        initial_url: initialUrl,
        ...placement,
      }),
    });
    const payload = await response.json();
    if (!payload.ok) {
      throw new Error(payload.error || "Browser launch failed.");
    }
    $("cdpUrl").value = payload.cdp_url || "http://127.0.0.1:9222";
    storageSet({ cdpUrl: $("cdpUrl").value });
    setBrowserConnection(true, "Work Window Connected");
    applyBrowserPayload({ ...payload, connected: true });
    addTimingSpan(payload.timing_span);
    recordActivationSignal("work_window_opened");
    $("agentStatus").textContent = "ready";
    $("runMessage").textContent = payload.message || "Work window is ready.";
    log("browser", payload.message || "Work window is ready.");
    return true;
  } catch (error) {
    $("agentStatus").textContent = "error";
    $("runMessage").textContent = error.message || "Browser launch failed.";
    log("error", error.message || "Browser launch failed.");
    return false;
  } finally {
    state.browserLaunching = false;
    updateButtons();
  }
}

async function attachChrome() {
  if (!state.connected || state.running || state.browserLaunching) return;
  state.browserBackend = "browser_use";
  state.mcpReady = false;
  state.browserLaunching = true;
  updateButtons();
  $("agentStatus").textContent = "connecting";
  $("runMessage").textContent = "Connecting to existing Chrome.";
  log("browser", "Existing Chrome connection requested.");

  try {
    const cdpUrl = browserEndpoint();
    const response = await fetch(`${state.helperUrl}/browser/attach`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cdp_url: cdpUrl }),
    });
    const payload = await response.json();
    if (!payload.ok) {
      throw new Error(payload.error || "Existing Chrome connection failed.");
    }
    $("cdpUrl").value = payload.cdp_url || cdpUrl;
    storageSet({ cdpUrl: $("cdpUrl").value });
    setBrowserConnection(true, "Work Window Connected");
    applyBrowserPayload({ ...payload, connected: true });
    recordActivationSignal("work_window_opened");
    $("agentStatus").textContent = "ready";
    $("runMessage").textContent = payload.message || "Existing Chrome is connected.";
    log("browser", payload.message || "Existing Chrome is connected.");
  } catch (error) {
    $("agentStatus").textContent = "error";
    $("runMessage").textContent = error.message || "Existing Chrome connection failed.";
    log("error", error.message || "Existing Chrome connection failed.");
  } finally {
    state.browserLaunching = false;
    updateButtons();
  }
}

function renderMcpPages(pages) {
  state.mcpPages = Array.isArray(pages) ? pages : [];
  const panel = $("mcpTabPanel");
  const list = $("mcpPages");
  panel.classList.remove("hidden");
  list.replaceChildren();

  if (!state.mcpPages.length) {
    const empty = document.createElement("p");
    empty.className = "field-note";
    empty.textContent = "No existing Chrome tabs were returned. Open chrome://inspect/#remote-debugging and allow remote debugging, then try again.";
    list.append(empty);
    return;
  }

  for (const page of state.mcpPages) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "mcp-page secondary";
    if (state.selectedMcpPage?.index === page.index) button.classList.add("selected");

    const title = document.createElement("strong");
    title.textContent = page.title || "Untitled tab";
    const url = document.createElement("span");
    url.textContent = page.url || "No URL reported";
    const mode = document.createElement("small");
    mode.textContent = page.cdp_url ? "CDP handoff available" : "Runs through Chrome MCP";
    button.append(title, url, mode);
    button.addEventListener("click", () => selectMcpPage(page));
    list.append(button);
  }
}

async function autoConnectChrome() {
  if (!state.connected || state.running || state.browserLaunching) return;
  state.browserLaunching = true;
  state.mcpReady = false;
  updateButtons();
  $("agentStatus").textContent = "connecting";
  $("runMessage").textContent = "Auto-connecting to existing Chrome.";
  $("mcpStatus").textContent = "Connecting to Chrome MCP";
  $("mcpMessage").textContent = "Opening the Chrome DevTools MCP auto-connect bridge.";
  $("mcpTabPanel").classList.remove("hidden");
  log("browser", "Chrome DevTools MCP auto-connect requested.");

  try {
    const response = await fetch(`${state.helperUrl}/browser/mcp/connect`, { method: "POST" });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.message || payload.error || "Chrome MCP auto-connect failed.");
    state.mcpConnected = true;
    $("mcpStatus").textContent = "Chrome MCP Connected";
    $("mcpMessage").textContent = payload.message || "Select the existing Chrome tab Flying Pig may supervise.";
    $("agentStatus").textContent = "ready";
    $("runMessage").textContent = "Select the existing Chrome tab to supervise.";
    renderMcpPages(payload.pages || []);
    log("browser", payload.message || "Chrome MCP connected.");
  } catch (error) {
    state.mcpConnected = false;
    $("mcpStatus").textContent = "Allow remote debugging in Chrome";
    $("mcpMessage").textContent = error.message || "Chrome MCP auto-connect failed.";
    $("agentStatus").textContent = "error";
    $("runMessage").textContent = error.message || "Chrome MCP auto-connect failed.";
    log("error", error.message || "Chrome MCP auto-connect failed.");
  } finally {
    state.browserLaunching = false;
    updateButtons();
  }
}

async function selectMcpPage(page) {
  if (!state.connected || state.running || state.browserLaunching) return;
  state.browserLaunching = true;
  state.selectedMcpPage = page;
  updateButtons();
  renderMcpPages(state.mcpPages);
  $("agentStatus").textContent = "checking";
  $("runMessage").textContent = "Verifying the selected Chrome tab.";

  try {
    const response = await fetch(`${state.helperUrl}/browser/mcp/select`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ page_index: page.index, page_id: page.id, url: page.url }),
    });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.message || payload.error || "Could not select Chrome tab.");
    state.selectedMcpPage = payload.page || page;
    state.browserBackend = payload.browser_backend || "mcp";
    state.mcpReady = Boolean(payload.browser_ready);
    $("mcpStatus").textContent = state.mcpReady ? "Chrome MCP Selected" : "Chrome MCP unavailable";
    $("mcpMessage").textContent = payload.message || "Chrome tab selected.";
    if (payload.current_url) {
      setTaskUrl(payload.current_url, { workWindow: true });
    }
    if (payload.cdp_url) {
      $("cdpUrl").value = payload.cdp_url;
      storageSet({ cdpUrl: payload.cdp_url });
    }
    setBrowserConnection(Boolean(payload.browser_ready), "Work Window Connected");
    recordActivationSignal("work_window_opened");
    $("agentStatus").textContent = "ready";
    $("runMessage").textContent = payload.message || "Chrome tab selected.";
    renderMcpPages(state.mcpPages);
    log("browser", payload.message || "Chrome tab selected.");
  } catch (error) {
    state.mcpReady = false;
    $("agentStatus").textContent = "error";
    $("runMessage").textContent = error.message || "Could not select Chrome tab.";
    log("error", error.message || "Could not select Chrome tab.");
  } finally {
    state.browserLaunching = false;
    updateButtons();
  }
}

async function openSetup() {
  const api = extensionApi();
  const url = api?.runtime?.getURL
    ? api.runtime.getURL("src/setup.html")
    : dashboardUrl("setup.html");
  if (api?.tabs?.create) {
    await api.tabs.create({ url });
    return;
  }
  window.open(url, "_blank", "noopener");
}

async function refreshBrowserStatus() {
  if (!state.connected) {
    setBrowserConnection(false, "Work Window Offline");
    return false;
  }
  if (state.browserBackend === "mcp") {
    setBrowserConnection(state.mcpReady, state.mcpReady ? "Work Window Connected" : "Work Window Offline");
    return state.mcpReady;
  }
  try {
    const cdpUrl = browserEndpoint();
    const response = await fetch(
      `${state.helperUrl}/browser/status?cdp_url=${encodeURIComponent(cdpUrl)}`,
    );
    const payload = await response.json();
    setBrowserConnection(
      Boolean(payload.connected),
      payload.connected ? "Work Window Connected" : "Work Window Offline",
    );
    if (payload.cdp_url) {
      $("cdpUrl").value = payload.cdp_url;
      storageSet({ cdpUrl: payload.cdp_url });
    }
    applyBrowserPayload(payload);
    return Boolean(payload.connected);
  } catch {
    setBrowserConnection(false, "Work Window Offline");
    return false;
  }
}

async function loadSettings() {
  const saved = await storageGet([
    "cdpUrl",
    "briefStarter",
    "taskText",
    "successCriteria",
    "template",
    "templateManual",
    "model",
    "helperUrl",
    "chromeProfile",
    "notifySound",
    "notifyOs",
    "selectedSite",
    "authorizationTarget",
    "authorizeClosure",
    "authorizeRefund",
    "refundChecking",
    "refundCheck",
    "authorizeHuca",
    "declinedAlternatives",
  ]);
  $("cdpUrl").value = saved.cdpUrl || "http://127.0.0.1:9222";
  state.helperUrl = new URLSearchParams(window.location.search).get("helperUrl")
    || saved.helperUrl
    || "http://127.0.0.1:8765";
  $("helperUrl").value = state.helperUrl;
  updateSetupDiagnostic();
  if (saved.briefStarter && $("briefStarter").querySelector(`option[value="${CSS.escape(saved.briefStarter)}"]`)) {
    $("briefStarter").value = saved.briefStarter;
  }
  if (saved.taskText) $("taskText").value = saved.taskText;
  if (saved.successCriteria) $("successCriteria").value = saved.successCriteria;
  if (
    saved.templateManual
    && saved.template
    && $("template").querySelector(`option[value="${CSS.escape(saved.template)}"]`)
  ) {
    $("template").value = saved.template;
  }
  if (saved.model) $("model").value = saved.model;
  state.modelSavedLocally = Boolean(saved.model);
  if (saved.chromeProfile) $("chromeProfile").value = saved.chromeProfile;
  state.selectedSite = saved.selectedSite && saved.selectedSite !== "auto"
    ? saved.selectedSite
    : "generic";
  $("sitePicker").value = state.selectedSite;
  state.notifySound = saved.notifySound ?? true;
  state.notifyOs = saved.notifyOs ?? true;
  $("notifySound").checked = state.notifySound;
  $("notifyOs").checked = state.notifyOs;
  $("authorizationTarget").value = saved.authorizationTarget || "";
  $("authorizeClosure").checked = Boolean(saved.authorizeClosure);
  $("authorizeRefund").checked = Boolean(saved.authorizeRefund);
  $("refundChecking").checked = Boolean(saved.refundChecking);
  $("refundCheck").checked = Boolean(saved.refundCheck);
  $("authorizeHuca").checked = Boolean(saved.authorizeHuca);
  $("declinedAlternatives").value = saved.declinedAlternatives || "";
}

function saveRunAuthorization() {
  storageSet({
    authorizationTarget: $("authorizationTarget").value.trim(),
    authorizeClosure: $("authorizeClosure").checked,
    authorizeRefund: $("authorizeRefund").checked,
    refundChecking: $("refundChecking").checked,
    refundCheck: $("refundCheck").checked,
    authorizeHuca: $("authorizeHuca").checked,
    declinedAlternatives: $("declinedAlternatives").value.trim(),
  });
}

function runAuthorizationPayload() {
  const authorizedActions = [];
  if ($("authorizeClosure").checked) authorizedActions.push("close_card");
  if ($("authorizeRefund").checked) authorizedActions.push("request_credit_refund");
  const refundMethods = [];
  if ($("refundChecking").checked) refundMethods.push("existing_checking");
  if ($("refundCheck").checked) refundMethods.push("check");
  const declinedAlternatives = $("declinedAlternatives").value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  return {
    target_account: $("authorizationTarget").value.trim() || null,
    authorized_actions: authorizedActions,
    refund_methods: refundMethods,
    declined_alternatives: declinedAlternatives,
    huca_authorized: $("authorizeHuca").checked,
    user_authorized: true,
  };
}

function applyBriefStarter() {
  const option = $("briefStarter").selectedOptions[0];
  if (!option) return;
  const task = option.dataset.task;
  if (task !== undefined) {
    $("taskText").value = task;
  }
  storageSet({
    briefStarter: $("briefStarter").value,
    taskText: $("taskText").value.trim(),
  });
  if ($("taskText").value.trim()) {
    recordActivationSignal("task_brief_written");
  }
  updateButtons();
}

function saveHelperUrl() {
  state.helperUrl = $("helperUrl").value.trim() || "http://127.0.0.1:8765";
  storageSet({ helperUrl: state.helperUrl });
  updateSetupDiagnostic();
}

function saveNotificationSettings() {
  state.notifySound = $("notifySound").checked;
  state.notifyOs = $("notifyOs").checked;
  storageSet({
    notifySound: state.notifySound,
    notifyOs: state.notifyOs,
  });
}

function saveTemplatePreference() {
  const template = $("template").value || null;
  storageSet({
    template,
    templateManual: Boolean(template),
  });
}

function connectHelper() {
  if (state.socket?.readyState === WebSocket.OPEN) return;

  $("agentStatus").textContent = "connecting";
  saveHelperUrl();
  const wsUrl = state.helperUrl.replace(/^http/, "ws");
  const socket = new WebSocket(`${wsUrl}/ws`);
  state.socket = socket;

  socket.addEventListener("open", () => {
    setConnection(true);
    $("agentStatus").textContent = state.running ? "running" : "ready";
    log("helper", "Connected to local Flying Pig helper.");
    socket.send(JSON.stringify({ type: "list_sites" }));
    socket.send(JSON.stringify({ type: "resolve", url: state.activeUrl }));
    refreshBrowserStatus();
    loadModelSettings();
    if (state.browserStatusTimer) clearInterval(state.browserStatusTimer);
    state.browserStatusTimer = setInterval(refreshBrowserStatus, 5000);
  });

  socket.addEventListener("close", () => {
    state.running = false;
    setConnection(false);
    if (state.browserStatusTimer) clearInterval(state.browserStatusTimer);
    state.browserStatusTimer = null;
    $("agentStatus").textContent = "offline";
    $("runMessage").textContent = "Set up or reconnect the local Flying Pig helper.";
    updateModelSettingsView();
    log("helper", "Disconnected from local Flying Pig helper.");
  });

  socket.addEventListener("error", () => {
    state.running = false;
    setConnection(false);
    if (state.browserStatusTimer) clearInterval(state.browserStatusTimer);
    state.browserStatusTimer = null;
    $("agentStatus").textContent = "error";
    $("runMessage").textContent = "Set up or reconnect the local Flying Pig helper.";
    updateModelSettingsView();
    log("error", `Helper unavailable at ${state.helperUrl}.`);
  });

  socket.addEventListener("message", (event) => {
    try {
      handleHelperMessage(JSON.parse(event.data));
    } catch {
      log("error", "Helper sent an unreadable message.");
    }
  });
}

function handleHelperMessage(message) {
  if (message.type === "ready") {
    log("ready", "Helper is ready.");
  } else if (message.type === "state") {
    setRunState(message);
  } else if (message.type === "resolved") {
    state.activeSite = message.site || "auto";
    $("siteStatus").textContent = siteLabel(message.site, state.sites);
    log("site", `Detected site: ${message.site || "unknown"}`);
    updateButtons();
  } else if (message.type === "sites") {
    renderSites(message.items || []);
  } else if (message.type === "status") {
    $("agentStatus").textContent = message.text || "Working";
    log("status", message.text || "Status updated.");
  } else if (message.type === "progress") {
    const event = message.event || {};
    $("agentStatus").textContent = "Working";
    $("stepStatus").textContent = event.step ? String(event.step) : $("stepStatus").textContent;
    const text = progressMessage(event);
    $("runMessage").textContent = text;
    log(`step ${event.step || ""}`, text);
  } else if (message.type === "timing_span") {
    addTimingSpan(message);
  } else if (message.type === "follow_up_reminder_due") {
    const reminder = message.reminder || {};
    const title = reminder.title || "Customer-service follow-up";
    const body = reminder.message || "A scheduled follow-up is due.";
    notifyAttention(title, body);
    log("follow up", body);
  } else if (isUserAttentionRequest(message)) {
    const request = message.original_type === "decision_checkpoint" || message.type === "decision_checkpoint"
      ? {
          type: message.type,
          original_type: "decision_checkpoint",
          checkpoint: message.checkpoint || {},
          summary: message.summary,
        }
      : {
          type: message.type,
          original_type: message.original_type || "question",
          question: message.question || message.summary || "The agent needs input.",
          reason: message.reason || "agent needs input",
        };
    renderPendingRequest(request);
    maybeNotifyRequest(request);
    log("input", request.question || request.checkpoint?.summary || "The agent needs input.");
  } else if (message.type === "active_human_work") {
    $("agentStatus").textContent = readableRunStatus("waiting_on_rep");
    $("runMessage").textContent = message.summary || "The representative is reviewing. Flying Pig is waiting.";
    log("waiting", message.summary || "Representative is working.");
  } else if (message.type === "preflight_failed") {
    state.running = false;
    updateButtons();
    $("agentStatus").textContent = "Pre-flight blocked";
    renderPreflightFailures(message.failures || []);
    log("preflight", message.text || "Pre-flight check failed.");
  } else if (message.type === "result" || message.type === "result_ready") {
    state.running = false;
    updateButtons();
    $("agentStatus").textContent = readableRunStatus("completed");
    $("runMessage").textContent = message.summary || "Task finished.";
    renderResult(message);
    if (message.human_reached === true || message.result?.human_reached === true) {
      recordActivationSignal("human_reached");
    }
    log(message.status || "result", message.summary || "Task finished.");
  } else if (message.type === "scorecard_updated") {
    if (state.lastResult) {
      state.lastResult.scorecard = message.scorecard || state.lastResult.scorecard;
      renderOutcomeSelection(state.lastResult.scorecard?.user_confirmed_outcome || null);
    }
  } else if (message.type === "error") {
    state.running = false;
    updateButtons();
    $("agentStatus").textContent = "error";
    $("runMessage").textContent = message.text || "Unknown helper error.";
    log("error", message.text || "Unknown helper error.");
  }
}

function renderPendingRequest(request) {
  $("agentStatus").textContent = formatAgentStatus(statusForPendingRequest(request));
  $("runMessage").textContent = pendingRunMessage(request);
  if (request.type === "decision_checkpoint" || request.original_type === "decision_checkpoint") {
    renderDecisionCheckpoint(request.checkpoint || {});
    return;
  }
  $("questionPanel").classList.remove("hidden");
  $("questionTitle").textContent = attentionTitles[request.type] || "Input needed";
  $("questionText").textContent = request.question || "The agent needs input.";
  $("checkpointPanel").classList.add("hidden");
  state.currentCheckpoint = null;
}

function renderPreflightFailures(failures) {
  const items = Array.isArray(failures) ? failures : [];
  state.preflightFailures = items;
  updateReadiness();
  const text = items.map((item) => item.message || item.code).filter(Boolean).join(" ");
  $("runMessage").textContent = text || "Pre-flight check failed.";
  for (const item of items) {
    log("preflight", item.message || item.code || "Pre-flight check failed.");
  }
}

function renderResult(result) {
  if (!result) return;
  if (Array.isArray(result.timing_spans)) {
    renderTimingSpans(result.timing_spans);
  }
  state.lastResult = {
    ...result,
    scorecard: result.scorecard || scorecardFromResult(result),
  };
  $("resultPanel").classList.remove("hidden");
  $("resultSummary").textContent = result.outcome_summary || result.summary || "Task finished.";
  const details = $("resultDetails");
  details.replaceChildren();
  const scorecard = state.lastResult.scorecard || {};
  const rows = [
    ["Scorecard status", scorecard.final_status || result.status || "Unknown"],
    ["Human reached", result.human_reached === null || result.human_reached === undefined ? "Unknown" : (result.human_reached ? "Yes" : "No")],
    ["Offer / result", result.offer_result || "Not captured"],
    ["HUCA attempts", String(scorecard.huca_attempts ?? 0)],
    ["Transcript", result.evidence?.transcript_path || result.transcript || "Not saved yet"],
    ["Timing", result.timing_summary ? `${formatDuration(result.timing_summary.total_ms)} across ${result.timing_summary.span_count} spans` : "Not captured"],
    ["Approvals", String(result.checkpoint_decisions?.length ?? result.checkpoint_events_count ?? 0)],
    ["Unresolved", Array.isArray(result.unresolved_items) && result.unresolved_items.length ? result.unresolved_items.join("; ") : "None captured"],
    ["Confirmation expected", result.confirmation_expected === true ? "Yes" : (result.confirmation_expected === false ? "No" : "Not captured")],
  ];
  for (const [label, value] of rows) {
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = label;
    dd.textContent = value;
    details.append(dt, dd);
  }
  renderResultEvidence(result);
  renderOutcomeSelection(scorecard.user_confirmed_outcome || null);
  renderBetaStats();
}

function renderResultEvidence(result) {
  const checklist = Array.isArray(result.completion_checklist) ? result.completion_checklist : [];
  const completionPanel = $("completionPanel");
  const completionList = $("completionChecklist");
  completionList.replaceChildren();
  completionPanel.classList.toggle("hidden", checklist.length === 0);
  for (const item of checklist) {
    const li = document.createElement("li");
    const status = item.complete ? "Complete" : "Incomplete";
    const deferred = item.deferred ? " (deferred)" : "";
    li.textContent = `${status}${deferred}: ${String(item.id || "goal").replaceAll("_", " ")}${item.evidence ? ` - ${item.evidence}` : ""}`;
    completionList.append(li);
  }

  const followUps = Array.isArray(result.follow_up_actions) ? result.follow_up_actions : [];
  const followUpPanel = $("followUpPanel");
  const followUpList = $("followUpActions");
  followUpList.replaceChildren();
  followUpPanel.classList.toggle("hidden", followUps.length === 0);
  for (const action of followUps) {
    const li = document.createElement("li");
    const summary = document.createElement("div");
    const methods = Array.isArray(action.methods) && action.methods.length
      ? ` via ${action.methods.map((method) => method.replaceAll("_", " ")).join(" or ")}`
      : "";
    summary.textContent = `${String(action.status || "pending")}: ${String(action.type || "follow up").replaceAll("_", " ")}${methods}`;
    const controls = document.createElement("div");
    controls.className = "follow-up-controls";
    const dueAt = document.createElement("input");
    dueAt.type = "datetime-local";
    dueAt.value = defaultReminderDateTime();
    dueAt.setAttribute("aria-label", "Reminder date and time");
    const schedule = document.createElement("button");
    schedule.type = "button";
    schedule.className = "secondary";
    schedule.textContent = "Schedule reminder";
    const status = document.createElement("span");
    status.className = "field-note";
    schedule.addEventListener("click", async () => {
      schedule.disabled = true;
      status.textContent = "Scheduling...";
      try {
        const reminder = await scheduleFollowUpReminder(action, dueAt.value);
        status.textContent = `Scheduled for ${new Date(reminder.due_at).toLocaleString()}.`;
      } catch (error) {
        status.textContent = error.message || "Could not schedule reminder.";
        schedule.disabled = false;
      }
    });
    controls.append(dueAt, schedule, status);
    li.append(summary, controls);
    followUpList.append(li);
  }
}

function defaultReminderDateTime() {
  const date = new Date();
  date.setDate(date.getDate() + 1);
  date.setHours(9, 0, 0, 0);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

async function scheduleFollowUpReminder(action, localDueAt) {
  const dueAt = new Date(localDueAt);
  if (!localDueAt || Number.isNaN(dueAt.getTime())) {
    throw new Error("Choose a valid reminder date and time.");
  }
  const methods = Array.isArray(action.methods) && action.methods.length
    ? action.methods.map((method) => method.replaceAll("_", " ")).join(" or ")
    : "the available method";
  const response = await fetch(`${state.helperUrl}/follow-up-reminders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: "Flying Pig follow-up",
      message: `Contact customer service and request the deferred resolution via ${methods}.`,
      due_at: dueAt.toISOString(),
      source: action,
    }),
  });
  const payload = await response.json();
  if (!response.ok || !payload.ok) {
    throw new Error(payload.error || "Could not schedule reminder.");
  }
  return payload.reminder;
}

function scorecardFromResult(result) {
  return {
    schema_version: 1,
    goal_type: "automatic",
    site_profile: state.selectedSite || state.activeSite || "generic",
    final_status: result.status || "unknown",
    human_reached: result.human_reached,
    huca_attempts: 0,
    checkpoint_count: result.checkpoint_decisions?.length ?? result.checkpoint_events_count ?? 0,
    user_intervention_count: result.checkpoint_decisions?.length ?? result.checkpoint_events_count ?? 0,
    duration_seconds: result.duration || 0,
    timing_total_ms: result.timing_summary?.total_ms || 0,
    offer_result: result.offer_result || null,
    blocked_reason: null,
    unresolved_items_count: Array.isArray(result.unresolved_items) ? result.unresolved_items.length : 0,
    user_confirmed_outcome: null,
  };
}

function renderOutcomeSelection(outcome) {
  $("outcomeStatus").textContent = outcome
    ? `Marked ${outcomeLabels[outcome] || outcome} for local beta stats.`
    : "Mark the outcome to improve local beta stats.";
  for (const [buttonId, value] of [
    ["markSolved", "solved"],
    ["markPartial", "partial"],
    ["markFailed", "failed"],
  ]) {
    $(buttonId).classList.toggle("selected", outcome === value);
  }
}

async function markRunOutcome(outcome) {
  if (!state.lastResult?.scorecard) return;
  const scorecard = {
    ...state.lastResult.scorecard,
    user_confirmed_outcome: outcome,
    recorded_at: new Date().toISOString(),
  };
  state.lastResult.scorecard = scorecard;
  renderOutcomeSelection(outcome);
  await saveLocalScorecard(scorecard);
  recordActivationSignal("outcome_marked");
  renderBetaStats();
  try {
    const response = await fetch(`${state.helperUrl}/run/outcome`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ outcome }),
    });
    if (!response.ok) {
      log("scorecard", "Outcome saved locally; helper did not accept the update.");
    }
  } catch {
    log("scorecard", "Outcome saved locally; helper update unavailable.");
  }
}

async function saveLocalScorecard(scorecard) {
  const saved = await storageGet([betaScorecardsKey]);
  const previous = Array.isArray(saved[betaScorecardsKey]) ? saved[betaScorecardsKey] : [];
  const next = [scorecard, ...previous].slice(0, 50);
  storageSet({ [betaScorecardsKey]: next });
}

async function renderBetaStats() {
  const saved = await storageGet([betaScorecardsKey]);
  const cards = Array.isArray(saved[betaScorecardsKey]) ? saved[betaScorecardsKey] : [];
  const confirmed = cards.filter((card) => card.user_confirmed_outcome);
  const solved = confirmed.filter((card) => card.user_confirmed_outcome === "solved").length;
  const partial = confirmed.filter((card) => card.user_confirmed_outcome === "partial").length;
  const failed = confirmed.filter((card) => card.user_confirmed_outcome === "failed").length;
  const humanReached = confirmed.filter((card) => card.human_reached === true).length;
  const hucaRuns = confirmed.filter((card) => Number(card.huca_attempts || 0) > 0).length;
  const stats = [
    ["Marked runs", String(confirmed.length)],
    ["Solved", ratioText(solved, confirmed.length)],
    ["Partial", ratioText(partial, confirmed.length)],
    ["Failed", ratioText(failed, confirmed.length)],
    ["Human reached", ratioText(humanReached, confirmed.length)],
    ["HUCA used", ratioText(hucaRuns, confirmed.length)],
  ];
  $("betaStats").replaceChildren();
  for (const [label, value] of stats) {
    const item = document.createElement("div");
    const title = document.createElement("span");
    const metric = document.createElement("strong");
    title.textContent = label;
    metric.textContent = value;
    item.append(title, metric);
    $("betaStats").append(item);
  }
}

function ratioText(count, total) {
  if (!total) return count ? String(count) : "-";
  return `${count}/${total}`;
}

function renderDecisionCheckpoint(checkpoint) {
  state.currentCheckpoint = checkpoint;
  $("questionPanel").classList.add("hidden");
  $("checkpointPanel").classList.remove("hidden");
  $("checkpointType").textContent = checkpoint.type
    ? checkpoint.type.replaceAll("_", " ")
    : "Decision needed";
  $("checkpointSummary").textContent = checkpoint.summary || "Choose how to proceed.";
  $("checkpointOptions").replaceChildren();
  const options = Array.isArray(checkpoint.options) ? checkpoint.options : [];
  for (const option of options) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "checkpoint-option";
    if (option.id === checkpoint.recommended_option_id) {
      button.classList.add("recommended");
    }

    const label = document.createElement("strong");
    label.textContent = option.id === checkpoint.recommended_option_id
      ? `${option.label} (Recommended)`
      : option.label;
    const consequence = document.createElement("span");
    consequence.textContent = option.consequence || "";
    button.append(label, consequence);
    if (option.message_to_send) {
      const message = document.createElement("code");
      message.textContent = option.message_to_send;
      button.append(message);
    }
    button.addEventListener("click", () => sendCheckpointOption(option));
    $("checkpointOptions").append(button);
  }
}

async function startTask() {
  const task = $("taskText").value.trim();
  if (!task) return;

  if (state.browserBackend !== "mcp" && !state.browserConnected) {
    state.workflowStage = "preparing";
    state.lastResult = null;
    $("preparationMessage").textContent = "Opening a work window. Log in and navigate to the customer-service chat.";
    updateWorkflowView();
    const opened = await launchChrome();
    $("preparationMessage").textContent = opened
      ? "Log in and navigate to the customer-service chat, then return here."
      : "The work window could not be opened. Try again or check Settings.";
    updateWorkflowView();
    return;
  }

  if (!state.activeUrl) {
    state.workflowStage = "preparing";
    $("preparationMessage").textContent = "Navigate to the customer-service chat in the work window, then return here.";
    updateWorkflowView();
    return;
  }

  beginRun(task);
}

function beginRun(task) {

  const payload = buildRunPayload(task);
  state.lastResult = null;
  $("resultPanel").classList.add("hidden");
  state.running = true;
  state.workflowStage = "running";
  state.activityOpen = false;
  recordActivationSignal("first_run_started");
  updateButtons();
  $("agentStatus").textContent = "Preparing";
  $("runMessage").textContent = "Checking permissions and preparing the supervised run.";
  state.socket.send(JSON.stringify({ type: "start", ...payload }));
  log("start", "Started Flying Pig for the work window.");
  updateWorkflowView();
}

async function confirmBrowserReady() {
  await refreshTab();
  if (!state.browserConnected) {
    const opened = await launchChrome();
    if (!opened) return;
  }
  if (!state.activeUrl) {
    $("preparationMessage").textContent = "Open a support page or chat in the work window, then try again.";
    return;
  }
  const task = $("taskText").value.trim();
  if (task) beginRun(task);
}

async function hucaTask() {
  if (state.browserBackend !== "mcp") {
    const browserReady = await refreshBrowserStatus();
    if (!browserReady) {
      $("agentStatus").textContent = "waiting";
      $("runMessage").textContent = "Launch the work window before restarting.";
      log("browser", "Controlled Chrome is not connected.");
      return;
    }
  }
  const task = $("taskText").value.trim();
  if (!task) return;

  const payload = buildRunPayload(task);
  state.running = true;
  updateButtons();
  $("agentStatus").textContent = "restarting";
  $("runMessage").textContent = "Starting a fresh chat for the same task.";
  state.socket.send(JSON.stringify({ type: "huca", ...payload }));
  $("questionPanel").classList.add("hidden");
  $("checkpointPanel").classList.add("hidden");
  state.currentCheckpoint = null;
  state.notifiedRequestKey = null;
  log("huca", "Requested a fresh chat for the same task.");
}

function buildRunPayload(task) {
  const cdpUrl = state.browserBackend === "mcp" ? null : browserEndpoint();
  const template = $("template").value || null;
  const model = $("model").value;
  const successCriteria = $("successCriteria").value.trim();
  saveHelperUrl();
  storageSet({
    taskText: task,
    successCriteria,
    cdpUrl,
    template,
    templateManual: Boolean(template),
    model,
  });

  return {
    site: state.selectedSite || state.activeSite || "generic",
    url: state.activeUrl,
    template,
    task,
    success_criteria: successCriteria,
    cdp_url: cdpUrl,
    target_url: state.activeUrl,
    target_tab_id: state.activeTabId,
    browser_backend: state.browserBackend || "browser_use",
    mcp_page: state.selectedMcpPage,
    model,
    max_steps: 80,
    permission_mode: "supervised_browser",
    user_authorized: true,
    evidence_capture: true,
    login_expectation: "manual_visible_browser",
    irreversible_actions_require_checkpoint: true,
    authorization: runAuthorizationPayload(),
  };
}

function cancelTask() {
  state.socket?.send(JSON.stringify({ type: "cancel" }));
  state.running = false;
  updateButtons();
  $("agentStatus").textContent = "cancelling";
  $("runMessage").textContent = "Cancelling.";
  log("cancel", "Cancel requested.");
  state.workflowStage = "ready";
  updateWorkflowView();
}

function sendAnswer() {
  const text = $("answerText").value.trim();
  if (!text) return;
  state.socket?.send(JSON.stringify({ type: "answer", text }));
  $("answerText").value = "";
  $("questionPanel").classList.add("hidden");
  state.notifiedRequestKey = null;
  log("answer", "Sent answer to agent.");
}

function sendCheckpointOption(option) {
  if (!state.currentCheckpoint || !option) return;
  state.socket?.send(JSON.stringify({
    type: "answer",
    payload: checkpointOptionAnswer(state.currentCheckpoint, option),
  }));
  $("checkpointPanel").classList.add("hidden");
  state.notifiedRequestKey = null;
  recordActivationSignal("checkpoint_answered");
  log("decision", `Selected: ${option.label}`);
}

function sendCheckpointCustom() {
  if (!state.currentCheckpoint) return;
  const text = $("checkpointCustomText").value.trim();
  if (!text) return;
  state.socket?.send(JSON.stringify({
    type: "answer",
    payload: checkpointCustomAnswer(state.currentCheckpoint, text),
  }));
  $("checkpointCustomText").value = "";
  $("checkpointPanel").classList.add("hidden");
  state.notifiedRequestKey = null;
  recordActivationSignal("checkpoint_answered");
  log("decision", "Sent custom instruction.");
}

document.addEventListener("DOMContentLoaded", async () => {
  await loadSettings();
  await loadActivationSignals();
  await refreshTab();
  setConnection(false);

  $("refreshTab").addEventListener("click", refreshTab);
  $("autoConnectChrome").addEventListener("click", autoConnectChrome);
  $("attachChrome").addEventListener("click", attachChrome);
  $("launchChrome").addEventListener("click", launchChrome);
  $("statusLaunchChrome").addEventListener("click", launchChrome);
  $("browserReady").addEventListener("click", confirmBrowserReady);
  $("backToTask").addEventListener("click", () => {
    state.workflowStage = "ready";
    updateWorkflowView();
  });
  $("activityToggle").addEventListener("click", () => {
    state.activityOpen = !state.activityOpen;
    updateWorkflowView();
  });
  $("focusedCancel").addEventListener("click", cancelTask);
  $("modelSettingsToggle").addEventListener("click", () => {
    state.settingsOpen = !state.settingsOpen;
    updateExperienceMode();
    if (state.settingsOpen) $("firstRunPanel").scrollIntoView({ behavior: "smooth", block: "start" });
  });
  $("guideConfigure").addEventListener("click", () => {
    state.settingsOpen = true;
    updateExperienceMode();
    $("firstRunPanel").scrollIntoView({ behavior: "smooth", block: "start" });
  });
  $("guideOpenWebsite").addEventListener("click", openWebsiteGuide);
  $("setupHelper").addEventListener("click", openSetup);
  $("reconnectHelper").addEventListener("click", () => {
    state.socket?.close();
    state.socket = null;
    connectHelper();
  });
  $("sitePicker").addEventListener("change", () => {
    state.selectedSite = $("sitePicker").value || "generic";
    storageSet({ selectedSite: state.selectedSite });
    updateButtons();
  });
  $("chromeProfile").addEventListener("change", () => {
    storageSet({ chromeProfile: $("chromeProfile").value || "dedicated" });
  });
  $("briefStarter").addEventListener("change", applyBriefStarter);
  $("template").addEventListener("change", saveTemplatePreference);
  $("model").addEventListener("change", () => {
    storageSet({ model: $("model").value });
    state.modelSavedLocally = true;
    updateModelSettingsView();
    updateButtons();
  });
  $("saveModelSettings").addEventListener("click", () => saveModelSettings());
  $("clearModelKey").addEventListener("click", () => saveModelSettings({ clearKey: true }));
  $("taskText").addEventListener("input", () => {
    storageSet({ taskText: $("taskText").value.trim() });
    if ($("taskText").value.trim()) {
      recordActivationSignal("task_brief_written");
    }
    updateButtons();
  });
  $("successCriteria").addEventListener("input", () => {
    storageSet({ successCriteria: $("successCriteria").value.trim() });
  });
  for (const id of [
    "authorizationTarget",
    "authorizeClosure",
    "authorizeRefund",
    "refundChecking",
    "refundCheck",
    "authorizeHuca",
    "declinedAlternatives",
  ]) {
    $(id).addEventListener("change", saveRunAuthorization);
  }
  $("notifySound").addEventListener("change", saveNotificationSettings);
  $("notifyOs").addEventListener("change", saveNotificationSettings);
  $("helperUrl").addEventListener("change", () => {
    saveHelperUrl();
    state.socket?.close();
    state.socket = null;
    connectHelper();
  });
  $("startTask").addEventListener("click", startTask);
  $("hucaTask").addEventListener("click", hucaTask);
  $("cancelTask").addEventListener("click", cancelTask);
  $("sendAnswer").addEventListener("click", sendAnswer);
  $("sendCheckpointCustom").addEventListener("click", sendCheckpointCustom);
  $("markSolved").addEventListener("click", () => markRunOutcome("solved"));
  $("markPartial").addEventListener("click", () => markRunOutcome("partial"));
  $("markFailed").addEventListener("click", () => markRunOutcome("failed"));
  $("clearLog").addEventListener("click", () => $("log").replaceChildren());

  connectHelper();
});
