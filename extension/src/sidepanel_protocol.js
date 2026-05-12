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

export function siteLabel(site) {
  if (site === "amex") return "American Express";
  if (site === "oura") return "Oura Ring";
  if (site === "generic") return "Generic chat";
  if (site === "unknown" || !site) return "Current tab";
  return site;
}

export function requestKey(request) {
  if (!request) return null;
  if (request.type === "decision_checkpoint") {
    return `checkpoint:${request.checkpoint?.checkpoint_id || request.checkpoint?.summary || ""}`;
  }
  if (request.type === "question") {
    return `question:${request.question || ""}`;
  }
  return JSON.stringify(request);
}

export function attentionForRequest(request) {
  if (!request) return null;
  if (request.type === "decision_checkpoint") {
    return {
      title: "Flying Pig needs a decision",
      message: request.checkpoint?.summary || "Choose how Flying Pig should proceed.",
    };
  }
  if (request.type === "question") {
    return {
      title: "Flying Pig needs input",
      message: request.question || "The agent needs input.",
    };
  }
  return null;
}

export function fallbackPendingRequest(message) {
  if (!message?.needs_input || !message.message) return null;
  return {
    type: "question",
    question: message.message,
    reason: "agent needs input",
  };
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
