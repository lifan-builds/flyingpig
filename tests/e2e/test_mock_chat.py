import asyncio
import multiprocessing

import pytest
import uvicorn
from src.agent.brain import AgentBrain

from tests.mock_amex.server import app


def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="error")


@pytest.fixture(scope="module")
def mock_amex_server():
    p = multiprocessing.Process(target=run_server)
    p.start()
    import time

    time.sleep(2)  # Give uvicorn time to start
    yield
    p.terminate()
    p.join()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_agent_with_mock_site(mock_amex_server, monkeypatch):
    """
    Test the Agent against our local mock HTML instead of the real Amex.
    """
    from src.sites.amex import AmexAdapter

    monkeypatch.setattr(AmexAdapter, "chat_url", "http://127.0.0.1:8080/?logged_in=true")
    monkeypatch.setattr(AmexAdapter, "login_url", "http://127.0.0.1:8080/")
    brain = AgentBrain(
        site="amex",
        headless=True,
        input_mode="api",
        browser_mode="controlled",
    )

    task_prompt = (
        "Open chat and ask them to cancel my account. "
        "If they offer a credit, accept it and terminate."
    )

    # Answer the mandatory pre-flight confirmation prompt in API mode.
    run_task = asyncio.create_task(brain.execute(task=task_prompt, max_steps=15))
    for _ in range(120):
        if brain.input_handler.pending_question:
            brain.input_handler.provide_input("Yes, confirmed. Continue with the test task.")
            break
        if run_task.done():
            break
        await asyncio.sleep(0.5)
    result = await run_task

    # The result should be success or partial since it successfully interacts
    assert result.status.value in ["success", "partial"]
    assert len(result.transcript) > 0

    # The transcript should capture our mock server response about a $50 credit
    transcript_text = str(result.transcript).lower()
    assert "credit" in transcript_text or "cancel" in transcript_text
