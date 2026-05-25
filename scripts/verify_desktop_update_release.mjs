#!/usr/bin/env node

import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");
const distDir = path.join(root, "dist", "desktop");
const latestMacPath = path.join(distDir, "latest-mac.yml");
const appPath = path.join(distDir, "mac-arm64", "Flying Pig.app");
const args = new Set(process.argv.slice(2));
const tagArg = process.argv.find((arg) => arg.startsWith("--tag="));
const tag = tagArg?.slice("--tag=".length);
const requireSigned = args.has("--require-signed");
const checkGithub = args.has("--github");

function fail(message) {
  console.error(`Desktop update verification failed: ${message}`);
  process.exit(1);
}

function parseLatestMac(text) {
  const pathMatch = text.match(/^path:\s*(.+)$/m);
  const sizeMatch = text.match(/^\s+size:\s*(\d+)$/m);
  const shaMatch = text.match(/^sha512:\s*(.+)$/m);
  const versionMatch = text.match(/^version:\s*(.+)$/m);
  if (!pathMatch || !sizeMatch || !shaMatch || !versionMatch) {
    fail("latest-mac.yml is missing version, path, size, or sha512.");
  }
  return {
    version: versionMatch[1].trim().replace(/^['"]|['"]$/g, ""),
    fileName: pathMatch[1].trim().replace(/^['"]|['"]$/g, ""),
    size: Number(sizeMatch[1]),
    sha512: shaMatch[1].trim().replace(/^['"]|['"]$/g, ""),
  };
}

function run(command, commandArgs) {
  const result = spawnSync(command, commandArgs, {
    cwd: root,
    encoding: "utf8",
  });
  return {
    ok: result.status === 0,
    stdout: result.stdout || "",
    stderr: result.stderr || "",
  };
}

if (!existsSync(latestMacPath)) {
  fail("dist/desktop/latest-mac.yml does not exist. Run npm run desktop:package first.");
}

const latestMac = parseLatestMac(readFileSync(latestMacPath, "utf8"));
const zipPath = path.join(distDir, latestMac.fileName);
if (!existsSync(zipPath)) {
  fail(`latest-mac.yml points to missing artifact ${latestMac.fileName}.`);
}
assert.equal(statSync(zipPath).size, latestMac.size);
const actualSha512 = createHash("sha512").update(readFileSync(zipPath)).digest("base64");
assert.equal(actualSha512, latestMac.sha512);

if (!existsSync(appPath)) {
  fail("packaged app bundle is missing from dist/desktop/mac-arm64.");
}

const codeSign = run("codesign", ["--verify", "--deep", "--strict", "--verbose=2", appPath]);
if (!codeSign.ok) {
  const message = `codesign verification failed for ${appPath}`;
  if (requireSigned) fail(`${message}\n${codeSign.stderr}`);
  console.warn(`${message}; continuing because --require-signed was not set.`);
} else {
  const spctl = run("spctl", ["-a", "-vvv", "-t", "execute", appPath]);
  if (!spctl.ok) {
    const message = `Gatekeeper assessment failed for ${appPath}`;
    if (requireSigned) fail(`${message}\n${spctl.stderr || spctl.stdout}`);
    console.warn(`${message}; continuing because --require-signed was not set.`);
  }
}

if (checkGithub) {
  if (!tag) fail("--github requires --tag=vX.Y.Z.");
  const repo = JSON.parse(
    execFileSync("gh", [
      "repo",
      "view",
      "lifan-builds/flyingpig",
      "--json",
      "visibility",
    ], { encoding: "utf8" }),
  );
  assert.equal(repo.visibility, "PUBLIC");
  const release = JSON.parse(
    execFileSync("gh", [
      "release",
      "view",
      tag,
      "--repo",
      "lifan-builds/flyingpig",
      "--json",
      "assets,isDraft,isPrerelease",
    ], { encoding: "utf8" }),
  );
  assert.equal(release.isDraft, false);
  const assetNames = release.assets.map((asset) => asset.name);
  for (const required of [latestMac.fileName, `${latestMac.fileName}.blockmap`, "latest-mac.yml"]) {
    if (!assetNames.includes(required)) {
      fail(`GitHub release ${tag} is missing update asset ${required}.`);
    }
  }
}

console.log(
  `Desktop update artifacts verified for ${latestMac.version}: ${latestMac.fileName}`,
);
