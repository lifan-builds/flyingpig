#!/usr/bin/env node

import assert from "node:assert/strict";

import {
  attentionForRequest,
  checkpointCustomAnswer,
  checkpointOptionAnswer,
  fallbackPendingRequest,
  progressMessage,
  readableRunStatus,
  requestKey,
  siteLabel,
  statusForPendingRequest,
} from "../dashboard/dashboard_protocol.js";

const checkpoint = {
  checkpoint_id: "cp_test",
  summary: "No retention offer is available.",
};
const option = {
  id: "close_card",
  message_to_send: "I would like to proceed toward closing.",
};

assert.equal(siteLabel("amex", [{ id: "amex", label: "American Express" }]), "American Express");
assert.equal(siteLabel("oura"), "oura");
assert.equal(
  requestKey({ type: "decision_checkpoint", checkpoint }),
  "checkpoint:cp_test",
);
assert.deepEqual(attentionForRequest({ type: "decision_checkpoint", checkpoint }), {
  title: "Flying Pig needs a decision",
  message: "No retention offer is available.",
});
assert.deepEqual(checkpointOptionAnswer(checkpoint, option), {
  checkpoint_id: "cp_test",
  selected_option_id: "close_card",
  selected_message: "I would like to proceed toward closing.",
});
assert.deepEqual(checkpointCustomAnswer(checkpoint, "Try one more time."), {
  checkpoint_id: "cp_test",
  selected_option_id: "custom",
  selected_message: null,
  free_text: "Try one more time.",
});
assert.deepEqual(fallbackPendingRequest({
  needs_input: true,
  message: "Please confirm.",
}), {
  type: "missing_information",
  original_type: "question",
  question: "Please confirm.",
  reason: "agent needs input",
});
assert.equal(readableRunStatus("waiting_on_rep"), "Waiting on representative");
assert.equal(statusForPendingRequest({ type: "manual_login_required" }), "waiting_on_login");
assert.equal(statusForPendingRequest({ type: "offer_received" }), "checkpoint_pending");
assert.equal(progressMessage({ phase: "starting", message: "Step 4 started" }), "Checking the page and support chat before acting.");
assert.equal(progressMessage({ display_message: "Representative is reviewing the account." }), "Representative is reviewing the account.");
assert.deepEqual(attentionForRequest({
  type: "manual_login_required",
  question: "Please log in in the visible browser.",
}), {
  title: "Manual login needed",
  message: "Please log in in the visible browser.",
});

console.log("Dashboard protocol unit tests passed.");
