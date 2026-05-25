export function configureAutoUpdates({
  app,
  autoUpdater,
  logger = console,
  onStatus = () => {},
  onDownloaded = () => {},
} = {}) {
  let downloaded = false;

  function emit(state, message, extra = {}) {
    onStatus({ state, message, ...extra });
  }

  if (!app || !autoUpdater) {
    emit("unavailable", "Auto-update is not available in this build.");
    return {
      get downloaded() {
        return downloaded;
      },
      checkForUpdates: async () => ({ ok: false, skipped: true }),
      installUpdateAndRelaunch: () => false,
    };
  }

  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = false;
  autoUpdater.logger = logger;

  autoUpdater.on("checking-for-update", () => {
    emit("checking", "Checking for updates.");
  });
  autoUpdater.on("update-available", (info) => {
    emit("available", "Update available. Downloading in the background.", { info });
  });
  autoUpdater.on("update-not-available", (info) => {
    emit("current", "Flying Pig is up to date.", { info });
  });
  autoUpdater.on("download-progress", (progress) => {
    emit("downloading", "Downloading update.", {
      percent: Math.round(progress.percent || 0),
    });
  });
  autoUpdater.on("update-downloaded", (info) => {
    downloaded = true;
    emit("downloaded", "Update downloaded. Relaunch to install.", { info });
    onDownloaded(info);
  });
  autoUpdater.on("error", (error) => {
    emit("error", "Could not check for updates.", { error: error.message });
  });

  return {
    get downloaded() {
      return downloaded;
    },
    async checkForUpdates({ manual = false } = {}) {
      if (!app.isPackaged) {
        const message = "Update checks run only in the packaged desktop app.";
        emit("skipped", message);
        return { ok: true, skipped: true, message };
      }
      try {
        const result = await autoUpdater.checkForUpdatesAndNotify();
        return { ok: true, result };
      } catch (error) {
        if (manual) {
          emit("error", "Could not check for updates.", { error: error.message });
        }
        return { ok: false, error };
      }
    },
    installUpdateAndRelaunch() {
      if (!downloaded) {
        emit("waiting", "No downloaded update is ready to install.");
        return false;
      }
      autoUpdater.quitAndInstall(false, true);
      return true;
    },
  };
}
