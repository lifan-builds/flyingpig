import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("flyingPigDesktop", {
  diagnostics: () => ipcRenderer.invoke("helper:diagnostics"),
  openLogs: () => ipcRenderer.invoke("helper:openLogs"),
  retryHelper: () => ipcRenderer.invoke("helper:retry"),
  onStatus: (callback) => {
    ipcRenderer.on("helper:status", (_event, status) => callback(status));
  },
});
