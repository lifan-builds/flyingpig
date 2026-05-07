"""Tests for AI chatbot detection module."""

from src.agent.detector import (
    ChatbotDetector,
    DetectionSignal,
    ResponderType,
)


class TestChatbotDetector:
    def setup_method(self):
        self.detector = ChatbotDetector()

    def test_empty_signals_returns_uncertain(self):
        result = self.detector.evaluate_signals([])
        assert result.responder_type == ResponderType.UNCERTAIN
        assert result.confidence == 0.0
        assert result.should_escalate is False

    def test_strong_ai_signals_detected(self):
        signals = [
            DetectionSignal("latency", weight=3.0, score=0.9, evidence="<1s response"),
            DetectionSignal("structure", weight=3.0, score=0.8, evidence="templated greeting"),
            DetectionSignal("flexibility", weight=3.0, score=0.9, evidence="deflected off-topic"),
        ]
        result = self.detector.evaluate_signals(signals)
        assert result.responder_type == ResponderType.AI_CHATBOT
        assert result.confidence > 0.5
        assert result.should_escalate is True

    def test_strong_human_signals_detected(self):
        signals = [
            DetectionSignal("latency", weight=3.0, score=0.1, evidence="15s variable delay"),
            DetectionSignal("structure", weight=3.0, score=0.2, evidence="casual with typos"),
            DetectionSignal("flexibility", weight=3.0, score=0.1, evidence="engaged naturally"),
        ]
        result = self.detector.evaluate_signals(signals)
        assert result.responder_type == ResponderType.HUMAN
        assert result.confidence > 0.5
        assert result.should_escalate is False

    def test_mixed_signals_uncertain(self):
        signals = [
            DetectionSignal("latency", weight=3.0, score=0.6, evidence="moderate delay"),
            DetectionSignal("structure", weight=3.0, score=0.4, evidence="mixed formatting"),
            DetectionSignal("flexibility", weight=3.0, score=0.5, evidence="partial engagement"),
        ]
        result = self.detector.evaluate_signals(signals)
        assert result.responder_type == ResponderType.UNCERTAIN
        assert result.should_escalate is False

    def test_instructions_contain_key_signals(self):
        instructions = self.detector.get_instructions()
        assert "Response Latency" in instructions
        assert "Message Structure" in instructions
        assert "Flexibility Test" in instructions
        assert "Typing Indicator" in instructions
        assert "THIRD exchange" in instructions

    def test_weight_matters(self):
        # High-weight AI signal + low-weight human signal = AI
        signals = [
            DetectionSignal("latency", weight=5.0, score=0.9, evidence="instant"),
            DetectionSignal(
                "escalation_resistance", weight=0.5, score=0.1, evidence="offered transfer"
            ),
        ]
        result = self.detector.evaluate_signals(signals)
        assert result.responder_type == ResponderType.AI_CHATBOT


class TestEscalationManager:
    def test_instructions_contain_all_strategies(self):
        from src.agent.escalator import EscalationManager

        mgr = EscalationManager()
        instructions = mgr.get_instructions()
        assert "Strategy 1: Direct Request" in instructions
        assert "Strategy 2: Complexity Escalation" in instructions
        assert "Strategy 3: Keyword Triggers" in instructions
        assert "Strategy 4: Dissatisfaction Signal" in instructions
        assert "Strategy 5: Channel Switch" in instructions
        assert "NEVER be rude" in instructions
        assert "Maximum 5 escalation attempts" in instructions


class TestBrainCustomTools:
    def test_build_tools_creates_registry(self):
        from src.agent.brain import _build_tools

        tools = _build_tools()
        # Tools should have our custom actions registered
        assert tools is not None
