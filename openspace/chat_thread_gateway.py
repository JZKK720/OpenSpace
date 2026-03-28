from __future__ import annotations

import json
from typing import Any, Dict, List
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


class ChatThreadGatewayError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 502, details: Any | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details


def submit_chat_thread_handoff(
    agent: Dict[str, Any],
    *,
    prompt: str,
    thread_id: str | None = None,
    timezone: str = "UTC",
    history_limit: int = 10,
) -> Dict[str, Any]:
    cleaned_prompt = str(prompt or "").strip()
    if not cleaned_prompt:
        raise ChatThreadGatewayError("prompt is required", status_code=400)

    action_url = str(agent.get("actionUrl") or "").strip()
    if not action_url:
        raise ChatThreadGatewayError("Chat-thread action URL is not configured", status_code=400)

    cleaned_thread_id = str(thread_id or "").strip() or None
    thread_created = False
    action_auth_token = _resolve_auth_token(agent, "action")
    action_headers = _resolve_headers(agent, "action")
    if not cleaned_thread_id:
        thread_payload = _request_json(
            _build_chat_url(action_url, "/api/chat/thread/new"),
            method="POST",
            auth_token=action_auth_token,
            headers=action_headers,
        )
        cleaned_thread_id = str(thread_payload.get("id") or "").strip()
        if not cleaned_thread_id:
            raise ChatThreadGatewayError("Chat-thread runtime did not return a thread id", details=thread_payload)
        thread_created = True

    send_payload = {
        "content": cleaned_prompt,
        "thread_id": cleaned_thread_id,
        "timezone": str(timezone or "UTC"),
    }
    send_response = _request_json(
        action_url,
        method="POST",
        payload=send_payload,
        auth_token=action_auth_token,
        headers=action_headers,
    )
    history = get_chat_thread_history(agent, thread_id=cleaned_thread_id, limit=history_limit)

    return {
        "agentId": str(agent.get("id") or "external-agent"),
        "threadId": cleaned_thread_id,
        "threadCreated": thread_created,
        "messageId": str(send_response.get("message_id") or ""),
        "status": str(send_response.get("status") or "accepted"),
        "actionUrl": action_url,
        **history,
    }


def get_chat_thread_history(
    agent: Dict[str, Any],
    *,
    thread_id: str,
    limit: int = 10,
) -> Dict[str, Any]:
    cleaned_thread_id = str(thread_id or "").strip()
    if not cleaned_thread_id:
        raise ChatThreadGatewayError("thread_id is required", status_code=400)

    action_url = str(agent.get("actionUrl") or "").strip()
    if not action_url:
        raise ChatThreadGatewayError("Chat-thread action URL is not configured", status_code=400)

    query = urlencode({"limit": max(1, min(int(limit), 100)), "thread_id": cleaned_thread_id})
    history_response = _request_json(
        _build_chat_url(action_url, "/api/chat/history", query=query),
        method="GET",
        auth_token=_resolve_auth_token(agent, "history") or _resolve_auth_token(agent, "action"),
        headers=_resolve_headers(agent, "history") or _resolve_headers(agent, "action"),
    )
    raw_turns = history_response.get("turns")
    turns: List[Dict[str, Any]] = [turn for turn in raw_turns if isinstance(turn, dict)] if isinstance(raw_turns, list) else []

    return {
        "agentId": str(agent.get("id") or "external-agent"),
        "threadId": str(history_response.get("thread_id") or cleaned_thread_id),
        "hasMore": bool(history_response.get("has_more")),
        "turns": turns,
        "latestTurn": _select_latest_turn(turns),
    }


def _select_latest_turn(turns: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    best_turn: Dict[str, Any] | None = None
    best_turn_number = -1

    for turn in turns:
        if not isinstance(turn, dict):
            continue
        turn_number = turn.get("turn_number")
        if isinstance(turn_number, int) and turn_number >= best_turn_number:
            best_turn = turn
            best_turn_number = turn_number
        elif best_turn is None:
            best_turn = turn

    return best_turn


def _build_chat_url(action_url: str, path: str, *, query: str = "") -> str:
    parsed = urlsplit(action_url)
    if not parsed.scheme or not parsed.netloc:
        raise ChatThreadGatewayError(f"Invalid action URL: {action_url}", status_code=400)

    base_path = parsed.path or ""
    if base_path.endswith("/api/chat/send"):
        base_path = base_path[: -len("/api/chat/send")]
    else:
        base_path = ""

    target_path = f"{base_path}{path}" if path.startswith("/") else f"{base_path}/{path}"
    return urlunsplit((parsed.scheme, parsed.netloc, target_path, query, ""))


def _request_json(
    url: str,
    *,
    method: str,
    payload: Dict[str, Any] | None = None,
    auth_token: str | None = None,
    headers: Dict[str, str] | None = None,
    timeout: float = 20.0,
) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request_headers = {
        "User-Agent": "OpenSpaceExternalGateway/1.0",
        "Accept": "application/json",
    }
    if headers:
        request_headers.update(headers)
    if auth_token:
        request_headers.setdefault("Authorization", f"Bearer {auth_token}")
    if body is not None:
        request_headers.setdefault("Content-Type", "application/json")

    request = Request(url, data=body, method=method.upper(), headers=request_headers)

    try:
        with urlopen(request, timeout=timeout) as response:
            raw_body = response.read().decode("utf-8")
    except HTTPError as exc:
        raw_body = exc.read().decode("utf-8", errors="replace")
        details = _decode_json(raw_body)
        status_code = int(getattr(exc, "code", 0) or 0) or 502
        message = _extract_error_message(details) or f"Chat-thread request failed with HTTP {status_code}"
        raise ChatThreadGatewayError(message, status_code=status_code, details=details) from exc
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise ChatThreadGatewayError(f"Chat-thread request failed: {exc}", status_code=502) from exc

    details = _decode_json(raw_body)
    if not isinstance(details, dict):
        raise ChatThreadGatewayError("Chat-thread runtime returned an invalid JSON payload", details=raw_body)
    return details


def _decode_json(raw_body: str) -> Any:
    try:
        return json.loads(raw_body)
    except json.JSONDecodeError:
        return raw_body


def _extract_error_message(details: Any) -> str | None:
    if isinstance(details, dict):
        for key in ("error", "message", "detail"):
            value = details.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    if isinstance(details, str) and details.strip():
        return details.strip()
    return None


def _resolve_auth_token(agent: Dict[str, Any], kind: str) -> str | None:
    if kind == "history":
        value = str(agent.get("_historyAuthToken") or "").strip()
        if value:
            return value
    return str(agent.get("_actionAuthToken") or "").strip() or None


def _resolve_headers(agent: Dict[str, Any], kind: str) -> Dict[str, str] | None:
    raw_headers = agent.get("_historyHeaders") if kind == "history" else agent.get("_actionHeaders")
    if not isinstance(raw_headers, dict):
        return None
    return {
        str(key): str(value)
        for key, value in raw_headers.items()
        if str(key).strip() and value is not None
    }