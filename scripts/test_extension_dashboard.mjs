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
const extensionDir = path.join(rootDir, "extension");
const mockUrl = "http://127.0.0.1:8086/?logged_in=true";
const helperPort = process.env.FLYINGPIG_HELPER_PORT || "8766";
const helperUrl = `http://127.0.0.1:${helperPort}`;
const helperHealthUrl = `${helperUrl}/health`;
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

async function openDashboardPage(browser, extensionId) {
  const dashboardUrl = `chrome-extension://${extensionId}/src/dashboard.html`;
  const triggerAction = browser.triggerExtensionAction?.bind(browser);
  if (triggerAction) {
    const dashboardTarget = browser
      .waitForTarget((target) => target.url().startsWith(dashboardUrl), { timeout: 8000 })
      .catch(() => null);
    await triggerAction(extensionId);
    const target = await dashboardTarget;
    const page = target ? await target.page() : null;
    if (page) {
      await page.goto(
        `${dashboardUrl}?targetUrl=${encodeURIComponent(mockUrl)}&helperUrl=${encodeURIComponent(helperUrl)}`,
        { waitUntil: "domcontentloaded" },
      );
      return page;
    }
  }

  const page = await browser.newPage();
  const url = `${dashboardUrl}?targetUrl=${encodeURIComponent(mockUrl)}&helperUrl=${encodeURIComponent(helperUrl)}`;
  await page.goto(url, { waitUntil: "domcontentloaded" });
  return page;
}

async function verifyOfflineSetupState(browser, extensionId) {
  const page = await browser.newPage();
  const dashboardUrl = `chrome-extension://${extensionId}/src/dashboard.html`;
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
    (target) => target.url().includes("/src/setup.html"),
    { timeout: 10000 },
  );
  await page.close();
}

async function main() {
  const userDataDir = await mkdtemp(path.join(os.tmpdir(), "flyingpig-extension-e2e-"));
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
      "tests.support.extension_daemon:app",
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
      headless: false,
      userDataDir,
      pipe: true,
      enableExtensions: [extensionDir],
      args: ["--window-size=1280,900"],
    });

    const workerTarget = await browser.waitForTarget(
      (target) => target.type() === "service_worker" && target.url().includes("/src/background.js"),
      { timeout: 15000 },
    );
    const extensionId = new URL(workerTarget.url()).host;

    await verifyOfflineSetupState(browser, extensionId);

    const mockPage = await browser.newPage();
    await mockPage.goto(mockUrl, { waitUntil: "domcontentloaded" });
    await mockPage.bringToFront();

    const dashboardPage = await openDashboardPage(browser, extensionId);
    await dashboardPage.waitForFunction(
      () => document.getElementById("runtimeStatus")?.textContent === "Helper Online",
      { timeout: 10000 },
    );
    await dashboardPage.waitForFunction(
      () => document.getElementById("browserStatus")?.textContent === "Work Window Offline",
      { timeout: 10000 },
    );
    const startDisabledWithoutBrowser = await dashboardPage.$eval(
      "#startTask",
      (button) => button.disabled,
    );
    if (!startDisabledWithoutBrowser) {
      throw new Error("Start is enabled before the controlled work window is connected.");
    }
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

    await dashboardPage.click("#launchChrome");
    await dashboardPage.waitForFunction(
      () => document.body.textContent.includes("MOCK-CHROME-READY"),
      { timeout: 10000 },
    );
    await dashboardPage.waitForFunction(
      () => document.getElementById("browserStatus")?.textContent === "Work Window Connected",
      { timeout: 10000 },
    );

    await setValue(dashboardPage, "#cdpUrl", cdpUrlForDashboard);
    await setValue(
      dashboardPage,
      "#taskText",
      "Mock extension smoke test: verify the dashboard can start a browser-use helper run.",
    );
    await dashboardPage.click("#startTask");
    await dashboardPage.waitForFunction(
      () => document.body.textContent.includes("MOCK-RUN-OK"),
      { timeout: 10000 },
    );

    await setValue(dashboardPage, "#taskText", "Mock cancel smoke.");
    await dashboardPage.click("#startTask");
    await dashboardPage.waitForFunction(
      () => document.body.textContent.includes("MOCK-CANCEL-RUNNING"),
      { timeout: 10000 },
    );
    await dashboardPage.click("#cancelTask");
    await dashboardPage.waitForFunction(
      () => document.body.textContent.includes("MOCK-CANCELLED"),
      { timeout: 10000 },
    );

    await setValue(dashboardPage, "#taskText", "Mock checkpoint flow.");
    await dashboardPage.click("#startTask");
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

    console.log("Extension helper dashboard smoke passed.");
  } catch (error) {
    if (browser) {
      const pages = await browser.pages();
      const page = pages.at(-1);
      await page?.screenshot({ path: "/private/tmp/flyingpig-extension-dashboard-failure.png" });
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
