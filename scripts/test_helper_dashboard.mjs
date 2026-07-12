#!/usr/bin/env node

import { spawn } from "node:child_process";
import { mkdtemp, rm } from "node:fs/promises";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

let puppeteer;
try {
  puppeteer = (await import("puppeteer")).default;
} catch {
  console.error("Puppeteer is not installed. Run `npm install` from the repo root first.");
  process.exit(1);
}

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, "..");
const mockUrl = "http://127.0.0.1:8086/?logged_in=true";
const helperPort = process.env.FLYINGPIG_HELPER_PORT || "8766";
const helperUrl = `http://127.0.0.1:${helperPort}`;
const helperHealthUrl = `${helperUrl}/health`;
const dashboardUrl = `${helperUrl}/dashboard/`;
const cdpUrlForDashboard = process.env.FLYINGPIG_CDP_URL || "http://127.0.0.1:9335";

const python = process.env.PYTHON || "python";
const env = { ...process.env, PYTHONPATH: rootDir };

function startServer(args, name) {
  const child = spawn(python, args, {
    cwd: rootDir,
    env,
    stdio: ["ignore", "pipe", "pipe"],
  });
  child.stdout.on("data", (chunk) => process.stdout.write(`[${name}] ${chunk}`));
  child.stderr.on("data", (chunk) => process.stderr.write(`[${name}] ${chunk}`));
  return child;
}

function stopProcess(child) {
  if (!child || child.killed) return;
  child.kill("SIGTERM");
}

async function waitForHttp(url, timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs;
  let lastError;
  while (Date.now() < deadline) {
    try {
      await new Promise((resolve, reject) => {
        const request = http.get(url, (response) => {
          response.resume();
          response.statusCode && response.statusCode < 500
            ? resolve()
            : reject(new Error(`HTTP ${response.statusCode}`));
        });
        request.on("error", reject);
        request.setTimeout(1000, () => request.destroy(new Error("timeout")));
      });
      return;
    } catch (error) {
      lastError = error;
      await new Promise((resolve) => setTimeout(resolve, 250));
    }
  }
  throw new Error(`Timed out waiting for ${url}: ${lastError?.message || "unknown"}`);
}

async function setValue(page, selector, value) {
  await page.$eval(
    selector,
    (element, nextValue) => {
      element.value = nextValue;
      element.dispatchEvent(new Event("input", { bubbles: true }));
      element.dispatchEvent(new Event("change", { bubbles: true }));
    },
    value,
  );
}

async function clickElement(page, selector) {
  await page.$eval(selector, (element) => {
    if (element.disabled) throw new Error(`Element is disabled: ${element.id || element.tagName}`);
    element.click();
  });
}

async function openDashboardPage(browser) {
  const page = await browser.newPage();
  const url = `${dashboardUrl}?targetUrl=${encodeURIComponent(mockUrl)}&helperUrl=${encodeURIComponent(helperUrl)}`;
  await page.goto(url, { waitUntil: "domcontentloaded" });
  return page;
}

async function verifyOfflineSetupState(browser) {
  const page = await browser.newPage();
  const deadHelperUrl = "http://127.0.0.1:65530";
  await page.goto(
    `${dashboardUrl}?targetUrl=${encodeURIComponent(mockUrl)}&helperUrl=${encodeURIComponent(deadHelperUrl)}`,
    { waitUntil: "domcontentloaded" },
  );
  await page.waitForFunction(
    () => document.getElementById("helperSetupPanel")
      && !document.getElementById("helperSetupPanel").classList.contains("hidden"),
    { timeout: 10000 },
  );
  await page.waitForFunction(
    (expected) => document.getElementById("setupDiagnostic")?.textContent.includes(expected),
    { timeout: 10000 },
    deadHelperUrl,
  );
  await page.click("#setupHelper");
  await browser.waitForTarget(
    (target) => target.url().includes("/dashboard/setup.html"),
    { timeout: 10000 },
  );
  await page.close();
}

async function main() {
  const userDataDir = await mkdtemp(path.join(os.tmpdir(), "flyingpig-dashboard-e2e-"));
  const benchmark = {};
  const startedAt = performance.now();
  const mockServer = startServer(
    [
      "-m",
      "uvicorn",
      "tests.mock_amex.server:app",
      "--host",
      "127.0.0.1",
      "--port",
      "8086",
      "--log-level",
      "error",
    ],
    "mock-amex",
  );
  const helper = startServer(
    [
      "-m",
      "uvicorn",
      "tests.support.dashboard_daemon:app",
      "--host",
      "127.0.0.1",
      "--port",
      helperPort,
      "--log-level",
      "error",
    ],
    "mock-helper",
  );

  let browser;
  try {
    await waitForHttp(mockUrl);
    await waitForHttp(helperHealthUrl);

    browser = await puppeteer.launch({
      headless: true,
      userDataDir,
      pipe: true,
      args: ["--window-size=1280,900"],
    });

    await verifyOfflineSetupState(browser);

    const mockPage = await browser.newPage();
    await mockPage.goto(mockUrl, { waitUntil: "domcontentloaded" });
    await mockPage.bringToFront();

    const dashboardPage = await openDashboardPage(browser);
    await dashboardPage.waitForFunction(
      () => document.getElementById("runtimeStatus")?.textContent === "Helper Online",
      { timeout: 10000 },
    );
    benchmark.helperOnlineMs = Math.round(performance.now() - startedAt);
    await dashboardPage.waitForFunction(
      () => document.getElementById("browserStatus")?.textContent === "Work Window Offline",
      { timeout: 10000 },
    );
    await dashboardPage.waitForFunction(
      () => document.getElementById("modelKeyStatus")?.textContent.includes("key is configured"),
      { timeout: 10000 },
    );
    const modelSetupPlacement = await dashboardPage.$eval("#model", (select) => ({
      inAdvanced: select.closest("details")?.classList.contains("advanced") || false,
      readyModel: document.getElementById("readyModel")?.textContent || "",
      quickstartText: document.getElementById("quickstartList")?.textContent || "",
      setupHidden: document.getElementById("firstRunPanel")?.classList.contains("hidden") || false,
    }));
    if (
      modelSetupPlacement.inAdvanced
      || modelSetupPlacement.readyModel !== "Configured"
      || !modelSetupPlacement.quickstartText.includes("Configure the model")
      || !modelSetupPlacement.quickstartText.includes("Open the work window")
      || !modelSetupPlacement.setupHidden
    ) {
      throw new Error(`Configured model setup did not collapse for repeat use: ${JSON.stringify(modelSetupPlacement)}`);
    }
    const firstUseGuide = await dashboardPage.$eval("#firstUseGuide", (guide) => ({
      visible: !guide.classList.contains("hidden"),
      text: guide.textContent || "",
      configuredReady: guide.querySelector('[data-guide-step="configure"]')?.dataset.ready || "",
    }));
    if (
      !firstUseGuide.visible
      || !firstUseGuide.text.includes("Configure")
      || !firstUseGuide.text.includes("Open the website")
      || !firstUseGuide.text.includes("Start")
      || firstUseGuide.configuredReady !== "true"
    ) {
      throw new Error(`First-use guide is incomplete: ${JSON.stringify(firstUseGuide)}`);
    }
    await clickElement(dashboardPage, "#modelSettingsToggle");
    await dashboardPage.waitForFunction(
      () => !document.getElementById("firstRunPanel")?.classList.contains("hidden"),
      { timeout: 10000 },
    );
    const modelKeyField = await dashboardPage.$eval("#modelApiKey", (input) => ({
      type: input.type,
      value: input.value,
      autocomplete: input.getAttribute("autocomplete"),
    }));
    if (
      modelKeyField.type !== "password"
      || modelKeyField.value !== ""
      || modelKeyField.autocomplete !== "off"
    ) {
      throw new Error(`Model key field is not safe by default: ${JSON.stringify(modelKeyField)}`);
    }
    await setValue(dashboardPage, "#model", "claude");
    await dashboardPage.waitForFunction(
      () => document.getElementById("modelKeyStatus")?.textContent.includes("not configured"),
      { timeout: 10000 },
    );
    const startReasonWithoutModel = await dashboardPage.$eval(
      "#startDisabledReason",
      (element) => element.textContent,
    );
    if (!startReasonWithoutModel.includes("Configure the selected model")) {
      throw new Error(`Start-disabled reason does not block unconfigured models: ${startReasonWithoutModel}`);
    }
    await setValue(dashboardPage, "#modelApiKey", "sk-ant-test-dashboard");
    await clickElement(dashboardPage, "#saveModelSettings");
    await dashboardPage.waitForFunction(
      () => document.getElementById("modelKeyStatus")?.textContent.includes("key is configured")
        && document.getElementById("modelApiKey")?.value === "",
      { timeout: 10000 },
    );
    await clickElement(dashboardPage, "#modelSettingsToggle");
    await dashboardPage.waitForFunction(
      () => !document.getElementById("firstRunPanel")?.classList.contains("hidden"),
      { timeout: 10000 },
    );
    await clickElement(dashboardPage, "#clearModelKey");
    await dashboardPage.waitForFunction(
      () => document.getElementById("modelKeyStatus")?.textContent.includes("not configured"),
      { timeout: 10000 },
    );
    await setValue(dashboardPage, "#model", "cliproxyapi");
    const startDisabledWithoutBrowser = await dashboardPage.$eval(
      "#startTask",
      (button) => button.disabled,
    );
    if (startDisabledWithoutBrowser) {
      throw new Error("Start should own work-window preparation after model setup.");
    }
    const startReason = await dashboardPage.$eval(
      "#startDisabledReason",
      (element) => element.textContent,
    );
    if (startReason) {
      throw new Error(`Ready state should not add redundant guidance: ${startReason}`);
    }
    const readinessBeforeLaunch = await dashboardPage.$$eval(
      ".readiness-item",
      (items) => items.map((item) => `${item.textContent}:${item.dataset.ready}`),
    );
    if (!readinessBeforeLaunch.some((item) => item.includes("Work Window") && item.endsWith("false"))) {
      throw new Error(`Readiness did not show missing work window: ${readinessBeforeLaunch.join(" | ")}`);
    }
    await dashboardPage.setViewport({ width: 390, height: 860, deviceScaleFactor: 1 });
    const narrowLayout = await dashboardPage.evaluate(() => ({
      overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      readinessColumns: getComputedStyle(document.querySelector(".readiness-strip"))
        .gridTemplateColumns
        .split(" ").length,
    }));
    if (narrowLayout.overflowX || narrowLayout.readinessColumns > 2) {
      throw new Error(`Narrow dashboard layout overflowed: ${JSON.stringify(narrowLayout)}`);
    }
    await dashboardPage.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });
    const statusLaunchHidden = await dashboardPage.$eval(
      "#statusLaunchChrome",
      (button) => getComputedStyle(button.closest(".status-row")).display === "none",
    );
    if (!statusLaunchHidden) {
      throw new Error("Configured users should not see a separate work-window launch control.");
    }
    const attachChromeVisible = await dashboardPage.$eval(
      "#attachChrome",
      (button) => button.textContent.includes("Connect Existing Chrome") && !button.disabled,
    );
    if (!attachChromeVisible) {
      throw new Error("Dashboard does not expose an enabled existing-Chrome connection button.");
    }
    const briefStarterOptions = await dashboardPage.$$eval(
      "#briefStarter option",
      (options) => options.map((option) => option.textContent),
    );
    for (const expected of [
      "Custom brief",
      "Lower bill or retention offer",
      "Refund or courtesy credit",
      "Escalate to human",
      "Continue existing chat",
    ]) {
      if (!briefStarterOptions.includes(expected)) {
        throw new Error(`Missing brief starter ${expected}: ${briefStarterOptions.join(", ")}`);
      }
    }
    if (briefStarterOptions.length < 7) {
      throw new Error(`Unexpected brief starter options: ${briefStarterOptions.join(", ")}`);
    }
    await dashboardPage.$eval(".advanced", (details) => {
      details.open = true;
    });
    const agentApproach = await dashboardPage.$eval("#template", (select) => ({
      label: document.querySelector('label[for="template"]')?.textContent || "",
      value: select.value,
      firstOption: select.options[0]?.textContent || "",
      inAdvanced: select.closest("details")?.classList.contains("advanced") || false,
      bodyText: document.body.textContent || "",
    }));
    if (
      agentApproach.label !== "Agent approach"
      || agentApproach.value !== ""
      || agentApproach.firstOption !== "Automatic (agent decides)"
      || !agentApproach.inAdvanced
      || agentApproach.bodyText.includes("Playbook")
    ) {
      throw new Error(`Unexpected agent approach UI: ${JSON.stringify(agentApproach)}`);
    }
    await dashboardPage.evaluate(() => {
      localStorage.setItem("flyingpig.template", JSON.stringify("retention_offer"));
      localStorage.removeItem("flyingpig.templateManual");
    });
    await dashboardPage.reload({ waitUntil: "domcontentloaded" });
    await dashboardPage.waitForFunction(
      () => document.getElementById("runtimeStatus")?.textContent === "Helper Online",
      { timeout: 10000 },
    );
    const migratedTemplate = await dashboardPage.$eval("#template", (select) => select.value);
    if (migratedTemplate !== "") {
      throw new Error(`Legacy saved template should migrate to automatic, got ${migratedTemplate}.`);
    }
    await setValue(dashboardPage, "#briefStarter", "retention_offer");
    const templateAfterStarter = await dashboardPage.$eval("#template", (select) => select.value);
    if (templateAfterStarter !== "") {
      throw new Error(`Brief starter should leave agent approach automatic, got ${templateAfterStarter}.`);
    }
    await setValue(dashboardPage, "#template", "negotiate_fee");
    await setValue(dashboardPage, "#briefStarter", "dispute_charge");
    const templateAfterManualChoice = await dashboardPage.$eval("#template", (select) => select.value);
    if (templateAfterManualChoice !== "negotiate_fee") {
      throw new Error(`Brief starter overwrote manual agent approach: ${templateAfterManualChoice}.`);
    }
    await setValue(dashboardPage, "#template", "");
    if (await dashboardPage.$("#openOura")) {
      throw new Error("Dashboard still renders the dedicated Oura button.");
    }
    if (await dashboardPage.$("#openSupportPage")) {
      throw new Error("Dashboard still opens support pages in normal Chrome.");
    }
    await dashboardPage.waitForFunction(
      () => Array.from(document.querySelectorAll("#sitePicker option"))
        .some((option) => option.textContent === "Oura Ring"),
      { timeout: 10000 },
    );
    const defaultChromeProfile = await dashboardPage.$eval("#chromeProfile", (select) => select.value);
    if (defaultChromeProfile !== "dedicated") {
      throw new Error(`Expected dedicated profile by default, got ${defaultChromeProfile}.`);
    }
    const hasDefaultProfileOption = await dashboardPage.$eval(
      "#chromeProfile",
      (select) => Array.from(select.options).some((option) => option.value === "default"),
    );
    if (!hasDefaultProfileOption) {
      throw new Error("Dashboard does not expose the copied default profile option.");
    }
    const hasUserDefaultProfileOption = await dashboardPage.$eval(
      "#chromeProfile",
      (select) => Array.from(select.options).some((option) => option.value === "existing"),
    );
    if (!hasUserDefaultProfileOption) {
      throw new Error("Dashboard does not expose the user default profile option.");
    }

    await clickElement(dashboardPage, "#startTask");
    await dashboardPage.waitForFunction(
      () => !document.getElementById("preparationPanel")?.classList.contains("hidden"),
      { timeout: 10000 },
    );
    await dashboardPage.waitForFunction(
      () => document.body.textContent.includes("MOCK-CHROME-READY"),
      { timeout: 10000 },
    );
    await clickElement(dashboardPage, "#backToTask");
    await dashboardPage.waitForFunction(
      () => document.getElementById("browserStatus")?.textContent === "Work Window Connected",
      { timeout: 10000 },
    );
    benchmark.workWindowReadyMs = Math.round(performance.now() - startedAt);
    await dashboardPage.waitForFunction(
      () => document.body.textContent.includes("Work window launch"),
      { timeout: 10000 },
    );
    const readinessAfterLaunch = await dashboardPage.$$eval(
      ".readiness-item",
      (items) => items.map((item) => `${item.textContent}:${item.dataset.ready}`),
    );
    if (!readinessAfterLaunch.some((item) => item.includes("Work Window") && item.endsWith("true"))) {
      throw new Error(`Readiness did not update after work-window connection: ${readinessAfterLaunch.join(" | ")}`);
    }

    await setValue(dashboardPage, "#cdpUrl", cdpUrlForDashboard);
    await dashboardPage.$eval(".run-options", (details) => { details.open = true; });
    await clickElement(dashboardPage, "#attachChrome");
    await dashboardPage.waitForFunction(
      () => document.body.textContent.includes("MOCK-EXISTING-CHROME-READY"),
      { timeout: 10000 },
    );
    const attachedEndpoint = await dashboardPage.$eval("#cdpUrl", (input) => input.value);
    if (attachedEndpoint !== cdpUrlForDashboard) {
      throw new Error(`Existing-Chrome attach did not preserve endpoint: ${attachedEndpoint}`);
    }

    await clickElement(dashboardPage, "#autoConnectChrome");
    await dashboardPage.waitForFunction(
      () => document.body.textContent.includes("MOCK-MCP-CONNECTED"),
      { timeout: 10000 },
    );
    const mcpPages = await dashboardPage.$$(".mcp-page");
    if (mcpPages.length < 2) {
      throw new Error(`Expected at least two mock MCP pages, got ${mcpPages.length}`);
    }
    await mcpPages[1].click();
    await dashboardPage.waitForFunction(
      () => document.body.textContent.includes("MOCK-MCP-NATIVE-READY"),
      { timeout: 10000 },
    );
    const mcpTabReady = await dashboardPage.$eval(
      "#browserStatus",
      (element) => element.textContent === "Work Window Connected",
    );
    if (!mcpTabReady) {
      throw new Error("MCP-selected Chrome tab did not mark the work window connected.");
    }

    await setValue(
      dashboardPage,
      "#taskText",
      "Mock helper dashboard smoke test: verify the dashboard can start a browser-use helper run.",
    );
    await setValue(dashboardPage, "#authorizationTarget", "12345");
    await clickElement(dashboardPage, "#authorizeClosure");
    await clickElement(dashboardPage, "#authorizeRefund");
    await clickElement(dashboardPage, "#refundChecking");
    await clickElement(dashboardPage, "#refundCheck");
    await clickElement(dashboardPage, "#authorizeHuca");
    await setValue(dashboardPage, "#declinedAlternatives", "retention offers, product changes");
    await clickElement(dashboardPage, "#startTask");
    await dashboardPage.waitForFunction(
      () => document.body.textContent.includes("MOCK-RUN-OK"),
      { timeout: 10000 },
    );
    const guideHiddenAfterStart = await dashboardPage.$eval(
      "#firstUseGuide",
      (guide) => guide.classList.contains("hidden"),
    );
    if (!guideHiddenAfterStart) {
      throw new Error("First-use guide should disappear after the first run starts.");
    }
    const activationSignals = await dashboardPage.evaluate(() => {
      const raw = localStorage.getItem("flyingpig.activationSignals");
      return raw ? JSON.parse(raw) : {};
    });
    for (const expected of [
      "model_configured",
      "work_window_opened",
      "chat_surface_selected",
      "task_brief_written",
      "first_run_started",
    ]) {
      if (!activationSignals[expected]) {
        throw new Error(`Missing local activation signal ${expected}: ${JSON.stringify(activationSignals)}`);
      }
    }
    benchmark.mockRunDoneMs = Math.round(performance.now() - startedAt);
    await dashboardPage.waitForFunction(
      () => document.body.textContent.includes("Model planning step")
        && document.body.textContent.includes("Timing")
        && document.getElementById("completionChecklist")?.textContent.includes("Complete: close card")
        && document.getElementById("followUpActions")?.textContent.includes("contact support after credit posts")
        && document.getElementById("resultDetails")?.textContent.includes("Confirmation expected")
        && document.getElementById("resultDetails")?.textContent.includes("Yes"),
      { timeout: 10000 },
    );
    await clickElement(dashboardPage, "#followUpActions .follow-up-controls button");
    await dashboardPage.waitForFunction(
      () => document.getElementById("followUpActions")?.textContent.includes("Scheduled for"),
      { timeout: 10000 },
    );
    await clickElement(dashboardPage, "#markSolved");
    await dashboardPage.waitForFunction(
      () => document.getElementById("outcomeStatus")?.textContent.includes("Marked Solved")
        && document.getElementById("betaStats")?.textContent.includes("Marked runs")
        && document.getElementById("betaStats")?.textContent.includes("1"),
      { timeout: 10000 },
    );

    await setValue(dashboardPage, "#taskText", "Mock HUCA smoke.");
    await clickElement(dashboardPage, "#hucaTask");
    await dashboardPage.waitForFunction(
      () => document.body.textContent.includes("MOCK-HUCA-OK"),
      { timeout: 10000 },
    );

    await setValue(dashboardPage, "#taskText", "Mock cancel smoke.");
    await clickElement(dashboardPage, "#startTask");
    await dashboardPage.waitForFunction(
      () => document.body.textContent.includes("MOCK-CANCEL-RUNNING"),
      { timeout: 10000 },
    );
    await clickElement(dashboardPage, "#cancelTask");
    await dashboardPage.waitForFunction(
      () => document.body.textContent.includes("MOCK-CANCELLED"),
      { timeout: 10000 },
    );

    await setValue(dashboardPage, "#taskText", "Mock checkpoint flow.");
    await clickElement(dashboardPage, "#startTask");
    await dashboardPage.waitForFunction(
      () => document.body.textContent.includes("No retention offer is available."),
      { timeout: 10000 },
    );
    await dashboardPage.reload({ waitUntil: "domcontentloaded" });
    await dashboardPage.waitForFunction(
      () => document.getElementById("runtimeStatus")?.textContent === "Helper Online",
      { timeout: 10000 },
    );
    await dashboardPage.waitForFunction(
      () => document.body.textContent.includes("No retention offer is available."),
      { timeout: 10000 },
    );
    await dashboardPage.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll(".checkpoint-option"));
      const closeCard = buttons.find((button) => button.textContent.includes("Close card"));
      if (!closeCard) throw new Error("Close card checkpoint option was not rendered.");
      closeCard.click();
    });
    await dashboardPage.waitForFunction(
      () => document.body.textContent.includes("MOCK-CHECKPOINT-OK"),
      { timeout: 10000 },
    );

    console.log(
      `Dashboard benchmark: helper_online=${benchmark.helperOnlineMs}ms `
      + `work_window_ready=${benchmark.workWindowReadyMs}ms `
      + `mock_run_done=${benchmark.mockRunDoneMs}ms`,
    );
    console.log("Helper dashboard smoke passed.");
  } catch (error) {
    if (browser) {
      const pages = await browser.pages();
      const page = pages.at(-1);
      await page?.screenshot({ path: "/private/tmp/flyingpig-helper-dashboard-failure.png" });
    }
    throw error;
  } finally {
    await browser?.close();
    stopProcess(mockServer);
    stopProcess(helper);
    await rm(userDataDir, { force: true, recursive: true });
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
