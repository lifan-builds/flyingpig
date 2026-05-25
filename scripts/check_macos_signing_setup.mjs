#!/usr/bin/env node

import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

const REPO = "lifan-builds/flyingpig";
const REQUIRED_GITHUB_SECRETS = [
  "MAC_CSC_LINK",
  "MAC_CSC_KEY_PASSWORD",
  "APPLE_API_KEY_P8",
  "APPLE_API_KEY_ID",
  "APPLE_API_ISSUER",
  "APPLE_TEAM_ID",
];
const REQUIRED_LOCAL_ENV = [
  "CSC_LINK",
  "CSC_KEY_PASSWORD",
  "APPLE_API_KEY",
  "APPLE_API_KEY_ID",
  "APPLE_API_ISSUER",
  "APPLE_TEAM_ID",
];

function printStatus(ok, label, detail = "") {
  const marker = ok ? "ok" : "missing";
  const suffix = detail ? ` - ${detail}` : "";
  console.log(`${marker}: ${label}${suffix}`);
}

async function findDeveloperIdIdentities() {
  try {
    const { stdout } = await execFileAsync("security", [
      "find-identity",
      "-v",
      "-p",
      "codesigning",
    ]);
    return stdout
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line.includes("Developer ID Application:"));
  } catch (error) {
    const output = `${error.stdout || ""}${error.stderr || ""}`.trim();
    throw new Error(output || error.message);
  }
}

async function listGitHubSecrets() {
  const { stdout } = await execFileAsync("gh", [
    "secret",
    "list",
    "--repo",
    REPO,
  ]);
  return new Set(
    stdout
      .split("\n")
      .map((line) => line.trim().split(/\s+/)[0])
      .filter(Boolean),
  );
}

async function main() {
  const checkGitHub = process.argv.includes("--github");
  let failures = 0;

  console.log("macOS signing setup");

  const identities = await findDeveloperIdIdentities();
  if (identities.length > 0) {
    printStatus(true, "Developer ID Application identity", identities[0]);
    if (identities.length > 1) {
      printStatus(true, "Additional Developer ID identities", `${identities.length - 1}`);
    }
  } else {
    printStatus(false, "Developer ID Application identity");
    failures += 1;
  }

  console.log("\nlocal release environment");
  for (const name of REQUIRED_LOCAL_ENV) {
    const hasValue = Boolean(process.env[name]);
    printStatus(hasValue, name);
    if (!hasValue) {
      failures += 1;
    }
  }

  if (checkGitHub) {
    console.log("\nGitHub repository secrets");
    try {
      const secrets = await listGitHubSecrets();
      for (const name of REQUIRED_GITHUB_SECRETS) {
        const exists = secrets.has(name);
        printStatus(exists, name);
        if (!exists) {
          failures += 1;
        }
      }
    } catch (error) {
      printStatus(false, "GitHub secret check", error.message);
      failures += 1;
    }
  } else {
    console.log("\nRun with --github to verify required repository secret names via gh.");
  }

  if (failures > 0) {
    console.log(`\n${failures} signing setup check(s) need attention.`);
    process.exit(1);
  }

  console.log("\nSigning setup checks passed.");
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
