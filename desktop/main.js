import { app, BrowserWindow, Menu, ipcMain, shell } from "electron";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { HelperSupervisor } from "./helper_supervisor.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

let mainWindow;
let helper;
let quitting = false;
let latestStatus = {
  state: "starting",
  message: "Starting the Flying Pig helper.",
};

function appPath() {
  return app.isPackaged ? path.dirname(process.execPath) : path.resolve(__dirname, "..");
}

function iconPath() {
  return path.join(__dirname, "assets", "app-icon.png");
}

function createMenu() {
  const template = [
    {
      label: "Flying Pig",
      submenu: [
        { role: "about" },
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
  });

  try {
    const diagnostics = await helper.start();
    sendStatus({
      state: "ready",
      message: "Helper is ready. Loading the dashboard.",
      diagnostics,
    });
    await mainWindow.loadURL(
      `${diagnostics.baseUrl}/dashboard/?helperUrl=${encodeURIComponent(diagnostics.baseUrl)}`,
    );
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
  const logPath = helper?.diagnostics().logPath || app.getPath("logs");
  await shell.openPath(path.dirname(logPath));
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

app.whenReady().then(async () => {
  createMenu();
  await createWindow();
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
