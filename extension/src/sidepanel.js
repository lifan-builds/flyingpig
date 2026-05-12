import {
  attentionForRequest,
  checkpointCustomAnswer,
  checkpointOptionAnswer,
  fallbackPendingRequest,
  formatTime,
  requestKey,
  siteLabel,
} from "./sidepanel_protocol.js";

const $ = (id) => document.getElementById(id);

const state = {
  socket: null,
  connected: false,
  activeUrl: "",
  activeTabId: null,
  activeSite: "auto",
  running: false,
  currentCheckpoint: null,
  helperUrl: "http://127.0.0.1:8765",
  notifySound: true,
  notifyOs: true,
  notifiedRequestKey: null,
};

function log(kind, text) {
  const item = document.createElement("li");
  const title = document.createElement("strong");
  const body = document.createElement("span");
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
  updateButtons();
}

function setRunState(message) {
  state.running = Boolean(message.running);
  if (message.site) {
    state.activeSite = message.site;
    $("siteStatus").textContent = siteLabel(message.site);
  }
  $("agentStatus").textContent = message.status || (state.running ? "running" : "ready");
  $("stepStatus").textContent = message.step ? String(message.step) : "-";
  $("runMessage").textContent = message.message || "Ready";
  $("startedAt").textContent = formatTime(message.started_at);
  $("updatedAt").textContent = formatTime(message.updated_at);

  if (message.pending_request) {
    renderPendingRequest(message.pending_request);
    maybeNotifyRequest(message.pending_request);
  } else if (fallbackPendingRequest(message)) {
    renderPendingRequest(fallbackPendingRequest(message));
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
  $("startTask").disabled = !state.connected || state.running || !hasTask;
  $("cancelTask").disabled = !state.connected || !state.running;
  $("launchChrome").disabled = !state.connected || state.running;
}

async function refreshTab() {
  const overrideUrl = new URLSearchParams(window.location.search).get("targetUrl");
  if (overrideUrl) {
    state.activeUrl = overrideUrl;
    state.activeTabId = null;
  } else {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    state.activeUrl = tab?.url || "";
    state.activeTabId = tab?.id || null;
  }
  $("currentUrl").value = state.activeUrl;
  chrome.storage.local.set({ activeUrl: state.activeUrl });
  if (state.connected) {
    state.socket?.send(JSON.stringify({ type: "resolve", url: state.activeUrl }));
  }
}

async function openOura() {
  await chrome.tabs.create({
    url: "https://support.ouraring.com/hc/en-us/articles/360047222554-Contact-Us",
  });
}

async function launchChrome() {
  if (!state.connected || state.running) return;
  $("agentStatus").textContent = "launching";
  $("runMessage").textContent = "Launching FlyingPig Chrome.";
  log("browser", "Launch requested.");

  try {
    const response = await fetch(`${state.helperUrl}/browser/launch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        site: state.activeSite && state.activeSite !== "unknown" ? state.activeSite : "generic",
        cdp_port: 9222,
        chrome_profile: "default",
        initial_url: state.activeUrl || undefined,
      }),
    });
    const payload = await response.json();
    if (!payload.ok) {
      throw new Error(payload.error || "Browser launch failed.");
    }
    $("cdpUrl").value = payload.cdp_url || "http://127.0.0.1:9222";
    chrome.storage.local.set({ cdpUrl: $("cdpUrl").value });
    $("agentStatus").textContent = "ready";
    $("runMessage").textContent = payload.message || "Chrome is ready.";
    log("browser", payload.message || "Chrome is ready.");
  } catch (error) {
    $("agentStatus").textContent = "error";
    $("runMessage").textContent = error.message || "Browser launch failed.";
    log("error", error.message || "Browser launch failed.");
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
  ]);
  $("cdpUrl").value = saved.cdpUrl || "http://127.0.0.1:9222";
  state.helperUrl = new URLSearchParams(window.location.search).get("helperUrl")
    || saved.helperUrl
    || "http://127.0.0.1:8765";
  $("helperUrl").value = state.helperUrl;
  if (saved.taskText) $("taskText").value = saved.taskText;
  if (saved.template) $("template").value = saved.template;
  if (saved.model) $("model").value = saved.model;
  state.notifySound = saved.notifySound ?? true;
  state.notifyOs = saved.notifyOs ?? true;
  $("notifySound").checked = state.notifySound;
  $("notifyOs").checked = state.notifyOs;
}

function saveHelperUrl() {
  state.helperUrl = $("helperUrl").value.trim() || "http://127.0.0.1:8765";
  chrome.storage.local.set({ helperUrl: state.helperUrl });
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
    socket.send(JSON.stringify({ type: "resolve", url: state.activeUrl }));
  });

  socket.addEventListener("close", () => {
    state.running = false;
    setConnection(false);
    $("agentStatus").textContent = "offline";
    $("runMessage").textContent = "Start the local helper with: flyingpig-helper";
    log("helper", "Disconnected from local Flying Pig helper.");
  });

  socket.addEventListener("error", () => {
    state.running = false;
    setConnection(false);
    $("agentStatus").textContent = "error";
    $("runMessage").textContent = "Helper unavailable. Run: flyingpig-helper";
    log("error", "Helper unavailable. Run: flyingpig-helper");
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
    $("siteStatus").textContent = siteLabel(message.site);
    log("site", `Detected site: ${message.site || "unknown"}`);
  } else if (message.type === "status") {
    $("agentStatus").textContent = message.text || "working";
    log("status", message.text || "Status updated.");
  } else if (message.type === "progress") {
    const event = message.event || {};
    $("agentStatus").textContent = "running";
    $("stepStatus").textContent = event.step ? String(event.step) : $("stepStatus").textContent;
    $("runMessage").textContent = event.message || event.goal || event.thought || "Working";
    log(`step ${event.step || ""}`, event.message || event.goal || event.thought || "Progress");
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
  $("agentStatus").textContent = "needs_input";
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
  await refreshTab();
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
    site: state.activeSite || "auto",
    url: state.activeUrl,
    template,
    task,
    cdp_url: cdpUrl,
    target_url: state.activeUrl,
    target_tab_id: state.activeTabId,
    model,
    max_steps: 80,
  }));
  log("start", "Started Flying Pig for the current tab.");
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
  $("openOura").addEventListener("click", openOura);
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
