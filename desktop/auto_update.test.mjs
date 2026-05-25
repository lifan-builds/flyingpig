import assert from "node:assert/strict";
import { test } from "node:test";

import { configureAutoUpdates } from "./auto_update.js";

test("skips update checks for development app runs", async () => {
  const statuses = [];
  const calls = [];
  const updater = mockUpdater(calls);
  const updates = configureAutoUpdates({
    app: { isPackaged: false },
    autoUpdater: updater,
    onStatus: (status) => statuses.push(status),
  });

  const result = await updates.checkForUpdates({ manual: true });

  assert.equal(result.skipped, true);
  assert.equal(calls.includes("check"), false);
  assert.equal(statuses.at(-1).state, "skipped");
});

test("tracks downloaded update and installs on relaunch", async () => {
  const statuses = [];
  const calls = [];
  const updater = mockUpdater(calls);
  const updates = configureAutoUpdates({
    app: { isPackaged: true },
    autoUpdater: updater,
    onStatus: (status) => statuses.push(status),
  });

  await updates.checkForUpdates();
  updater.emit("update-downloaded", { version: "1.0.2" });

  assert.equal(calls.includes("check"), true);
  assert.equal(updates.downloaded, true);
  assert.equal(statuses.at(-1).state, "downloaded");
  assert.equal(updates.installUpdateAndRelaunch(), true);
  assert.equal(calls.includes("quitAndInstall:false:true"), true);
});

function mockUpdater(calls) {
  const handlers = new Map();
  return {
    on(event, handler) {
      handlers.set(event, handler);
    },
    emit(event, payload) {
      handlers.get(event)?.(payload);
    },
    async checkForUpdatesAndNotify() {
      calls.push("check");
      return { updateInfo: { version: "1.0.2" } };
    },
    quitAndInstall(isSilent, isForceRunAfter) {
      calls.push(`quitAndInstall:${isSilent}:${isForceRunAfter}`);
    },
  };
}
