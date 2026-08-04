import { app, BrowserWindow, Menu, ipcMain, shell } from "electron";
import updaterPackage from "electron-updater";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { configureAutoUpdates } from "./auto_update.js";
import { buildMetadata } from "./build_metadata.js";
import { HelperSupervisor } from "./helper_supervisor.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const { autoUpdater } = updaterPackage;

let mainWindow;
let helper;
let updates;
let quitting = false;
let latestStatus = {
  state: "starting",
  message: "Starting the Flying Pig helper.",
};
let latestUpdateStatus = {
  state: "idle",
  message: "Updates have not been checked yet.",
};

function appPath() {
  return app.isPackaged ? path.dirname(process.execPath) : path.resolve(__dirname, "..");
}

function iconPath() {
  return path.join(__dirname, "assets", "app-icon.png");
}

function createMenu() {
  const manualUpdateMode = updates?.mode === "download";
  const template = [
    {
      label: "Flying Pig",
      submenu: [
        { role: "about" },
        { type: "separator" },
        { label: "Check for Updates", click: () => checkForUpdates({ manual: true }) },
        {
          label: manualUpdateMode ? "Download Latest Version" : "Install Update and Relaunch",
          enabled: manualUpdateMode || Boolean(updates?.downloaded),
          click: () => (manualUpdateMode ? openUpdateDownloadPage() : installUpdateAndRelaunch()),
        },
        { type: "separator" },
        { label: "Retry Helper", click: () => retryHelper() },
        { label: "Open Logs Folder", click: () => openLogsFolder() },
        { type: "separator" },
        { role: "quit" },
      ],
    },
    {
      label: "Edit",
      submenu: [
        { role: "undo" },
        { role: "redo" },
        { type: "separator" },
        { role: "cut" },
        { role: "copy" },
        { role: "paste" },
        { role: "selectAll" },
      ],
    },
    {
      label: "View",
      submenu: [
        { role: "reload" },
        { role: "toggleDevTools" },
        { type: "separator" },
        { role: "resetZoom" },
        { role: "zoomIn" },
        { role: "zoomOut" },
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

function sendStatus(status) {
  latestStatus = { ...latestStatus, ...status };
  mainWindow?.webContents.send("helper:status", latestStatus);
}

function sendUpdateStatus(status) {
  latestUpdateStatus = { ...latestUpdateStatus, ...status };
  mainWindow?.webContents.send("updates:status", latestUpdateStatus);
}

async function showStatusScreen(status = {}) {
  await mainWindow.loadFile(path.join(__dirname, "status.html"));
  sendStatus(status);
}

async function startHelperAndLoadDashboard() {
  sendStatus({
    state: "starting",
    message: "Starting the local Flying Pig helper.",
    error: null,
  });

  helper = new HelperSupervisor({
    appPath: appPath(),
    resourcesPath: process.resourcesPath,
    isPackaged: app.isPackaged,
    logsDir: app.getPath("logs"),
    env: process.env,
    expectedBuild: {
      version: app.getVersion(),
      revision: buildMetadata.revision,
      builtAt: buildMetadata.builtAt,
      channel: buildMetadata.channel,
    },
    onDiagnostics: (diagnostics) => {
      const messages = {
        port_selection: "Selecting a local helper port.",
        spawn: "Launching the local helper.",
        health_wait: "Waiting for the local helper to become ready.",
        ready: "The local helper is ready.",
      };
      sendStatus({
        state: diagnostics.phase === "ready" ? "ready" : "starting",
        message: messages[diagnostics.phase] || "Starting the local Flying Pig helper.",
        diagnostics,
      });
    },
  });

  try {
    const diagnostics = await helper.start();
    sendStatus({
      state: "ready",
      message: diagnostics.buildMatch === "mismatch"
        ? "Helper is ready, but its build does not match this desktop package."
        : "Helper is ready. Loading the dashboard.",
      diagnostics,
    });
    const dashboardParams = new URLSearchParams({
      helperUrl: diagnostics.baseUrl,
      desktopBuildMatch: diagnostics.buildMatch,
    });
    await mainWindow.loadURL(`${diagnostics.baseUrl}/dashboard/?${dashboardParams}`);
  } catch (error) {
    sendStatus({
      state: "failed",
      message: "Flying Pig could not start the local helper.",
      error: error.message,
      diagnostics: helper.diagnostics(),
    });
  }
}

async function retryHelper() {
  if (!mainWindow) return;
  await helper?.stop({ forceAfterMs: 1500 });
  helper = null;
  await showStatusScreen({
    state: "starting",
    message: "Retrying the Flying Pig helper.",
    error: null,
  });
  await startHelperAndLoadDashboard();
}

async function openLogsFolder() {
  await shell.openPath(helper?.logsDir || app.getPath("logs"));
}

async function checkForUpdates(options = {}) {
  return updates?.checkForUpdates(options) || { ok: false, skipped: true };
}

async function installUpdateAndRelaunch() {
  if (!updates?.downloaded) {
    sendUpdateStatus({
      state: "waiting",
      message: "No downloaded update is ready to install.",
    });
    return false;
  }
  quitting = true;
  await helper?.stop();
  return updates.installUpdateAndRelaunch();
}

async function openUpdateDownloadPage() {
  return updates?.openDownloadPage() || false;
}

function configureUpdates() {
  updates = configureAutoUpdates({
    app,
    autoUpdater,
    shell,
    mode: process.env.FLYINGPIG_AUTO_INSTALL_UPDATES === "1" ? "install" : "download",
    onStatus: (status) => {
      sendUpdateStatus(status);
      createMenu();
    },
    onDownloaded: () => createMenu(),
  });
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 900,
    minWidth: 960,
    minHeight: 680,
    title: "Flying Pig",
    backgroundColor: "#0f1514",
    icon: iconPath(),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  await showStatusScreen(latestStatus);
  await startHelperAndLoadDashboard();
}

ipcMain.handle("helper:retry", retryHelper);
ipcMain.handle("helper:diagnostics", () => latestStatus);
ipcMain.handle("helper:openLogs", openLogsFolder);
ipcMain.handle("updates:check", () => checkForUpdates({ manual: true }));
ipcMain.handle("updates:status", () => latestUpdateStatus);
ipcMain.handle("updates:install", () =>
  updates?.mode === "download" ? openUpdateDownloadPage() : installUpdateAndRelaunch(),
);

app.whenReady().then(async () => {
  configureUpdates();
  createMenu();
  await createWindow();
  await checkForUpdates();
});

app.on("activate", async () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    await createWindow();
  }
});

app.on("window-all-closed", () => {
  app.quit();
});

app.on("before-quit", async (event) => {
  if (quitting) return;
  event.preventDefault();
  quitting = true;
  await helper?.stop();
  app.exit(0);
});
