"""
OpenAI-compatible client for nanobot's ``nanobot serve`` HTTP API.

Chat protocol (nanobot serve exposes):
  POST {base}/v1/chat/completions
       body: {"messages": [{"role":"user","content":"<text>"}],
              "session_id": "<id>"}   (custom nanobot extension)
       response: standard OpenAI chat-completion object

Health check:
  GET {base}/health 鈫?{"status": "ok"}
  GET {base}/v1/models 鈫?{"object":"list","data":[...]}

Uses only Python stdlib + threading 鈥?no httpx/requests (dashboard image is minimal).
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class NanobotGatewayError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


# 鈹€鈹€ In-process session store 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

_sessions: Dict[str, "_NanobotSession"] = {}
_sessions_lock = threading.Lock()
_SESSION_TTL_SECONDS = 3600  # 1 hour idle TTL


class _NanobotSession:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.turns: List[Dict[str, Any]] = []
        self.last_used: float = time.monotonic()

    def touch(self) -> None:
        self.last_used = time.monotonic()


def _get_or_create_session(thread_id: Optional[str]) -> "_NanobotSession":
    if thread_id:
        with _sessions_lock:
            session = _sessions.get(thread_id)
        if session is not None:
            session.touch()
            return session
    session_id = thread_id or str(uuid.uuid4())
    session = _NanobotSession(session_id)
    with _sessions_lock:
        _sessions[session_id] = session
    return session


# 鈹€鈹€ HTTP helper 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

def _post_json(
    url: str,
    payload: Dict[str, Any],
    *,
    timeout: float = 90.0,
) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "OpenSpaceNanobotBridge/1.0",
    }
    req = Request(url, data=body, method="POST", headers=headers)
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace").strip()
            if not raw:
                return {}
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {}
    except HTTPError as exc:
        body_text = ""
        try:
            body_text = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        raise NanobotGatewayError(
            f"Nanobot API error HTTP {exc.code}: {body_text or exc.reason}",
            status_code=exc.code,
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise NanobotGatewayError(
            f"Nanobot connection error: {exc}", status_code=502
        ) from exc


# 鈹€鈹€ Public API 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

def send_message(
    base_url: str,
    user_text: str,
    *,
    thread_id: Optional[str] = None,
    timeout: float = 90.0,
) -> Dict[str, Any]:
    """Send *user_text* to nanobot and return a handoff response dict.

    Calls nanobot's OpenAI-compatible ``POST /v1/chat/completions`` endpoint.
    Nanobot v0.1.4+ maintains server-side conversation history keyed by
    ``session_id``, so only the current user message is sent each turn.
    """
    base = base_url.rstrip("/")
    session = _get_or_create_session(thread_id)
    session.touch()

    payload: Dict[str, Any] = {
        "messages": [{"role": "user", "content": user_text}],
        "session_id": session.session_id,
    }
    result = _post_json(f"{base}/v1/chat/completions", payload, timeout=timeout)

    # Extract assistant text from OpenAI-compatible response
    response_text: Optional[str] = None
    try:
        choices = result.get("choices") or []
        if choices:
            response_text = str(choices[0]["message"]["content"] or "").strip() or None
    except (KeyError, IndexError, TypeError):
        pass

    turn_number = len(session.turns) + 1
    turn: Dict[str, Any] = {
        "turn_number": turn_number,
        "user_input": user_text,
        "response": response_text,
        "state": "completed",
        "started_at": None,
        "completed_at": None,
        "tool_calls": [],
    }
    session.turns.append(turn)

    return {
        "agentId": "nanobot",
        "threadId": session.session_id,
        "threadCreated": thread_id != session.session_id,
        "messageId": str(result.get("id") or ""),
        "status": "completed",
        "actionUrl": f"{base}/v1/chat/completions",
        "hasMore": False,
        "turns": list(session.turns),
        "latestTurn": turn,
    }


def get_history(thread_id: str) -> Dict[str, Any]:
    """Return stored turns for an existing session."""
    with _sessions_lock:
        session = _sessions.get(thread_id)
    if session is None:
        return {
            "agentId": "nanobot",
            "threadId": thread_id,
            "hasMore": False,
            "turns": [],
            "latestTurn": None,
        }
    session.touch()
    latest = session.turns[-1] if session.turns else None
    return {
        "agentId": "nanobot",
        "threadId": session.session_id,
        "hasMore": False,
        "turns": list(session.turns),
        "latestTurn": latest,
    }


def cleanup_expired() -> None:
    """Evict sessions idle longer than SESSION_TTL_SECONDS."""
    cutoff = time.monotonic() - _SESSION_TTL_SECONDS
    with _sessions_lock:
        expired = [sid for sid, s in _sessions.items() if s.last_used < cutoff]
        for sid in expired:
            del _sessions[sid]
