import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("flyingPigDesktop", {
  diagnostics: () => ipcRenderer.invoke("helper:diagnostics"),
  checkForUpdates: () => ipcRenderer.invoke("updates:check"),
  installUpdate: () => ipcRenderer.invoke("updates:install"),
  openLogs: () => ipcRenderer.invoke("helper:openLogs"),
  retryHelper: () => ipcRenderer.invoke("helper:retry"),
  updateStatus: () => ipcRenderer.invoke("updates:status"),
  onStatus: (callback) => {
    ipcRenderer.on("helper:status", (_event, status) => callback(status));
  },
  onUpdateStatus: (callback) => {
    ipcRenderer.on("updates:status", (_event, status) => callback(status));
  },
});
