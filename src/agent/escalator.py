"""Human representative escalation strategies.

When the detector identifies an AI chatbot, this module provides ordered
escalation strategies to reach a human agent.
"""

from dataclasses import dataclass
from enum import StrEnum


class EscalationStrategy(StrEnum):
    DIRECT_REQUEST = "direct_request"
    COMPLEXITY = "complexity"
    KEYWORD_TRIGGER = "keyword_trigger"
    DISSATISFACTION = "dissatisfaction"
    CHANNEL_SWITCH = "channel_switch"


@dataclass
class EscalationAttempt:
    strategy: EscalationStrategy
    message_sent: str
    succeeded: bool
    response_summary: str


class EscalationManager:
    """Manages escalation from AI chatbot to human representative.

    Strategies are ordered by effectiveness and tried sequentially.
    The instructions are embedded into the agent's task prompt.
    """

    def get_instructions(self) -> str:
        """Return escalation instructions to embed in the agent's task prompt."""
        return """
## Human Escalation Instructions

If you detect the responder is an AI chatbot, attempt to reach a human representative
using these strategies IN ORDER. Move to the next strategy if the current one fails.

### Strategy 1: Direct Request
Say: "I appreciate your help, but I'd like to speak with a human representative please."
If the bot offers alternatives, insist politely: "I understand, but I specifically need
a human agent for this matter."

### Strategy 2: Complexity Escalation
Introduce nuance that exceeds typical chatbot capabilities:
"My situation involves multiple accounts and a billing discrepancy across several
statement periods. I'd need someone who can look at the full picture."

### Strategy 3: Keyword Triggers
Use known escalation phrases naturally in your message:
- "I'd like to file a formal complaint"
- "Please connect me with a supervisor"
- "I need to speak with a manager about this"
- "This needs to be escalated"

### Strategy 4: Dissatisfaction Signal
Express that the current assistance is insufficient:
"I don't think this is being resolved adequately. I've explained my situation
and the responses aren't addressing my specific case. I need human assistance."

### Strategy 5: Channel Switch
If chat escalation fails after strategies 1-4:
"Can you transfer me to a phone callback? I'd like to discuss this with
someone directly."

### Recovery: Hangup and Call-again
If the chat gives a final refusal, the representative disconnects, or the chat
appears dead after reasonable waiting, use a fresh-chat recovery only after user
confirmation. Ask the user whether to end this chat and start a new one. If the
user confirms, end the current chat, open a new chat in the same browser session,
and restate the current task from scratch without referencing old agent names.

### Important Rules
- Try each strategy ONCE before moving to the next
- Wait for the response after each attempt — the bot may comply
- If a strategy partially works (e.g., "let me check if an agent is available"),
  wait and follow the process rather than immediately trying the next strategy
- After all 5 escalation strategies, if still talking to AI, proceed to negotiate with the
  AI chatbot — some resolution is better than none
- Hangup and call-again is a separate recovery path, not an escalation attempt,
  and must only happen after explicit user confirmation
- NEVER be rude or hostile — firm but polite always works better
- Maximum 5 escalation attempts total before proceeding with whoever you're talking to
"""
