#!/usr/bin/env node
"use strict";

// codex-context-hook.js — lifecycle nudges for Codex.
// Hooks do not run skills directly; they add compact context so the active
// agent invokes context-catch-up, context-init, or context-maintain at the right
// moment.

const fs = require("fs");
const path = require("path");
const { readHookInput, readTextSafe, findProjectRoot } = require("./lib");

const mode = readArg("--mode") || "catch-up";
const input = readHookInput();
const cwd = path.resolve(input.cwd || process.cwd());

try {
  if (mode === "catch-up") runCatchUp(cwd);
  else if (mode === "init") runInit(cwd);
  else if (mode === "maintain") runMaintain(cwd);
} catch {
  // Context hooks are best-effort. They should never break ordinary Codex work.
}

process.exit(0);

// ---------------------------------------------------------------------------

function runCatchUp(startDir) {
  const root = findContextRoot(startDir);
  if (!root) return;

  const agents = readTextSafe(path.join(root, "AGENTS.md"));
  const context = readTextSafe(path.join(root, "CONTEXT.md"));
  const now = trimForHook(readTextSafe(path.join(root, "NOW.md")), 1400);
  const needsUpgrade = !hasCurrentSchema(agents) || !hasCurrentSchema(context) || !hasContextIndex(agents) || !context.trim();
  emitAdditionalContext(
    [
      "context-harness detected.",
      needsUpgrade
        ? "Before planning or editing, use context-catch-up Compatibility Upgrade. Preserve local context, add the current schema marker, install runtime scripts, and refresh the AGENTS.md Context Index."
        : "Before planning or editing, use context-catch-up: read NOW.md first, then read relevant CONTEXT.md sections from AGENTS.md.",
      now ? `Current NOW.md:\n${now}` : "",
    ]
      .filter(Boolean)
      .join("\n\n")
  );
}

function runInit(startDir) {
  if (findContextRoot(startDir)) return;

  const projectRoot = findProjectRoot(startDir);
  if (!looksLikeProject(projectRoot)) return;

  emitAdditionalContext(
    [
      "No context-harness files were found for this project.",
      "Before substantial project work, use context-init to create AGENTS.md, CONTEXT.md, NOW.md, and optional PLAN.md.",
      "If the user only asked for a tiny one-off command, continue without initialization.",
    ].join("\n")
  );
}

function runMaintain(startDir) {
  const root = findContextRoot(startDir);
  if (!root) return;

  emitAdditionalContext(
    [
      "Before ending after a substantial task, use context-maintain.",
      "Update NOW.md with current focus, blockers, next step, and touched files.",
      "Route durable terms, rules, relationships, and repeated lessons to CONTEXT.md; route task-local findings and decisions to PLAN.md.",
      "If CONTEXT.md changed, refresh AGENTS.md with `node scripts/context-index.js update`.",
    ].join("\n")
  );
}

function findContextRoot(startDir) {
  let current = path.resolve(startDir);
  while (current !== path.dirname(current)) {
    const hasContext = fs.existsSync(path.join(current, "CONTEXT.md"));
    const hasNow = fs.existsSync(path.join(current, "NOW.md"));
    const hasAgents = fs.existsSync(path.join(current, "AGENTS.md"));
    if (hasContext && (hasNow || hasAgents)) return current;
    current = path.dirname(current);
  }
  return null;
}

function looksLikeProject(root) {
  if (!root || root === path.dirname(root)) return false;
  return [
    ".git",
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "Gemfile",
  ].some((marker) => fs.existsSync(path.join(root, marker)));
}

function trimForHook(text, maxChars) {
  const trimmed = text.trim();
  if (trimmed.length <= maxChars) return trimmed;
  return `${trimmed.slice(0, maxChars).trimEnd()}\n...`;
}

function hasCurrentSchema(text) {
  return /<!--\s*context-harness:schema\s+v2\s*-->/.test(text);
}

function hasContextIndex(text) {
  return /<!--\s*context-harness:index:start\s*-->/.test(text);
}

function emitAdditionalContext(additionalContext) {
  console.log(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: input.hook_event_name || eventNameForMode(mode),
        additionalContext,
      },
    })
  );
}

function eventNameForMode(value) {
  if (value === "catch-up") return "SessionStart";
  if (value === "init") return "UserPromptSubmit";
  if (value === "maintain") return "Stop";
  return "";
}

function readArg(name) {
  const index = process.argv.indexOf(name);
  if (index === -1) return "";
  return process.argv[index + 1] || "";
}
