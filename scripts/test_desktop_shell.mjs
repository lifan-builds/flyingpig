#!/usr/bin/env node

import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { findAvailablePort, helperBaseUrl, waitForHelperReady } from "../desktop/helper_supervisor.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, "..");
const python = process.env.PYTHON || "python";

function startMockHelper(port) {
  const child = spawn(
    python,
    [
      "-m",
      "uvicorn",
      "tests.support.dashboard_daemon:app",
      "--host",
      "127.0.0.1",
      "--port",
      String(port),
      "--log-level",
      "error",
    ],
    {
      cwd: rootDir,
      env: { ...process.env, PYTHONPATH: rootDir },
      stdio: ["ignore", "pipe", "pipe"],
    },
  );
  child.stdout.on("data", (chunk) => process.stdout.write(`[desktop-mock-helper] ${chunk}`));
  child.stderr.on("data", (chunk) => process.stderr.write(`[desktop-mock-helper] ${chunk}`));
  return child;
}

function stopProcess(child) {
  if (!child || child.killed) return;
  child.kill("SIGTERM");
}

async function getText(url) {
  return new Promise((resolve, reject) => {
    const request = http.get(url, (response) => {
      const chunks = [];
      response.on("data", (chunk) => chunks.push(chunk));
      response.on("end", () => {
        if (!response.statusCode || response.statusCode >= 400) {
          reject(new Error(`HTTP ${response.statusCode || "unknown"}`));
          return;
        }
        resolve(Buffer.concat(chunks).toString("utf8"));
      });
    });
    request.on("error", reject);
    request.setTimeout(1000, () => request.destroy(new Error("timeout")));
  });
}

async function main() {
  const port = await findAvailablePort({ startPort: 8865 });
  const helper = startMockHelper(port);
  try {
    const baseUrl = helperBaseUrl({ port });
    await waitForHelperReady({ baseUrl, timeoutMs: 15000 });
    const dashboard = await getText(`${baseUrl}/dashboard/`);

    assert.match(dashboard, /Flying Pig Dashboard/);
    assert.match(dashboard, /Open Work Window/);
    console.log(`Desktop shell smoke reached helper dashboard at ${baseUrl}/dashboard/`);
  } finally {
    stopProcess(helper);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
