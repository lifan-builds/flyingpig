#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import { writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const revision = safeRevision(process.env.FLYINGPIG_BUILD_REVISION) || gitRevision();
const builtAt = buildTimestamp();
const channel = safeToken(process.env.FLYINGPIG_BUILD_CHANNEL) || "packaged";

const pythonPayload = JSON.stringify(
  { revision, built_at: builtAt, channel },
  null,
  4,
).replaceAll(": null", ": None");
const python = `"""Generated PII-free package build metadata."""

BUILD_METADATA = ${pythonPayload}
`;
const javascript = `// Generated PII-free package build metadata.
export const buildMetadata = Object.freeze(${JSON.stringify({ revision, builtAt, channel }, null, 2)});
`;

await Promise.all([
  writeFile(path.join(root, "src", "_build_metadata.py"), python, "utf8"),
  writeFile(path.join(root, "desktop", "build_metadata.js"), javascript, "utf8"),
]);
console.log(`Generated Flying Pig build metadata for ${revision || "unknown revision"}.`);

function gitRevision() {
  try {
    return safeRevision(
      execFileSync("git", ["rev-parse", "--short=12", "HEAD"], {
        cwd: root,
        encoding: "utf8",
        stdio: ["ignore", "pipe", "ignore"],
      }).trim(),
    );
  } catch {
    return null;
  }
}

function buildTimestamp() {
  const sourceDateEpoch = Number(process.env.SOURCE_DATE_EPOCH);
  if (Number.isFinite(sourceDateEpoch) && sourceDateEpoch > 0) {
    return new Date(sourceDateEpoch * 1000).toISOString();
  }
  try {
    const commitEpoch = Number(execFileSync("git", ["show", "-s", "--format=%ct", "HEAD"], {
      cwd: root,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim());
    return Number.isFinite(commitEpoch) && commitEpoch > 0
      ? new Date(commitEpoch * 1000).toISOString()
      : null;
  } catch {
    return null;
  }
}

function safeRevision(value) {
  const normalized = String(value || "").trim();
  return /^[a-f0-9]{7,40}$/i.test(normalized) ? normalized : null;
}

function safeToken(value) {
  const normalized = String(value || "").trim();
  return /^[A-Za-z0-9._+-]{1,40}$/.test(normalized) ? normalized : null;
}
