import {
  attentionForRequest,
  checkpointCustomAnswer,
  checkpointOptionAnswer,
  fallbackPendingRequest,
  formatTime,
  requestKey,
  siteLabel,
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
  browserStatusTimer: null,
  currentCheckpoint: null,
  helperUrl: "http://127.0.0.1:8765",
  notifySound: true,
  notifyOs: true,
  notifiedRequestKey: null,
};

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
  if (!state.notifyOs || !chrome.notifications) return;
  chrome.notifications.create({
    type: "basic",
    iconUrl: "src/notification.svg",
    title,
    message,
  });
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
  updateButtons();
}

function setBrowserConnection(connected, label) {
  state.browserConnected = connected;
  $("browserStatus").textContent = label || (connected ? "Work Window Connected" : "Work Window Offline");
  $("browserStatus").className = `pill ${connected ? "connected" : "disconnected"}`;
  $("currentUrlLabel").textContent = connected ? "Work Window URL" : "Launch URL";
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
  $("agentStatus").textContent = formatAgentStatus(status);
  $("stepStatus").textContent = message.step ? String(message.step) : "-";
  $("runMessage").textContent = pendingRequest
    ? pendingRunMessage(pendingRequest)
    : message.message || "Ready";
  $("startedAt").textContent = formatTime(message.started_at);
  $("updatedAt").textContent = formatTime(message.updated_at);

  if (pendingRequest) {
    renderPendingRequest(pendingRequest);
    maybeNotifyRequest(pendingRequest);
  } else if (!message.needs_input) {
    $("questionPanel").classList.add("hidden");
    $("checkpointPanel").classList.add("hidden");
    state.currentCheckpoint = null;
    state.notifiedRequestKey = null;
  }
  updateButtons();
}

function updateButtons() {
  const hasTask = Boolean($("taskText").value.trim());
  $("startTask").disabled = !state.connected || !state.browserConnected || state.running || !hasTask;
  $("cancelTask").disabled = !state.connected || !state.running;
  $("launchChrome").disabled = !state.connected || state.running;
  $("refreshTab").disabled = !state.connected || !state.browserConnected;
}

function updateSetupDiagnostic() {
  $("setupDiagnostic").textContent = `${state.helperUrl} unavailable`;
}

function siteForAction() {
  if (state.selectedSite) return state.selectedSite;
  if (state.activeSite && state.activeSite !== "unknown") {
    return state.activeSite;
  }
  return "generic";
}

function formatAgentStatus(status) {
  if (status === "needs_input") return "Needs input";
  if (status === "running") return "Running";
  if (status === "starting") return "Starting";
  if (status === "idle") return "Ready";
  return status || "Ready";
}

function pendingRunMessage(request) {
  if (request?.type === "decision_checkpoint") {
    return "Choose how Flying Pig should proceed below.";
  }
  return "Answer the prompt below so Flying Pig can continue.";
}

function progressMessage(event) {
  const raw = event.message || event.goal || event.thought || "";
  if (raw && !/^Step \d+ started$/.test(raw)) return raw;
  if (event.phase === "starting") {
    return "Checking the current page and chat state before the next action.";
  }
  return "Working on the customer-service chat.";
}

function setTaskUrl(url, { workWindow = false } = {}) {
  const previousUrl = state.activeUrl;
  state.activeUrl = url || "";
  state.activeTabId = workWindow ? null : state.activeTabId;
  $("currentUrl").value = state.activeUrl;
  chrome.storage.local.set({ activeUrl: state.activeUrl });
  if (state.connected && state.activeUrl && state.activeUrl !== previousUrl) {
    state.socket?.send(JSON.stringify({ type: "resolve", url: state.activeUrl }));
  }
}

function applyBrowserPayload(payload) {
  if (!payload?.connected || !payload.current_url) return;
  setTaskUrl(payload.current_url, { workWindow: true });
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
  chrome.storage.local.set({ activeUrl: state.activeUrl });
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
  if (!chrome.windows?.getCurrent || !chrome.windows?.update) return fallback;

  const availableWidth = window.screen?.availWidth || 0;
  const availableHeight = window.screen?.availHeight || 0;
  if (availableWidth < 1500 || availableHeight < 720) return fallback;

  const cockpitWidth = Math.min(580, Math.max(500, Math.floor(availableWidth * 0.34)));
  const gap = 8;
  const workWidth = Math.max(900, availableWidth - cockpitWidth - gap);
  const workHeight = Math.max(720, availableHeight);
  try {
    const current = await chrome.windows.getCurrent();
    await chrome.windows.update(current.id, {
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
  if (!state.connected || state.running) return;
  $("agentStatus").textContent = "launching";
  $("runMessage").textContent = "Launching Flying Pig work window.";
  log("browser", "Launch requested.");

  try {
    const site = siteForAction();
    const initialUrl = site === "generic" && state.activeUrl ? state.activeUrl : undefined;
    const placement = await workWindowPlacement();
    const response = await fetch(`${state.helperUrl}/browser/launch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        site,
        cdp_port: 9222,
        chrome_profile: "dedicated",
        initial_url: initialUrl,
        ...placement,
      }),
    });
    const payload = await response.json();
    if (!payload.ok) {
      throw new Error(payload.error || "Browser launch failed.");
    }
    $("cdpUrl").value = payload.cdp_url || "http://127.0.0.1:9222";
    chrome.storage.local.set({ cdpUrl: $("cdpUrl").value });
    setBrowserConnection(true, "Work Window Connected");
    applyBrowserPayload({ ...payload, connected: true });
    $("agentStatus").textContent = "ready";
    $("runMessage").textContent = payload.message || "Work window is ready.";
    log("browser", payload.message || "Work window is ready.");
  } catch (error) {
    $("agentStatus").textContent = "error";
    $("runMessage").textContent = error.message || "Browser launch failed.";
    log("error", error.message || "Browser launch failed.");
  }
}

async function openSetup() {
  const url = chrome.runtime.getURL("src/setup.html");
  await chrome.tabs.create({ url });
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
      chrome.storage.local.set({ cdpUrl: payload.cdp_url });
    }
    applyBrowserPayload(payload);
    return Boolean(payload.connected);
  } catch {
    setBrowserConnection(false, "Work Window Offline");
    return false;
  }
}

async function loadSettings() {
  const saved = await chrome.storage.local.get([
    "cdpUrl",
    "taskText",
    "template",
    "model",
    "helperUrl",
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
  if (saved.taskText) $("taskText").value = saved.taskText;
  if (saved.template) $("template").value = saved.template;
  if (saved.model) $("model").value = saved.model;
  state.selectedSite = saved.selectedSite && saved.selectedSite !== "auto"
    ? saved.selectedSite
    : "generic";
  $("sitePicker").value = state.selectedSite;
  state.notifySound = saved.notifySound ?? true;
  state.notifyOs = saved.notifyOs ?? true;
  $("notifySound").checked = state.notifySound;
  $("notifyOs").checked = state.notifyOs;
}

function saveHelperUrl() {
  state.helperUrl = $("helperUrl").value.trim() || "http://127.0.0.1:8765";
  chrome.storage.local.set({ helperUrl: state.helperUrl });
  updateSetupDiagnostic();
}

function saveNotificationSettings() {
  state.notifySound = $("notifySound").checked;
  state.notifyOs = $("notifyOs").checked;
  chrome.storage.local.set({
    notifySound: state.notifySound,
    notifyOs: state.notifyOs,
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
    log("helper", "Disconnected from local Flying Pig helper.");
  });

  socket.addEventListener("error", () => {
    state.running = false;
    setConnection(false);
    if (state.browserStatusTimer) clearInterval(state.browserStatusTimer);
    state.browserStatusTimer = null;
    $("agentStatus").textContent = "error";
    $("runMessage").textContent = "Set up or reconnect the local Flying Pig helper.";
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
    $("agentStatus").textContent = message.text || "working";
    log("status", message.text || "Status updated.");
  } else if (message.type === "progress") {
    const event = message.event || {};
    $("agentStatus").textContent = "Running";
    $("stepStatus").textContent = event.step ? String(event.step) : $("stepStatus").textContent;
    const text = progressMessage(event);
    $("runMessage").textContent = text;
    log(`step ${event.step || ""}`, text);
  } else if (message.type === "question") {
    const request = {
      type: "question",
      question: message.question || "The agent needs input.",
      reason: message.reason || "agent needs input",
    };
    renderPendingRequest(request);
    maybeNotifyRequest(request);
    log("input", message.question || "The agent needs input.");
  } else if (message.type === "decision_checkpoint") {
    const request = {
      type: "decision_checkpoint",
      checkpoint: message.checkpoint || {},
    };
    renderPendingRequest(request);
    maybeNotifyRequest(request);
    log("decision", message.checkpoint?.summary || "Decision checkpoint.");
  } else if (message.type === "result") {
    state.running = false;
    updateButtons();
    $("agentStatus").textContent = message.status || "finished";
    $("runMessage").textContent = message.summary || "Task finished.";
    log(message.status || "result", message.summary || "Task finished.");
  } else if (message.type === "error") {
    state.running = false;
    updateButtons();
    $("agentStatus").textContent = "error";
    $("runMessage").textContent = message.text || "Unknown helper error.";
    log("error", message.text || "Unknown helper error.");
  }
}

function renderPendingRequest(request) {
  $("agentStatus").textContent = "Needs input";
  $("runMessage").textContent = pendingRunMessage(request);
  if (request.type === "decision_checkpoint") {
    renderDecisionCheckpoint(request.checkpoint || {});
    return;
  }
  $("questionPanel").classList.remove("hidden");
  $("questionText").textContent = request.question || "The agent needs input.";
  $("checkpointPanel").classList.add("hidden");
  state.currentCheckpoint = null;
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

  const cdpUrl = $("cdpUrl").value.trim() || "http://127.0.0.1:9222";
  const template = $("template").value;
  const model = $("model").value;
  saveHelperUrl();
  chrome.storage.local.set({ taskText: task, cdpUrl, template, model });

  state.running = true;
  updateButtons();
  $("agentStatus").textContent = "starting";
  $("runMessage").textContent = "Starting browser-use agent.";
  state.socket.send(JSON.stringify({
    type: "start",
    site: state.selectedSite || state.activeSite || "generic",
    url: state.activeUrl,
    template,
    task,
    cdp_url: cdpUrl,
    target_url: state.activeUrl,
    target_tab_id: state.activeTabId,
    model,
    max_steps: 80,
  }));
  log("start", "Started Flying Pig for the work window.");
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
  $("setupHelper").addEventListener("click", openSetup);
  $("reconnectHelper").addEventListener("click", () => {
    state.socket?.close();
    state.socket = null;
    connectHelper();
  });
  $("sitePicker").addEventListener("change", () => {
    state.selectedSite = $("sitePicker").value || "generic";
    chrome.storage.local.set({ selectedSite: state.selectedSite });
    updateButtons();
  });
  $("taskText").addEventListener("input", updateButtons);
  $("notifySound").addEventListener("change", saveNotificationSettings);
  $("notifyOs").addEventListener("change", saveNotificationSettings);
  $("helperUrl").addEventListener("change", () => {
    saveHelperUrl();
    state.socket?.close();
    state.socket = null;
    connectHelper();
  });
  $("startTask").addEventListener("click", startTask);
  $("cancelTask").addEventListener("click", cancelTask);
  $("sendAnswer").addEventListener("click", sendAnswer);
  $("sendCheckpointCustom").addEventListener("click", sendCheckpointCustom);
  $("clearLog").addEventListener("click", () => $("log").replaceChildren());

  connectHelper();
});
