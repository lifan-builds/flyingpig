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
};

const betaScorecardsKey = "betaScorecards";
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
}

function setBrowserConnection(connected, label) {
  state.browserConnected = connected;
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
}

function updateButtons() {
  const hasTask = Boolean($("taskText").value.trim());
  const canLaunchBrowser = state.connected && !state.running && !state.browserLaunching;
  const startReason = startDisabledReason({ hasTask });
  $("startTask").disabled = Boolean(startReason);
  $("hucaTask").disabled = !state.connected || !state.browserConnected || !hasTask;
  $("cancelTask").disabled = !state.connected || !state.running;
  $("launchChrome").disabled = !canLaunchBrowser;
  $("refreshTab").disabled = !state.connected || !state.browserConnected;
  $("statusLaunchChrome").classList.toggle("hidden", !state.connected || state.browserConnected);
  $("statusLaunchChrome").disabled = !canLaunchBrowser;
  $("startDisabledReason").textContent = startReason || "Ready to start when the chat surface is prepared.";
  $("startDisabledReason").classList.toggle("ready", !startReason);
  updateReadiness();
}

function startDisabledReason({ hasTask } = { hasTask: Boolean($("taskText").value.trim()) }) {
  if (!state.connected) return "Reconnect the Flying Pig helper before starting.";
  if (state.browserLaunching) return "Wait for the work window to finish opening.";
  if (!state.browserConnected) return "Open the work window before starting.";
  if (!state.activeUrl) return "Prepare a visible support page or chat surface in the work window.";
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
  updateReadiness();
  updateButtons();
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
  if (!state.connected || state.running || state.browserLaunching) return;
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
        cdp_port: 9222,
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
    $("agentStatus").textContent = "ready";
    $("runMessage").textContent = payload.message || "Work window is ready.";
    log("browser", payload.message || "Work window is ready.");
  } catch (error) {
    $("agentStatus").textContent = "error";
    $("runMessage").textContent = error.message || "Browser launch failed.";
    log("error", error.message || "Browser launch failed.");
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
  try {
    const cdpUrl = $("cdpUrl").value.trim() || "http://127.0.0.1:9222";
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
  ];
  for (const [label, value] of rows) {
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = label;
    dd.textContent = value;
    details.append(dt, dd);
  }
  renderOutcomeSelection(scorecard.user_confirmed_outcome || null);
  renderBetaStats();
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
  const browserReady = await refreshBrowserStatus();
  if (!browserReady) {
    $("agentStatus").textContent = "waiting";
    $("runMessage").textContent = "Launch the work window before starting.";
    log("browser", "Controlled Chrome is not connected.");
    return;
  }
  const task = $("taskText").value.trim();
  if (!task) return;

  const payload = buildRunPayload(task);
  state.running = true;
  updateButtons();
  $("agentStatus").textContent = "Preparing";
  $("runMessage").textContent = "Checking permissions and preparing the supervised run.";
  state.socket.send(JSON.stringify({ type: "start", ...payload }));
  log("start", "Started Flying Pig for the work window.");
}

async function hucaTask() {
  const browserReady = await refreshBrowserStatus();
  if (!browserReady) {
    $("agentStatus").textContent = "waiting";
    $("runMessage").textContent = "Launch the work window before restarting.";
    log("browser", "Controlled Chrome is not connected.");
    return;
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
  const cdpUrl = $("cdpUrl").value.trim() || "http://127.0.0.1:9222";
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
    model,
    max_steps: 80,
    permission_mode: "supervised_browser",
    user_authorized: true,
    evidence_capture: true,
    login_expectation: "manual_visible_browser",
    irreversible_actions_require_checkpoint: true,
  };
}

function cancelTask() {
  state.socket?.send(JSON.stringify({ type: "cancel" }));
  state.running = false;
  updateButtons();
  $("agentStatus").textContent = "cancelling";
  $("runMessage").textContent = "Cancelling.";
  log("cancel", "Cancel requested.");
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
  log("decision", "Sent custom instruction.");
}

document.addEventListener("DOMContentLoaded", async () => {
  await loadSettings();
  await refreshTab();
  setConnection(false);

  $("refreshTab").addEventListener("click", refreshTab);
  $("launchChrome").addEventListener("click", launchChrome);
  $("statusLaunchChrome").addEventListener("click", launchChrome);
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
  });
  $("saveModelSettings").addEventListener("click", () => saveModelSettings());
  $("clearModelKey").addEventListener("click", () => saveModelSettings({ clearKey: true }));
  $("taskText").addEventListener("input", () => {
    storageSet({ taskText: $("taskText").value.trim() });
    updateButtons();
  });
  $("successCriteria").addEventListener("input", () => {
    storageSet({ successCriteria: $("successCriteria").value.trim() });
  });
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
