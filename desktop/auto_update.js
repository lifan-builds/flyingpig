export function configureAutoUpdates({
  app,
  autoUpdater,
  shell,
  logger = console,
  onStatus = () => {},
  onDownloaded = () => {},
  fetchImpl = globalThis.fetch,
  mode = "download",
  releasesApiUrl = "https://api.github.com/repos/lifan-builds/flyingpig/releases/latest",
  releasesPageUrl = "https://github.com/lifan-builds/flyingpig/releases/latest",
} = {}) {
  let downloaded = false;
  let availableRelease = null;

  function emit(state, message, extra = {}) {
    onStatus({ state, message, ...extra });
  }

  function currentVersion() {
    return app?.getVersion?.() || app?.version || "0.0.0";
  }

  function releaseVersion(release = {}) {
    return String(release.tag_name || release.name || "").replace(/^v/i, "");
  }

  function parseVersion(version) {
    return String(version)
      .replace(/^v/i, "")
      .split(/[.-]/)
      .map((part) => Number.parseInt(part, 10))
      .map((part) => (Number.isFinite(part) ? part : 0));
  }

  function isNewerVersion(candidate, current) {
    const left = parseVersion(candidate);
    const right = parseVersion(current);
    const length = Math.max(left.length, right.length);
    for (let index = 0; index < length; index += 1) {
      const candidatePart = left[index] || 0;
      const currentPart = right[index] || 0;
      if (candidatePart > currentPart) return true;
      if (candidatePart < currentPart) return false;
    }
    return false;
  }

  async function checkDownloadRelease({ manual = false } = {}) {
    if (!app?.isPackaged) {
      const message = "Update checks run only in the packaged desktop app.";
      emit("skipped", message);
      return { ok: true, skipped: true, message };
    }
    if (!fetchImpl) {
      const message = "Update checks need a runtime with fetch support.";
      emit(manual ? "error" : "skipped", message);
      return { ok: false, skipped: !manual, message };
    }
    try {
      emit("checking", "Checking for updates.");
      const response = await fetchImpl(releasesApiUrl, {
        headers: {
          Accept: "application/vnd.github+json",
          "User-Agent": "FlyingPigDesktop",
        },
      });
      if (!response.ok) {
        throw new Error(`GitHub release check failed with HTTP ${response.status}`);
      }
      const release = await response.json();
      const latestVersion = releaseVersion(release);
      const releasePage = release.html_url || releasesPageUrl;
      if (latestVersion && isNewerVersion(latestVersion, currentVersion())) {
        availableRelease = { ...release, html_url: releasePage, version: latestVersion };
        emit("available", "Update available. Download the latest GitHub release to install it.", {
          info: availableRelease,
          url: releasePage,
        });
        return { ok: true, updateInfo: availableRelease };
      }
      availableRelease = null;
      emit("current", "Flying Pig is up to date.", {
        info: { ...release, html_url: releasePage, version: latestVersion },
      });
      return { ok: true, updateInfo: null };
    } catch (error) {
      if (manual) {
        emit("error", "Could not check for updates.", { error: error.message });
      }
      return { ok: false, error };
    }
  }

  if (!app || (mode === "install" && !autoUpdater)) {
    emit("unavailable", "Auto-update is not available in this build.");
    return {
      mode,
      get downloaded() {
        return downloaded;
      },
      get hasAvailableUpdate() {
        return Boolean(availableRelease);
      },
      checkForUpdates: async () => ({ ok: false, skipped: true }),
      installUpdateAndRelaunch: () => false,
      openDownloadPage: async () => false,
    };
  }

  if (mode === "download") {
    return {
      mode,
      get downloaded() {
        return downloaded;
      },
      get hasAvailableUpdate() {
        return Boolean(availableRelease);
      },
      async checkForUpdates(options = {}) {
        return checkDownloadRelease(options);
      },
      installUpdateAndRelaunch() {
        emit("manual", "Unsigned beta updates are installed manually from GitHub Releases.");
        return false;
      },
      async openDownloadPage() {
        const url = availableRelease?.html_url || releasesPageUrl;
        await shell?.openExternal?.(url);
        emit("manual", "Opened the latest GitHub release in your browser.", { url });
        return true;
      },
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
    mode,
    get downloaded() {
      return downloaded;
    },
    get hasAvailableUpdate() {
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
    async openDownloadPage() {
      await shell?.openExternal?.(releasesPageUrl);
      return true;
    },
  };
}
