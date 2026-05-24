import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import {
  buildHelperLaunchCommand,
  findAvailablePort,
  helperBaseUrl,
  helperExecutableName,
  waitForHelperReady,
} from "./helper_supervisor.js";

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
