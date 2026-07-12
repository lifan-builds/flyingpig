#!/usr/bin/env node
"use strict";

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const sourceDir = __dirname;
const coreScriptNames = [
  "codex-context-hook.js",
  "context-gen.js",
  "context-index.js",
  "format-on-edit.js",
  "guard.js",
  "install-project.js",
  "lib.js",
  "session-end.js",
  "task.js",
];
const knownManagedHashes = {
  "codex-context-hook.js": ["4d3bfe10a6c4b03d09c1575fa003a4a83497807fbf793851ba03579278bfde12", "f8384bd0705af8638a9f965e68f716a4554836debc36ec6689754516b5d663cb", "0fe64ff668e1d9e2417e4a6379ea23f62cd7bca48c6eb5c1452317f21b805a73", "670b326c902aeaca3a2bf3c4af03af783e6bcf2bf4c8727740c28877246b1801", "010ea95caa8222ad61095fdb2d941268723cfe2fcc57325016151ab8f27b1047", "aed3061433ad3f9260a9ab1a1ac2941dfb603801d782ffa1406457ccfb3c7a45"],
  "context-gen.js": ["75667fad241ea843eeea299d042406ddcf65ff9925b7658eb116dca66e740aed", "30884a4ac56bd9e7e6dd107a1435cdb9c708ca7d5e8f88780f3b5c2013240686", "460b60b1c9f3125b5e5c64767adb61ce38e6b76059f1fdd12e801ebc327b6517", "651906ca648ce3a1f9488ee6a5683dc980b884f326cd07f5a4aeadd0a383844c"],
  "context-index.js": ["1b3c83b006f3f1516f3fa3ac85536ca72b33be1ce33cac171f49d607d9fb576a", "eda249201125089acd7f99526880714f745bb35ebcdc259d91777c19e05cc47a", "90660fada7fc4149e182a2379bf5e517606ed6085b430137ea282c1026a8a8df", "8b9096632c9558deff7e46c0166ca00610a6af6cd3e8c227595a01fe19e53b61", "16c2e7d28acf0cbef148cd2cdcb6b9d76528a62d129debfe06490e38db001da7", "e7e26b737c26860c4090965ed957497496ea8a738943663e7164a3dcf1240cb2", "f3152e0e39d0cc16556e52789dc29e6da91853e93814ddfaf9a55e4c26bb7db9", "76f4c91e23daaacbaeb46f58d50634d6eecd4490c3df685fa213aeff8c4acdc3", "58c74f7cba606e91af6ba282cd5b53f1b7bf32c20a01f55ada90e469951154f8"],
  "format-on-edit.js": ["bbfa55779b79faade0f98a893b4341ffaf3988e530335b70ca1d417c2be6d76f"],
  "guard.js": ["d21aaa9cbd505cf3bdf71453286f491692804367b0f29bdb2cc988b78d9899dc"],
  "install-project.js": ["291bc7dbbce33115c7f2c9805d59dc88e530838bddec2b4d1ba2f17f5ad60015", "ade2eb2f3dc424c6d04435a85294dee56a095ab1a466b9bba48ca5eaefd49b33", "4b0d6292c3edc3fdd791d123bf51b05551e5fdfb7a2c2cd11924a21538c365ae", "fb2d04496a35bdd250d9f45c452ffa3dacd1fb2ef04f8f463d305e8584058109", "6df25a58feb90ee0bfa373848d5a09c31ecd251637d5203a07d49ce6f91543d3"],
  "lib.js": ["ab476b8b3bc2cb400160fa661f30daff06e015dfcc1b188469345246780a058d", "4a1c25b2b94b6849a5028fd8d95e03328d95a6e3542f889b54a22def0ee909f4", "0bffa391ddea24014e1939101dff317047a52433e6cff518afd6fa5dbf3e5462", "efbbb603a31ebc8efb42d20a600bede921f24d35da95133a328214e1aba7b2e9"],
  "session-end.js": ["2ca1297c5e11fe8076c4d107d62ad47f0f31d637523541a332e38035f90ba955"],
  "task.js": ["e121c555db7a54715cccb700894ea7ee0e8bb074eb195043d813f42636b2954d"],
};
const packageJsonContent = `${JSON.stringify({
  private: true,
  type: "commonjs",
  description: "context-harness runtime scripts",
}, null, 2)}\n`;

main();

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.fleetRoot) return runFleet(options);
  const result = updateProject(options.targetRoot, true);
  console.log(`Installed ${result.changed.length} context-harness scripts to scripts.`);
  if (result.conflicts.length) {
    for (const conflict of result.conflicts) console.error(`Refusing to overwrite existing non-context-harness script: ${conflict.path}`);
    console.error(`Skipped ${result.conflicts.length} existing non-context-harness scripts.`);
    process.exit(1);
  }
}

function runFleet(options) {
  const repos = discoverRepos(options.fleetRoot);
  const results = repos.map((repo) => updateProject(repo, options.apply, options.fleetRoot));
  const ledger = {
    schema: 1,
    mode: options.apply ? "apply" : "dry-run",
    rootId: path.basename(options.fleetRoot),
    summary: {
      discovered: results.length,
      changed: results.filter((entry) => entry.changed.length).length,
      unchanged: results.filter((entry) => !entry.changed.length && !entry.conflicts.length).length,
      conflicted: results.filter((entry) => entry.conflicts.length).length,
      failed: results.filter((entry) => entry.errors.length).length,
    },
    results,
  };
  if (options.ledger) {
    fs.mkdirSync(path.dirname(options.ledger), { recursive: true });
    fs.writeFileSync(options.ledger, `${JSON.stringify(ledger, null, 2)}\n`);
  }
  process.stdout.write(`${JSON.stringify(ledger, null, 2)}\n`);
  if (ledger.summary.failed) process.exitCode = 1;
}

function updateProject(targetRoot, apply, fleetRoot = targetRoot) {
  const before = gitState(targetRoot);
  const dirtyHashes = hashPaths(targetRoot, before.dirtyPaths);
  const candidates = coreScriptNames.map((name) => classifyCandidate(name, targetRoot));
  candidates.push(classifyPackage(targetRoot));
  const changed = [];
  const conflicts = candidates.filter((entry) => entry.classification === "managed-local");
  const errors = [];

  if (apply) {
    for (const candidate of candidates) {
      if (!["missing", "managed-clean"].includes(candidate.classification) || candidate.beforeHash === candidate.sourceHash) continue;
      const currentHash = fileHash(candidate.absolutePath);
      if (currentHash !== candidate.beforeHash) {
        conflicts.push({ path: candidate.path, classification: "changed-after-plan" });
        continue;
      }
      fs.mkdirSync(path.dirname(candidate.absolutePath), { recursive: true });
      fs.writeFileSync(candidate.absolutePath, candidate.content);
      changed.push(candidate.path);
    }
  } else {
    changed.push(...candidates.filter((entry) => ["missing", "managed-clean"].includes(entry.classification) && entry.beforeHash !== entry.sourceHash).map((entry) => entry.path));
  }

  let update = { status: "not-run" };
  let check = { status: "not-run" };
  if (apply && changed.length && hasHarness(targetRoot)) {
    update = runIndex(targetRoot, "update");
    if (update.status === 0) check = runIndex(targetRoot, "check");
    else errors.push("context index update failed");
    if (check.status !== "not-run" && check.status !== 0) errors.push("context index check failed");
  }

  const preservedDirtyPaths = [];
  for (const [relative, hash] of Object.entries(dirtyHashes)) {
    if (changed.includes(relative) || relative.startsWith(".context-harness/") || relative === "AGENTS.md") continue;
    if (fileHash(path.join(targetRoot, relative)) === hash) preservedDirtyPaths.push(relative);
    else errors.push(`preexisting dirty path changed: ${relative}`);
  }

  return {
    repo: path.relative(fleetRoot, targetRoot) || path.basename(targetRoot),
    revision: before.revision,
    dirty: before.dirtyPaths.length > 0,
    considered: candidates.map(({ path: relative, classification, beforeHash, sourceHash }) => ({ path: relative, classification, beforeHash, sourceHash })),
    changed,
    conflicts: uniqueByPath(conflicts).map(({ path: relative, classification }) => ({ path: relative, classification })),
    preservedDirtyPaths,
    update,
    check,
    errors,
  };
}

function classifyCandidate(name, targetRoot) {
  const source = path.join(sourceDir, name);
  const absolutePath = path.join(targetRoot, "scripts", name);
  const content = fs.readFileSync(source, "utf8");
  const beforeHash = fileHash(absolutePath);
  const sourceHash = sha256(content);
  let classification = "managed-local";
  if (!beforeHash) classification = "missing";
  else if (beforeHash === sourceHash || (knownManagedHashes[name] || []).includes(beforeHash)) classification = "managed-clean";
  return { path: `scripts/${name}`, absolutePath, content, beforeHash, sourceHash, classification };
}

function classifyPackage(targetRoot) {
  const absolutePath = path.join(targetRoot, "scripts", "package.json");
  const beforeHash = fileHash(absolutePath);
  const sourceHash = sha256(packageJsonContent);
  return {
    path: "scripts/package.json",
    absolutePath,
    content: packageJsonContent,
    beforeHash,
    sourceHash,
    classification: !beforeHash ? "missing" : beforeHash === sourceHash ? "managed-clean" : "managed-local",
  };
}

function discoverRepos(root) {
  const repos = [];
  const visit = (dir) => {
    let entries;
    try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
    if (fs.existsSync(path.join(dir, ".git"))) {
      if (hasHarness(dir)) repos.push(dir);
      return;
    }
    for (const entry of entries) {
      if (!entry.isDirectory() || [".git", "node_modules", ".context-harness", ".cache"].includes(entry.name)) continue;
      visit(path.join(dir, entry.name));
    }
  };
  visit(root);
  return repos.sort();
}

function hasHarness(root) {
  return fs.existsSync(path.join(root, "CONTEXT.md"));
}

function gitState(root) {
  const revision = runGit(root, ["rev-parse", "HEAD"]);
  const status = runGit(root, ["status", "--porcelain=v1", "-z"]);
  const dirtyPaths = status.status === 0
    ? status.stdout.split("\0").filter(Boolean).map((entry) => entry.slice(3)).filter((entry) => !entry.includes(" -> "))
    : [];
  return { revision: revision.status === 0 ? revision.stdout.trim() : null, dirtyPaths };
}

function hashPaths(root, paths) {
  return Object.fromEntries(paths.map((relative) => [relative, fileHash(path.join(root, relative))]));
}

function runIndex(root, command) {
  const script = path.join(root, "scripts", "context-index.js");
  const result = spawnSync(process.execPath, [script, command], { cwd: root, encoding: "utf8" });
  return { status: result.status ?? 1, outputHash: sha256(`${result.stdout || ""}${result.stderr || ""}`) };
}

function runGit(root, args) {
  const result = spawnSync("git", args, { cwd: root, encoding: "utf8" });
  return { status: result.status ?? 1, stdout: result.stdout || "" };
}

function fileHash(file) {
  try { return sha256(fs.readFileSync(file)); } catch { return null; }
}

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

function uniqueByPath(entries) {
  return [...new Map(entries.map((entry) => [entry.path, entry])).values()];
}

function parseArgs(args) {
  const options = { targetRoot: process.cwd(), fleetRoot: "", ledger: "", apply: false };
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (["--help", "-h"].includes(arg)) usage(0);
    if (arg === "--fleet") options.fleetRoot = path.resolve(args[++index] || "");
    else if (arg === "--ledger") options.ledger = path.resolve(args[++index] || "");
    else if (arg === "--apply") options.apply = true;
    else if (arg === "--dry-run") options.apply = false;
    else if (arg.startsWith("-")) usage(1, `Unknown argument: ${arg}`);
    else if (options.targetRoot !== process.cwd()) usage(1, `Unexpected extra argument: ${arg}`);
    else options.targetRoot = path.resolve(arg);
  }
  return options;
}

function usage(code, message = "") {
  if (message) console.error(message);
  console.error("Usage: install-project.js [project-root]\n       install-project.js --fleet <root> [--dry-run|--apply] [--ledger <file>]");
  process.exit(code);
}
