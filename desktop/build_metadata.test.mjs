import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import {
  copyFileSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
} from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

test("build metadata generation is reproducible and PII-free", () => {
  const temporaryRoot = mkdtempSync(path.join(os.tmpdir(), "flyingpig-build-metadata-"));
  for (const directory of ["scripts", "src", "desktop"]) {
    mkdirSync(path.join(temporaryRoot, directory), { recursive: true });
  }
  const generator = path.join(temporaryRoot, "scripts", "generate_build_metadata.mjs");
  copyFileSync(path.join(repositoryRoot, "scripts", "generate_build_metadata.mjs"), generator);
  const env = {
    ...process.env,
    FLYINGPIG_BUILD_REVISION: "abcdef123456",
    FLYINGPIG_BUILD_CHANNEL: "synthetic",
    SOURCE_DATE_EPOCH: "1767225600",
  };

  execFileSync(process.execPath, [generator], { env, stdio: "ignore" });
  const firstPython = readFileSync(path.join(temporaryRoot, "src", "_build_metadata.py"), "utf8");
  const firstJavaScript = readFileSync(
    path.join(temporaryRoot, "desktop", "build_metadata.js"),
    "utf8",
  );
  execFileSync(process.execPath, [generator], { env, stdio: "ignore" });

  assert.equal(
    readFileSync(path.join(temporaryRoot, "src", "_build_metadata.py"), "utf8"),
    firstPython,
  );
  assert.equal(
    readFileSync(path.join(temporaryRoot, "desktop", "build_metadata.js"), "utf8"),
    firstJavaScript,
  );
  assert.match(firstPython, /abcdef123456/);
  assert.match(firstJavaScript, /2026-01-01T00:00:00.000Z/);
  assert.equal(firstPython.includes(temporaryRoot), false);
  assert.equal(firstJavaScript.includes(temporaryRoot), false);
});
