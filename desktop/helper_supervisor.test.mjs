import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { mkdtempSync } from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { PassThrough } from "node:stream";
import { test } from "node:test";

import {
  buildHelperLaunchCommand,
  compareBuildIdentity,
  findAvailablePort,
  helperBaseUrl,
  helperExecutableName,
  HelperSupervisor,
  waitForHelperReady,
} from "./helper_supervisor.js";

test("compares packaged desktop and helper build identities", () => {
  assert.equal(
    compareBuildIdentity({ version: "1.0.2" }, { version: "1.0.2", channel: "development" }),
    "match",
  );
  assert.equal(
    compareBuildIdentity({ version: "1.0.2" }, { version: "1.0.1" }),
    "mismatch",
  );
  assert.equal(
    compareBuildIdentity(
      { version: "1.0.2", revision: "abc123" },
      { version: "1.0.2", revision: "def456" },
    ),
    "mismatch",
  );
  assert.equal(
    compareBuildIdentity(
      { version: "1.0.2", revision: "abc123", builtAt: "2026-01-01T00:00:00.000Z" },
      { version: "1.0.2", revision: null, built_at: null, channel: "development" },
    ),
    "mismatch",
  );
  assert.equal(compareBuildIdentity({ version: "1.0.2" }, null), "unknown");
});

test("builds development helper launch command", () => {
  const launch = buildHelperLaunchCommand({
    appPath: "/repo/flyingpig",
    host: "127.0.0.1",
    port: 8877,
    cdpPort: 9444,
    python: "python3",
    isPackaged: false,
  });

  assert.equal(launch.command, "python3");
  assert.equal(launch.cwd, "/repo/flyingpig");
  assert.deepEqual(launch.args, [
    "-m",
    "src.helper",
    "--no-dashboard",
    "--host",
    "127.0.0.1",
    "--port",
    "8877",
    "--cdp-port",
    "9444",
  ]);
  assert.equal(launch.envPatch.PYTHONPATH, "/repo/flyingpig");
});

test("builds packaged sidecar launch command", () => {
  const launch = buildHelperLaunchCommand({
    resourcesPath: "/Applications/Flying Pig.app/Contents/Resources",
    host: "127.0.0.1",
    port: 8878,
    isPackaged: true,
    platform: "darwin",
  });

  assert.equal(launch.command.endsWith("/helper/flyingpig-helper"), true);
  assert.equal(launch.args.includes("--no-dashboard"), true);
  assert.equal(helperExecutableName("win32"), "flyingpig-helper.exe");
});

test("chooses a free helper port after an occupied one", async () => {
  const occupied = await listenWithHealth();
  try {
    const port = await findAvailablePort({
      host: "127.0.0.1",
      startPort: occupied.port,
      maxAttempts: 3,
    });

    assert.equal(port, occupied.port + 1);
  } finally {
    await occupied.close();
  }
});

test("waits for helper health readiness", async () => {
  let calls = 0;
  const server = await listenWithHealth((_request, response) => {
    calls += 1;
    response.writeHead(calls < 2 ? 503 : 200, { "content-type": "application/json" });
    response.end(JSON.stringify({ ok: calls >= 2 }));
  });

  try {
    const payload = await waitForHelperReady({
      baseUrl: helperBaseUrl({ port: server.port }),
      timeoutMs: 2000,
      intervalMs: 25,
    });

    assert.deepEqual(payload, { ok: true });
    assert.equal(calls >= 2, true);
  } finally {
    await server.close();
  }
});

test("supervisor reports port fallback and build mismatch without launch details", async () => {
  const occupied = await listenWithHealth();
  const child = fakeChild();
  const phases = [];
  const supervisor = new HelperSupervisor({
    startPort: occupied.port,
    logsDir: mkdtempSync(path.join(os.tmpdir(), "flyingpig-supervisor-")),
    spawnFn: () => child,
    waitForReady: async () => ({
      ok: true,
      build: { version: "1.0.1", identity: "1.0.1+synthetic" },
    }),
    expectedBuild: { version: "1.0.2" },
    onDiagnostics: (diagnostics) => phases.push(diagnostics.phase),
  });

  try {
    const diagnostics = await supervisor.start();
    assert.equal(diagnostics.phase, "ready");
    assert.equal(diagnostics.preferredPortOccupied, true);
    assert.equal(diagnostics.port, occupied.port + 1);
    assert.equal(diagnostics.buildMatch, "mismatch");
    assert.deepEqual(
      phases.filter((phase, index) => phase !== phases[index - 1]),
      ["port_selection", "spawn", "health_wait", "ready"],
    );
    assert.equal("command" in diagnostics, false);
    assert.equal("args" in diagnostics, false);
    assert.equal("logPath" in diagnostics, false);
  } finally {
    await supervisor.stop();
    await occupied.close();
  }
});

test("supervisor classifies early exit and readiness timeout", async () => {
  const earlyChild = fakeChild();
  const earlySupervisor = new HelperSupervisor({
    startPort: await findAvailablePort({ startPort: 18865 }),
    logsDir: mkdtempSync(path.join(os.tmpdir(), "flyingpig-supervisor-")),
    spawnFn: () => {
      queueMicrotask(() => earlyChild.emit("exit", 1, null));
      return earlyChild;
    },
    waitForReady: () => new Promise(() => {}),
  });
  await assert.rejects(
    earlySupervisor.start(),
    (error) => error.phase === "early_exit" && error.message.includes("exited before"),
  );

  const timeoutChild = fakeChild();
  const timeoutSupervisor = new HelperSupervisor({
    startPort: await findAvailablePort({ startPort: 18965 }),
    logsDir: mkdtempSync(path.join(os.tmpdir(), "flyingpig-supervisor-")),
    spawnFn: () => timeoutChild,
    waitForReady: async () => {
      throw new Error("private raw startup detail");
    },
  });
  await assert.rejects(
    timeoutSupervisor.start(),
    (error) => (
      error.phase === "health_wait"
      && error.message.includes("did not become ready")
      && !error.message.includes("private raw")
    ),
  );

  const spawnSupervisor = new HelperSupervisor({
    startPort: await findAvailablePort({ startPort: 19065 }),
    logsDir: mkdtempSync(path.join(os.tmpdir(), "flyingpig-supervisor-")),
    spawnFn: () => {
      throw new Error("private executable path");
    },
  });
  await assert.rejects(
    spawnSupervisor.start(),
    (error) => (
      error.phase === "spawn"
      && error.message.includes("could not be launched")
      && !error.message.includes("private executable")
    ),
  );
});

function fakeChild() {
  const child = new EventEmitter();
  child.stdout = new PassThrough();
  child.stderr = new PassThrough();
  child.killed = false;
  child.kill = () => {
    if (child.killed) return;
    child.killed = true;
    queueMicrotask(() => child.emit("exit", 0, "SIGTERM"));
  };
  return child;
}

async function listenWithHealth(handler = defaultHealthHandler) {
  const server = http.createServer((request, response) => {
    if (request.url === "/health") {
      handler(request, response);
      return;
    }
    response.writeHead(404);
    response.end();
  });

  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  return {
    port: server.address().port,
    close: () => new Promise((resolve) => server.close(resolve)),
  };
}

function defaultHealthHandler(_request, response) {
  response.writeHead(200, { "content-type": "application/json" });
  response.end(JSON.stringify({ ok: true }));
}
