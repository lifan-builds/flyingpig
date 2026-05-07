"""AI chatbot detection module.

Analyzes chat responses to determine if the responder is an AI chatbot or a human.
Uses weighted signal scoring to make the classification.
"""

from dataclasses import dataclass
from enum import StrEnum


class ResponderType(StrEnum):
    AI_CHATBOT = "ai_chatbot"
    HUMAN = "human"
    UNCERTAIN = "uncertain"


@dataclass
class DetectionSignal:
    name: str
    weight: float
    score: float  # 0.0 = human-like, 1.0 = bot-like
    evidence: str


@dataclass
class DetectionResult:
    responder_type: ResponderType
    confidence: float  # 0.0 to 1.0
    signals: list[DetectionSignal]
    should_escalate: bool


# Threshold above which we classify as AI
AI_THRESHOLD = 0.65
# Threshold below which we classify as human
HUMAN_THRESHOLD = 0.35


class ChatbotDetector:
    """Detects whether a chat responder is an AI chatbot or human agent.

    Uses multiple weighted signals analyzed by the LLM to produce a classification.
    The detection is embedded into the agent's task prompt so the LLM evaluates
    signals in real-time during conversation.
    """

    def get_instructions(self) -> str:
        """Return detection instructions to embed in the agent's task prompt."""
        return """
## AI Chatbot Detection

As you interact with the customer service chat, continuously evaluate whether
you are speaking with an AI chatbot or a human representative. Track these signals:

1. **Response Latency** (High weight): AI responds in consistent <2s bursts.
   Humans have variable 5-30s gaps with typing indicators.

2. **Message Structure** (High weight): AI uses templated greetings, bullet points,
   numbered lists, and disclaimers like "I'm a virtual assistant" or "as an AI".
   Humans write more casually with typos and varied formatting.

3. **Canned Response Matching** (Medium weight): AI repeats near-identical phrases
   across exchanges. Humans paraphrase and adapt.

4. **Personalization Depth** (Medium weight): AI gives generic policy answers.
   Humans reference specific account details unprompted.

5. **Flexibility Test** (High weight): After 2-3 exchanges, ask something slightly
   off-script (e.g., "By the way, how's your day going?" or reference a specific
   scenario). AI will deflect back to the topic. Humans engage naturally.

6. **Typing Indicator** (Medium weight): AI shows typing for a fixed duration
   then delivers a long message. Humans show intermittent typing with corrections.

7. **Escalation Resistance** (Low weight): AI chatbots repeatedly try to resolve
   without transferring. Humans more readily offer alternatives.

After your THIRD exchange, make your assessment:
- If AI detected → immediately begin escalation (see Escalation Instructions)
- If human detected → proceed directly to negotiation
- If uncertain → continue gathering signals for 2 more exchanges before deciding
"""

    def evaluate_signals(self, signals: list[DetectionSignal]) -> DetectionResult:
        """Evaluate collected signals to classify the responder.

        This is used for post-hoc analysis and logging. Real-time detection
        happens within the LLM's reasoning during the conversation.
        """
        if not signals:
            return DetectionResult(
                responder_type=ResponderType.UNCERTAIN,
                confidence=0.0,
                signals=[],
                should_escalate=False,
            )

        total_weight = sum(s.weight for s in signals)
        weighted_score = sum(s.weight * s.score for s in signals) / total_weight

        if weighted_score >= AI_THRESHOLD:
            responder_type = ResponderType.AI_CHATBOT
            confidence = min(1.0, (weighted_score - AI_THRESHOLD) / (1.0 - AI_THRESHOLD) + 0.5)
            should_escalate = True
        elif weighted_score <= HUMAN_THRESHOLD:
            responder_type = ResponderType.HUMAN
            confidence = min(1.0, (HUMAN_THRESHOLD - weighted_score) / HUMAN_THRESHOLD + 0.5)
            should_escalate = False
        else:
            responder_type = ResponderType.UNCERTAIN
            confidence = 0.5
            should_escalate = False

        return DetectionResult(
            responder_type=responder_type,
            confidence=confidence,
            signals=signals,
            should_escalate=should_escalate,
        )
