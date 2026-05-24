import { spawn } from "node:child_process";
import { createWriteStream } from "node:fs";
import { mkdir } from "node:fs/promises";
import http from "node:http";
import net from "node:net";
import os from "node:os";
import path from "node:path";

export const DEFAULT_HOST = "127.0.0.1";
export const DEFAULT_START_PORT = 8765;
export const DEFAULT_CDP_PORT = 9222;

export function helperExecutableName(platform = process.platform) {
  return platform === "win32" ? "flyingpig-helper.exe" : "flyingpig-helper";
}

export function helperSidecarPath({
  resourcesPath = process.resourcesPath,
  platform = process.platform,
} = {}) {
  return path.join(resourcesPath, "helper", helperExecutableName(platform));
}

export function helperBaseUrl({ host = DEFAULT_HOST, port }) {
  return `http://${host}:${port}`;
}

export function buildHelperLaunchCommand({
  host = DEFAULT_HOST,
  port,
  cdpPort = DEFAULT_CDP_PORT,
  appPath = process.cwd(),
  resourcesPath = process.resourcesPath,
  isPackaged = false,
  helperPath = process.env.FLYINGPIG_HELPER_PATH,
  python = process.env.PYTHON || "python",
  verbose = false,
  platform = process.platform,
} = {}) {
  if (!port) {
    throw new Error("helper port is required");
  }

  const args = [
    "--no-dashboard",
    "--host",
    host,
    "--port",
    String(port),
    "--cdp-port",
    String(cdpPort),
  ];
  if (verbose) args.push("--verbose");

  if (helperPath) {
    return { command: helperPath, args, cwd: appPath, envPatch: {} };
  }

  if (isPackaged) {
    return {
      command: helperSidecarPath({ resourcesPath, platform }),
      args,
      cwd: path.dirname(helperSidecarPath({ resourcesPath, platform })),
      envPatch: {},
    };
  }

  return {
    command: python,
    args: ["-m", "src.helper", ...args],
    cwd: appPath,
    envPatch: { PYTHONPATH: appPath },
  };
}

export async function isPortAvailable(host, port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once("error", () => resolve(false));
    server.once("listening", () => {
      server.close(() => resolve(true));
    });
    server.listen(port, host);
  });
}

export async function findAvailablePort({
  host = DEFAULT_HOST,
  startPort = DEFAULT_START_PORT,
  maxAttempts = 50,
} = {}) {
  for (let offset = 0; offset < maxAttempts; offset += 1) {
    const port = startPort + offset;
    if (await isPortAvailable(host, port)) return port;
  }
  throw new Error(`No available helper port found from ${startPort}`);
}

export async function waitForHelperReady({
  baseUrl,
  timeoutMs = 30000,
  intervalMs = 250,
} = {}) {
  if (!baseUrl) throw new Error("baseUrl is required");
  const deadline = Date.now() + timeoutMs;
  let lastError;

  while (Date.now() < deadline) {
    try {
      const payload = await fetchJson(`${baseUrl}/health`);
      if (payload?.ok === true) return payload;
      lastError = new Error("health response did not include ok=true");
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }

  throw new Error(
    `Timed out waiting for Flying Pig helper at ${baseUrl}: ${lastError?.message || "unknown"}`,
  );
}

async function fetchJson(url) {
  return new Promise((resolve, reject) => {
    const request = http.get(url, (response) => {
      const chunks = [];
      response.on("data", (chunk) => chunks.push(chunk));
      response.on("end", () => {
        if (!response.statusCode || response.statusCode >= 500) {
          reject(new Error(`HTTP ${response.statusCode || "unknown"}`));
          return;
        }
        try {
          resolve(JSON.parse(Buffer.concat(chunks).toString("utf8")));
        } catch (error) {
          reject(error);
        }
      });
    });
    request.on("error", reject);
    request.setTimeout(1000, () => request.destroy(new Error("timeout")));
  });
}

export class HelperSupervisor {
  constructor({
    host = DEFAULT_HOST,
    startPort = Number(process.env.FLYINGPIG_DESKTOP_PORT || DEFAULT_START_PORT),
    cdpPort = Number(process.env.FLYINGPIG_CDP_PORT || DEFAULT_CDP_PORT),
    appPath = process.cwd(),
    resourcesPath = process.resourcesPath,
    isPackaged = false,
    logsDir = path.join(os.homedir(), ".flyingpig", "logs"),
    env = process.env,
    spawnFn = spawn,
    waitForReady = waitForHelperReady,
  } = {}) {
    this.host = host;
    this.startPort = startPort;
    this.cdpPort = cdpPort;
    this.appPath = appPath;
    this.resourcesPath = resourcesPath;
    this.isPackaged = isPackaged;
    this.logsDir = logsDir;
    this.env = env;
    this.spawnFn = spawnFn;
    this.waitForReady = waitForReady;
    this.child = null;
    this.port = null;
    this.baseUrl = null;
    this.logPath = path.join(logsDir, "desktop-helper.log");
    this.launch = null;
    this.lastError = null;
  }

  diagnostics() {
    return {
      baseUrl: this.baseUrl,
      command: this.launch?.command,
      args: this.launch?.args || [],
      logPath: this.logPath,
      port: this.port,
      running: Boolean(this.child && !this.child.killed),
      lastError: this.lastError?.message || null,
    };
  }

  async start() {
    if (this.child) return this.diagnostics();

    this.port = await findAvailablePort({
      host: this.host,
      startPort: this.startPort,
    });
    this.baseUrl = helperBaseUrl({ host: this.host, port: this.port });
    this.launch = buildHelperLaunchCommand({
      host: this.host,
      port: this.port,
      cdpPort: this.cdpPort,
      appPath: this.appPath,
      resourcesPath: this.resourcesPath,
      isPackaged: this.isPackaged,
      helperPath: this.env.FLYINGPIG_HELPER_PATH,
      python: this.env.PYTHON || "python",
      verbose: this.env.FLYINGPIG_HELPER_VERBOSE === "1",
    });

    await mkdir(this.logsDir, { recursive: true });
    const log = createWriteStream(this.logPath, { flags: "a" });
    log.write(`\n[desktop] starting helper at ${new Date().toISOString()}\n`);
    log.write(`[desktop] ${this.launch.command} ${this.launch.args.join(" ")}\n`);

    this.child = this.spawnFn(this.launch.command, this.launch.args, {
      cwd: this.launch.cwd,
      env: { ...this.env, ...this.launch.envPatch },
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
    });
    this.child.stdout?.pipe(log, { end: false });
    this.child.stderr?.pipe(log, { end: false });
    const spawnError = new Promise((_resolve, reject) => {
      this.child.once("error", (error) => {
        log.write(`[desktop] helper spawn failed: ${error.message}\n`);
        reject(error);
      });
    });
    spawnError.catch(() => {});
    this.child.once("exit", (code, signal) => {
      log.write(`[desktop] helper exited code=${code ?? ""} signal=${signal ?? ""}\n`);
      log.end();
      this.child = null;
    });

    try {
      await Promise.race([this.waitForReady({ baseUrl: this.baseUrl }), spawnError]);
      this.lastError = null;
      return this.diagnostics();
    } catch (error) {
      this.lastError = error;
      await this.stop({ forceAfterMs: 1500 });
      throw error;
    }
  }

  async stop({ forceAfterMs = 5000 } = {}) {
    const child = this.child;
    if (!child) return;

    await new Promise((resolve) => {
      let finished = false;
      const done = () => {
        if (finished) return;
        finished = true;
        resolve();
      };
      child.once("exit", done);
      child.kill("SIGTERM");
      setTimeout(() => {
        if (!finished) {
          child.kill("SIGKILL");
        }
        done();
      }, forceAfterMs);
    });
  }
}
