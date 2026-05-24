const DASHBOARD_PATH = "src/dashboard.html";

function dashboardUrlFor(tab) {
  const dashboardUrl = chrome.runtime.getURL(DASHBOARD_PATH);
  const sourceUrl = tab?.url || "";
  if (!sourceUrl || sourceUrl.startsWith("chrome-extension://") || sourceUrl.startsWith("chrome://")) {
    return dashboardUrl;
  }
  return `${dashboardUrl}?targetUrl=${encodeURIComponent(sourceUrl)}`;
}

async function openDashboard(tab) {
  const dashboardUrl = chrome.runtime.getURL(DASHBOARD_PATH);
  const tabs = await chrome.tabs.query({ url: `${dashboardUrl}*` });
  const existing = tabs[0];
  if (existing?.id) {
    await chrome.tabs.update(existing.id, { active: true });
    if (existing.windowId) {
      await chrome.windows.update(existing.windowId, { focused: true });
    }
    return;
  }

  await chrome.tabs.create({ url: dashboardUrlFor(tab) });
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({ dashboardPath: DASHBOARD_PATH });
});

chrome.action.onClicked.addListener(openDashboard);
