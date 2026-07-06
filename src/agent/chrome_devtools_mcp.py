"""Chrome DevTools MCP auto-connect client for existing Chrome sessions."""

from __future__ import annotations

import json
import os
import selectors
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Any

from src.agent.browser_runtime import normalize_cdp_url

REMOTE_DEBUGGING_HELP = (
    "Open chrome://inspect/#remote-debugging in Chrome and allow remote debugging, "
    "then try Auto-Connect Existing Chrome again."
)

DEFAULT_MCP_COMMAND = ["npx", "-y", "chrome-devtools-mcp@latest", "--autoConnect"]


class ChromeDevtoolsMcpError(RuntimeError):
    """Raised when the Chrome DevTools MCP bridge cannot complete a request."""


def permission_help_message(detail: str | None = None) -> str:
    """Return actionable setup guidance for Chrome DevTools MCP failures."""
    if detail:
        return f"{detail}. {REMOTE_DEBUGGING_HELP}"
    return REMOTE_DEBUGGING_HELP


@dataclass(frozen=True)
class ChromeMcpPage:
    """Safe metadata for one existing Chrome page reported by MCP."""

    index: int
    title: str
    url: str
    page_id: str | None = None
    cdp_url: str | None = None

    def as_payload(self) -> dict:
        return {
            "index": self.index,
            "id": self.page_id,
            "title": self.title,
            "url": self.url,
            "cdp_url": self.cdp_url,
        }


def cdp_url_from_mcp_page(page: dict) -> str | None:
    """Return a browser-use-compatible CDP URL if MCP page metadata exposes one."""
    for key in (
        "cdp_url",
        "cdpUrl",
        "browserUrl",
        "browser_url",
        "debuggerUrl",
        "debugger_url",
        "webSocketDebuggerUrl",
        "websocketDebuggerUrl",
    ):
        value = page.get(key)
        if isinstance(value, str) and value.strip():
            candidate = value.strip()
            if candidate.startswith("ws://") or candidate.startswith("wss://"):
                # Browser-use expects the HTTP CDP endpoint; a target WebSocket URL is
                # not enough unless the MCP server also reports its HTTP origin.
                continue
            try:
                return normalize_cdp_url(candidate)
            except ValueError:
                continue
    return None


def safe_page_payload(page: dict, index: int) -> dict:
    """Normalize MCP page data to safe dashboard metadata."""
    raw_index = page.get("index", page.get("pageIdx", index))
    try:
        page_index = int(raw_index)
    except (TypeError, ValueError):
        page_index = index
    page_id = page.get("id") or page.get("page_id") or page.get("targetId")
    safe_page = ChromeMcpPage(
        index=page_index,
        page_id=str(page_id) if page_id is not None else None,
        title=str(page.get("title") or page.get("name") or "Untitled tab"),
        url=str(page.get("url") or ""),
        cdp_url=cdp_url_from_mcp_page(page),
    )
    return safe_page.as_payload()


def parse_mcp_pages(result: Any) -> list[dict]:
    """Extract page metadata from structured or text MCP tool responses."""
    if isinstance(result, dict):
        for key in ("pages", "tabs", "items"):
            value = result.get(key)
            if isinstance(value, list):
                return [
                    safe_page_payload(item, i)
                    for i, item in enumerate(value)
                    if isinstance(item, dict)
                ]
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            pages = parse_mcp_pages(structured)
            if pages:
                return pages
        content = result.get("content")
        if isinstance(content, list):
            pages = _parse_pages_from_content(content)
            if pages:
                return pages
    if isinstance(result, list):
        return [
            safe_page_payload(item, i)
            for i, item in enumerate(result)
            if isinstance(item, dict)
        ]
    return []


def _parse_pages_from_content(content: list) -> list[dict]:
    pages: list[dict] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if not isinstance(text, str):
            continue
        parsed = _parse_pages_text(text)
        if parsed:
            pages.extend(parsed)
    return pages


def _parse_pages_text(text: str) -> list[dict]:
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        decoded = None
    if isinstance(decoded, list):
        return [
            safe_page_payload(item, i)
            for i, item in enumerate(decoded)
            if isinstance(item, dict)
        ]
    if isinstance(decoded, dict):
        pages = parse_mcp_pages(decoded)
        if pages:
            return pages

    pages: list[dict] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Common MCP list_pages text resembles: "0: Title - https://example.com".
        prefix, sep, rest = stripped.partition(":")
        if not sep or not prefix.strip().isdigit():
            continue
        title, url = _split_title_url(rest.strip())
        pages.append(
            safe_page_payload(
                {"index": int(prefix), "title": title, "url": url},
                len(pages),
            )
        )
    return pages


def _split_title_url(text: str) -> tuple[str, str]:
    marker_start = text.rfind("(http")
    if marker_start != -1:
        marker_end = text.find(")", marker_start)
        if marker_end != -1:
            title = text[:marker_start].strip()
            url = text[marker_start + 1 : marker_end].strip()
            suffix = text[marker_end + 1 :].strip()
            if suffix and not suffix.startswith("["):
                title = f"{title} {suffix}".strip()
            return title or "Untitled tab", url

    for delimiter in (" - http", " — http", " | http"):
        if delimiter in text:
            title, suffix = text.split(delimiter, 1)
            return title.strip() or "Untitled tab", f"http{suffix}".strip()
    if text.startswith("http://") or text.startswith("https://"):
        return "Untitled tab", text
    return text or "Untitled tab", ""


def summarize_mcp_error(exc: Exception) -> str:
    """Map low-level MCP failures to user-facing setup copy."""
    message = str(exc) or type(exc).__name__
    if "DevToolsActivePort" in message or "Could not connect to Chrome" in message:
        return permission_help_message(message)
    if isinstance(exc, FileNotFoundError) or "No such file" in message:
        return (
            "Could not start Chrome DevTools MCP because npx/Node was not found. "
            "Install Node.js, then try again."
        )
    return message


class ChromeDevtoolsMcpSession:
    """Persistent helper-owned Chrome DevTools MCP session."""

    def __init__(self, client: ChromeDevtoolsMcpClient | None = None):
        self._client = client
        self._lock = threading.RLock()
        self.selected_page: dict | None = None
        self.latest_snapshot: dict | None = None
        self._tools: list[dict] | None = None

    def connect(self) -> list[dict]:
        with self._lock:
            self._ensure_client()
            return self.list_pages()

    def list_tools(self) -> list[dict]:
        with self._lock:
            self._ensure_client()
            if self._tools is None:
                self._tools = self._client.list_tools() if self._client else []
            return list(self._tools)

    def list_pages(self) -> list[dict]:
        with self._lock:
            self._ensure_client()
            return self._client.list_pages() if self._client else []

    def select_page(self, page: dict) -> dict:
        with self._lock:
            self._ensure_client()
            snapshot = self._client.select_page(page) if self._client else {}
            self.selected_page = dict(page)
            self.latest_snapshot = snapshot
            return snapshot

    def take_snapshot(self) -> dict:
        with self._lock:
            self._ensure_client()
            snapshot = self._client.call_tool("take_snapshot", {}) if self._client else {}
            self.latest_snapshot = {
                "page": self.selected_page or {},
                "snapshot_text": _content_text(snapshot.get("content")),
                "snapshot": snapshot,
            }
            return self.latest_snapshot

    def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        with self._lock:
            self._ensure_client()
            return self._client.call_tool(name, arguments or {}) if self._client else {}

    def close(self) -> None:
        with self._lock:
            if self._client is not None:
                self._client.close()
            self._client = None
            self._tools = None
            self.selected_page = None
            self.latest_snapshot = None

    def _ensure_client(self) -> None:
        if self._client is None:
            self._client = ChromeDevtoolsMcpClient()
            self._client.start()


_default_mcp_session: ChromeDevtoolsMcpSession | None = None


def get_default_mcp_session() -> ChromeDevtoolsMcpSession:
    """Return the process-wide helper-owned Chrome DevTools MCP session."""
    global _default_mcp_session
    if _default_mcp_session is None:
        _default_mcp_session = ChromeDevtoolsMcpSession()
    return _default_mcp_session


def reset_default_mcp_session() -> None:
    """Close and clear the default MCP session for tests or shutdown."""
    global _default_mcp_session
    if _default_mcp_session is not None:
        _default_mcp_session.close()
    _default_mcp_session = None


class ChromeDevtoolsMcpClient:
    """Minimal stdio JSON-RPC client for chrome-devtools-mcp."""

    def __init__(
        self,
        command: list[str] | None = None,
        *,
        timeout_seconds: float = 60.0,
    ):
        self.command = command or list(DEFAULT_MCP_COMMAND)
        self.timeout_seconds = timeout_seconds
        self._process: subprocess.Popen | None = None
        self._next_id = 1
        self._buffer = b""

    def __enter__(self) -> ChromeDevtoolsMcpClient:
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def start(self) -> None:
        if self._process is not None:
            return
        self._process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "flyingpig", "version": "1.0.2"},
            },
        )
        self._notify("notifications/initialized", {})

    def list_tools(self) -> list[dict]:
        result = self._request("tools/list", {})
        tools = result.get("tools") if isinstance(result, dict) else None
        return tools if isinstance(tools, list) else []

    def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        result = self._request(
            "tools/call",
            {"name": name, "arguments": arguments or {}},
        )
        if not isinstance(result, dict):
            return {"content": result}
        if result.get("isError") is True:
            text = _content_text(result.get("content")) or f"MCP tool {name} failed"
            raise ChromeDevtoolsMcpError(text)
        return result

    def list_pages(self) -> list[dict]:
        return parse_mcp_pages(self.call_tool("list_pages"))

    def select_page(self, page: dict) -> dict:
        page_id = page.get("id") if page.get("id") is not None else page.get("index", 0)
        args = {"pageId": page_id, "bringToFront": False}
        self.call_tool("select_page", args)
        snapshot = self.call_tool("take_snapshot", {})
        return {
            "page": page,
            "snapshot_text": _content_text(snapshot.get("content")),
            "snapshot": snapshot,
        }

    def close(self) -> None:
        process = self._process
        self._process = None
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)

    def _request(self, method: str, params: dict | None) -> Any:
        request_id = self._next_id
        self._next_id += 1
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}})
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            message = self._read_message(deadline)
            if message is None:
                continue
            if message.get("id") != request_id:
                continue
            if "error" in message:
                error = message["error"]
                detail = error.get("message") if isinstance(error, dict) else str(error)
                raise ChromeDevtoolsMcpError(detail)
            return message.get("result")
        stderr = self._read_stderr()
        detail = f"Timed out waiting for Chrome DevTools MCP response to {method}"
        if stderr:
            detail = f"{detail}: {stderr}"
        raise ChromeDevtoolsMcpError(detail)

    def _notify(self, method: str, params: dict | None) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def _send(self, payload: dict) -> None:
        process = self._require_process()
        # The MCP stdio transport uses newline-delimited JSON-RPC messages.
        # Keep the parser below tolerant of LSP-style Content-Length frames in
        # case another MCP server implementation uses that framing.
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"
        assert process.stdin is not None
        process.stdin.write(body)
        process.stdin.flush()

    def _read_message(self, deadline: float) -> dict | None:
        while time.monotonic() < deadline:
            parsed = self._pop_message()
            if parsed is not None:
                return parsed
            remaining = max(0.0, deadline - time.monotonic())
            self._read_stdout_chunk(min(remaining, 0.25))
        return None

    def _pop_message(self) -> dict | None:
        if not self._buffer.startswith(b"Content-Length:"):
            newline = self._buffer.find(b"\n")
            if newline != -1:
                line = self._buffer[:newline].strip()
                self._buffer = self._buffer[newline + 1 :]
                if not line:
                    return None
                return json.loads(line.decode("utf-8"))

        for delimiter in (b"\r\n\r\n", b"\n\n"):
            header_end = self._buffer.find(delimiter)
            if header_end == -1:
                continue
            header = self._buffer[:header_end].decode("ascii", errors="replace")
            length = None
            for line in header.splitlines():
                name, sep, value = line.partition(":")
                if sep and name.lower() == "content-length":
                    length = int(value.strip())
                    break
            if length is None:
                self._buffer = self._buffer[header_end + len(delimiter) :]
                return None
            body_start = header_end + len(delimiter)
            body_end = body_start + length
            if len(self._buffer) < body_end:
                return None
            body = self._buffer[body_start:body_end]
            self._buffer = self._buffer[body_end:]
            return json.loads(body.decode("utf-8"))
        return None

    def _read_stdout_chunk(self, timeout: float) -> None:
        process = self._require_process()
        if process.poll() is not None:
            stderr = self._read_stderr()
            raise ChromeDevtoolsMcpError(
                f"Chrome DevTools MCP exited with code {process.returncode}: {stderr}"
            )
        assert process.stdout is not None
        selector = selectors.DefaultSelector()
        try:
            selector.register(process.stdout, selectors.EVENT_READ)
            if not selector.select(timeout):
                return
            chunk = os.read(process.stdout.fileno(), 65536)
            if not chunk:
                return
            self._buffer += chunk
        finally:
            selector.close()

    def _read_stderr(self) -> str:
        process = self._process
        if process is None or process.stderr is None:
            return ""
        try:
            selector = selectors.DefaultSelector()
            selector.register(process.stderr, selectors.EVENT_READ)
            if not selector.select(0):
                return ""
            chunk = os.read(process.stderr.fileno(), 65536)
            return chunk.decode("utf-8", errors="replace").strip()
        except Exception:
            return ""
        finally:
            try:
                selector.close()
            except Exception:
                pass

    def _require_process(self) -> subprocess.Popen:
        if self._process is None:
            raise ChromeDevtoolsMcpError("Chrome DevTools MCP is not started")
        return self._process


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    chunks = []
    for item in content:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            chunks.append(item["text"])
    return "\n".join(chunks)
