from __future__ import annotations

import pytest
from src.agent.chrome_devtools_mcp import (
    ChromeDevtoolsMcpClient,
    ChromeDevtoolsMcpError,
    cdp_url_from_mcp_page,
    chrome_devtools_mcp_command,
    parse_mcp_pages,
    summarize_mcp_error,
)


def test_parse_mcp_pages_from_structured_content():
    pages = parse_mcp_pages(
        {
            "structuredContent": {
                "pages": [
                    {
                        "index": 2,
                        "id": "target-2",
                        "title": "CPA Management Center",
                        "url": "https://cpa.example/dashboard",
                        "browserUrl": "localhost:9335",
                    }
                ]
            }
        }
    )

    assert pages == [
        {
            "index": 2,
            "id": "target-2",
            "title": "CPA Management Center",
            "url": "https://cpa.example/dashboard",
            "cdp_url": "http://localhost:9335",
        }
    ]


def test_parse_mcp_pages_from_text_lines():
    pages = parse_mcp_pages(
        {
            "content": [
                {
                    "type": "text",
                    "text": "0: Linear - https://linear.app/acme\n1: New Tab - chrome://newtab",
                }
            ]
        }
    )

    assert pages[0]["index"] == 0
    assert pages[0]["title"] == "Linear"
    assert pages[0]["url"] == "https://linear.app/acme"
    assert pages[1]["title"] == "New Tab - chrome://newtab"


def test_cdp_url_from_mcp_page_ignores_target_websocket():
    assert (
        cdp_url_from_mcp_page(
            {"webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/page/abc"}
        )
        is None
    )
    assert cdp_url_from_mcp_page({"cdpUrl": "http://[::1]:9222/json/version"}) == (
        "http://[::1]:9222"
    )


def test_mcp_error_mentions_remote_debugging_permission():
    message = summarize_mcp_error(
        ChromeDevtoolsMcpError(
            "Could not connect to Chrome. Could not find DevToolsActivePort"
        )
    )

    assert "chrome://inspect/#remote-debugging" in message
    assert "allow remote debugging" in message


class FakeRpcClient(ChromeDevtoolsMcpClient):
    def __init__(self):
        super().__init__(command=["fake"])
        self.requests = []

    def _request(self, method, params):
        self.requests.append((method, params))
        if method == "tools/call":
            return {"content": [{"type": "text", "text": "[]"}]}
        return {}


def test_call_tool_uses_mcp_tools_call_shape():
    client = FakeRpcClient()

    client.call_tool("list_pages", {"include": "tabs"})

    assert client.requests == [
        (
            "tools/call",
            {"name": "list_pages", "arguments": {"include": "tabs"}},
        )
    ]

def test_call_tool_raises_mcp_tool_errors():
    class ErrorClient(FakeRpcClient):
        def _request(self, method, params):
            return {"isError": True, "content": [{"type": "text", "text": "boom"}]}

    with pytest.raises(ChromeDevtoolsMcpError, match="boom"):
        ErrorClient().call_tool("list_pages")


def test_chrome_devtools_mcp_command_uses_override(monkeypatch):
    monkeypatch.setenv(
        "FLYINGPIG_CHROME_MCP_COMMAND",
        "/custom/npx -y chrome-devtools-mcp@latest --autoConnect",
    )

    assert chrome_devtools_mcp_command() == [
        "/custom/npx",
        "-y",
        "chrome-devtools-mcp@latest",
        "--autoConnect",
    ]
