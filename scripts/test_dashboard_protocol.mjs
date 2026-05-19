#!/usr/bin/env node

import assert from "node:assert/strict";

import {
  attentionForRequest,
  checkpointCustomAnswer,
  checkpointOptionAnswer,
  fallbackPendingRequest,
  requestKey,
  siteLabel,
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
  type: "question",
  question: "Please confirm.",
  reason: "agent needs input",
});

console.log("Dashboard protocol unit tests passed.");
