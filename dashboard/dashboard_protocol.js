export function formatTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function siteLabel(site, sites = []) {
  const match = sites.find((item) => item.id === site);
  if (match?.label) return match.label;
  if (site === "generic") return "Generic chat";
  if (site === "unknown" || !site) return "Work window";
  return site;
}

export const userAttentionTypes = new Set([
  "question",
  "decision_checkpoint",
  "missing_information",
  "otp_required",
  "auth_required",
  "manual_login_required",
  "account_access_blocked",
  "resume_after_auth",
  "attachment_required",
  "irreversible_action_pending",
  "offer_received",
  "recovery_pending",
]);

export function isUserAttentionRequest(request) {
  return userAttentionTypes.has(request?.type);
}

export function requestKey(request) {
  if (!request) return null;
  if (request.type === "decision_checkpoint" || request.original_type === "decision_checkpoint") {
    return `checkpoint:${request.checkpoint?.checkpoint_id || request.checkpoint?.summary || ""}`;
  }
  if (request.question) {
    return `question:${request.question || ""}`;
  }
  return JSON.stringify(request);
}

export function attentionForRequest(request) {
  if (!request) return null;
  if (request.type === "decision_checkpoint" || request.original_type === "decision_checkpoint") {
    return {
      title: "Flying Pig needs a decision",
      message: request.checkpoint?.summary || "Choose how Flying Pig should proceed.",
    };
  }
  const labels = {
    missing_information: "Flying Pig needs information",
    otp_required: "Verification code needed",
    auth_required: "Authentication needed",
    manual_login_required: "Manual login needed",
    account_access_blocked: "Account access blocked",
    resume_after_auth: "Resume after auth",
    attachment_required: "Attachment needed",
    irreversible_action_pending: "Approval needed",
    offer_received: "Offer received",
    recovery_pending: "Recovery decision needed",
  };
  if (request.question || labels[request.type]) {
    return {
      title: labels[request.type] || "Flying Pig needs input",
      message: request.question || "The agent needs input.",
    };
  }
  return null;
}

export function fallbackPendingRequest(message) {
  if (!message?.needs_input || !message.message) return null;
  return {
    type: "missing_information",
    original_type: "question",
    question: message.message,
    reason: "agent needs input",
  };
}

export function readableRunStatus(status) {
  const labels = {
    preparing: "Preparing",
    ready_to_start: "Ready",
    running: "Working",
    waiting_on_user: "Waiting on you",
    waiting_on_rep: "Waiting on representative",
    waiting_on_login: "Waiting on login",
    waiting_on_auth: "Waiting on authentication",
    checkpoint_pending: "Approval needed",
    recovery_pending: "Recovery pending",
    completed: "Completed",
    failed: "Failed",
    cancelled: "Cancelled",
    idle: "Ready",
    starting: "Preparing",
    needs_input: "Waiting on you",
    success: "Completed",
    partial: "Completed with follow-up",
    error: "Failed",
  };
  return labels[status] || status || "Ready";
}

export function statusForPendingRequest(request) {
  if (request?.type === "manual_login_required") return "waiting_on_login";
  if (["otp_required", "auth_required", "account_access_blocked", "resume_after_auth"].includes(request?.type)) {
    return "waiting_on_auth";
  }
  if (["decision_checkpoint", "irreversible_action_pending", "offer_received"].includes(request?.type) || request?.original_type === "decision_checkpoint") {
    return "checkpoint_pending";
  }
  if (request?.type === "recovery_pending") return "recovery_pending";
  return "waiting_on_user";
}

export function progressMessage(event) {
  const raw = event?.display_message || event?.message || event?.goal || event?.thought || "";
  if (raw && !/^Step \d+ started$/.test(raw)) return raw;
  if (event?.phase === "starting") {
    return "Checking the page and support chat before acting.";
  }
  return "Working on the customer-service chat.";
}

export function checkpointOptionAnswer(checkpoint, option) {
  return {
    checkpoint_id: checkpoint.checkpoint_id,
    selected_option_id: option.id,
    selected_message: option.message_to_send || null,
  };
}

export function checkpointCustomAnswer(checkpoint, text) {
  return {
    checkpoint_id: checkpoint.checkpoint_id,
    selected_option_id: "custom",
    selected_message: null,
    free_text: text,
  };
}
