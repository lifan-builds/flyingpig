const $ = (id) => document.getElementById(id);

const state = {
  socket: null,
  connected: false,
  activeUrl: "",
  activeTabId: null,
  activeSite: "auto",
  running: false,
};

function formatTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function siteLabel(site) {
  if (site === "amex") return "American Express";
  if (site === "unknown" || !site) return "Unsupported tab";
  return site;
}

function log(kind, text) {
  const item = document.createElement("li");
  const title = document.createElement("strong");
  const body = document.createElement("span");
  title.textContent = kind;
  body.textContent = text;
  item.append(title, body);
  $("log").prepend(item);
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

  if (message.needs_input && message.message) {
    $("questionPanel").classList.remove("hidden");
    $("questionText").textContent = message.message;
  } else if (!message.needs_input) {
    $("questionPanel").classList.add("hidden");
  }
  updateButtons();
}

function updateButtons() {
  const hasTask = Boolean($("taskText").value.trim());
  $("startTask").disabled = !state.connected || state.running || !hasTask;
  $("cancelTask").disabled = !state.connected || !state.running;
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

async function openAmex() {
  await chrome.tabs.create({
    url: "https://www.americanexpress.com/us/customer-service/",
  });
}

async function loadSettings() {
  const saved = await chrome.storage.local.get(["cdpUrl", "taskText", "template", "model"]);
  $("cdpUrl").value = saved.cdpUrl || "http://127.0.0.1:9222";
  if (saved.taskText) $("taskText").value = saved.taskText;
  if (saved.template) $("template").value = saved.template;
  if (saved.model) $("model").value = saved.model;
}

function connectHelper() {
  if (state.socket?.readyState === WebSocket.OPEN) return;

  $("agentStatus").textContent = "connecting";
  const socket = new WebSocket("ws://127.0.0.1:8765/ws");
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
    $("runMessage").textContent = "Install or start the local Flying Pig helper to run browser-use.";
    log("helper", "Disconnected from local Flying Pig helper.");
  });

  socket.addEventListener("error", () => {
    state.running = false;
    setConnection(false);
    $("agentStatus").textContent = "error";
    $("runMessage").textContent = "Local helper is unavailable.";
    log("error", "Local helper is unavailable.");
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
    $("agentStatus").textContent = "needs_input";
    $("questionPanel").classList.remove("hidden");
    $("questionText").textContent = message.question || "The agent needs input.";
    log("input", message.question || "The agent needs input.");
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

async function startTask() {
  await refreshTab();
  const task = $("taskText").value.trim();
  if (!task) return;

  const cdpUrl = $("cdpUrl").value.trim() || "http://127.0.0.1:9222";
  const template = $("template").value;
  const model = $("model").value;
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
  log("answer", "Sent answer to agent.");
}

document.addEventListener("DOMContentLoaded", async () => {
  await loadSettings();
  await refreshTab();
  setConnection(false);

  $("refreshTab").addEventListener("click", refreshTab);
  $("openAccount").addEventListener("click", openAmex);
  $("taskText").addEventListener("input", updateButtons);
  $("startTask").addEventListener("click", startTask);
  $("cancelTask").addEventListener("click", cancelTask);
  $("sendAnswer").addEventListener("click", sendAnswer);
  $("clearLog").addEventListener("click", () => $("log").replaceChildren());

  connectHelper();
});
