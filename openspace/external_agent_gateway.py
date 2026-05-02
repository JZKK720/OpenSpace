from __future__ import annotations

from abc import ABC, abstractmethod
import json
from pathlib import Path
from tempfile import gettempdir
from threading import Lock
from typing import Any, Dict, List
from uuid import uuid4
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from openspace.chat_thread_gateway import (
    ChatThreadGatewayError,
    get_chat_thread_history,
    submit_chat_thread_handoff,
)
from openspace import nanobot_gateway as _nanobot


class ExternalAgentGatewayError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 502, details: Any | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details


_OPENCLAW_HISTORY_STORE_PATH = Path(gettempdir()) / "openspace_openclaw_history.json"
_OPENCLAW_HISTORY_MAX_TURNS = 200
_OPENCLAW_HISTORY_LOCK = Lock()
_OPENCLAW_HISTORY_CACHE: Dict[str, Dict[str, List[Dict[str, Any]]]] | None = None


class ExternalAgentAdapter(ABC):
    protocol_ids: tuple[str, ...] = ()

    def matches(self, protocol: str) -> bool:
        return protocol.strip().lower() in self.protocol_ids

    @abstractmethod
    def handoff(
        self,
        agent: Dict[str, Any],
        *,
        prompt: str,
        thread_id: str | None = None,
        timezone: str = "UTC",
        history_limit: int = 10,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def history(
        self,
        agent: Dict[str, Any],
        *,
        thread_id: str,
        limit: int = 10,
    ) -> Dict[str, Any]:
        raise NotImplementedError


def _new_openclaw_thread_id() -> str:
    return f"openspace:openclaw:{uuid4().hex}"


def _normalize_openclaw_history_cache(raw: Any) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    cache: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    if not isinstance(raw, dict):
        return cache

    for agent_id, threads in raw.items():
        if not isinstance(agent_id, str) or not isinstance(threads, dict):
            continue
        normalized_threads: Dict[str, List[Dict[str, Any]]] = {}
        for thread_id, turns in threads.items():
            if not isinstance(thread_id, str) or not isinstance(turns, list):
                continue
            normalized_turns = [dict(turn) for turn in turns if isinstance(turn, dict)]
            if normalized_turns:
                normalized_threads[thread_id] = normalized_turns
        if normalized_threads:
            cache[agent_id] = normalized_threads
    return cache


def _ensure_openclaw_history_cache_locked() -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    global _OPENCLAW_HISTORY_CACHE

    if _OPENCLAW_HISTORY_CACHE is not None:
        return _OPENCLAW_HISTORY_CACHE

    try:
        raw = _OPENCLAW_HISTORY_STORE_PATH.read_text(encoding="utf-8")
    except OSError:
        _OPENCLAW_HISTORY_CACHE = {}
        return _OPENCLAW_HISTORY_CACHE

    _OPENCLAW_HISTORY_CACHE = _normalize_openclaw_history_cache(_decode_json(raw))
    return _OPENCLAW_HISTORY_CACHE


def _save_openclaw_history_cache_locked(cache: Dict[str, Dict[str, List[Dict[str, Any]]]]) -> None:
    try:
        temp_path = _OPENCLAW_HISTORY_STORE_PATH.with_suffix(".tmp")
        temp_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        temp_path.replace(_OPENCLAW_HISTORY_STORE_PATH)
    except OSError:
        pass


def _build_completed_turn(prompt: str, reply: str, *, turn_number: int) -> Dict[str, Any]:
    return {
        "turn_number": turn_number,
        "user_input": prompt,
        "response": reply,
        "state": "completed",
        "started_at": None,
        "completed_at": None,
        "tool_calls": [],
    }


def _record_openclaw_turn(agent_id: str, thread_id: str, *, prompt: str, reply: str) -> Dict[str, Any]:
    with _OPENCLAW_HISTORY_LOCK:
        cache = _ensure_openclaw_history_cache_locked()
        thread_turns = cache.setdefault(agent_id, {}).setdefault(thread_id, [])
        thread_turns.append(_build_completed_turn(prompt, reply, turn_number=len(thread_turns) + 1))
        if len(thread_turns) > _OPENCLAW_HISTORY_MAX_TURNS:
            del thread_turns[:-_OPENCLAW_HISTORY_MAX_TURNS]
        for index, turn in enumerate(thread_turns, start=1):
            turn["turn_number"] = index
        _save_openclaw_history_cache_locked(cache)
        return dict(thread_turns[-1])


def _read_openclaw_history(agent_id: str, thread_id: str, *, limit: int) -> Dict[str, Any]:
    with _OPENCLAW_HISTORY_LOCK:
        cache = _ensure_openclaw_history_cache_locked()
        turns = [
            dict(turn)
            for turn in cache.get(agent_id, {}).get(thread_id, [])
            if isinstance(turn, dict)
        ]

    if not turns:
        raise ExternalAgentGatewayError(
            (
                f"No mirrored history is available for OpenClaw thread '{thread_id}'. "
                "Only turns initiated through this OpenSpace instance can be refreshed."
            ),
            status_code=404,
        )

    safe_limit = max(1, min(int(limit), 100))
    selected_turns = turns[-safe_limit:]
    return {
        "hasMore": len(turns) > len(selected_turns),
        "turns": selected_turns,
        "latestTurn": dict(selected_turns[-1]),
    }


def _build_openclaw_messages(agent_id: str, thread_id: str | None, prompt: str) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []
    cleaned_thread_id = str(thread_id or "").strip()
    if cleaned_thread_id:
        with _OPENCLAW_HISTORY_LOCK:
            cache = _ensure_openclaw_history_cache_locked()
            prior_turns = [
                dict(turn)
                for turn in cache.get(agent_id, {}).get(cleaned_thread_id, [])
                if isinstance(turn, dict)
            ]
        for turn in prior_turns:
            user_input = str(turn.get("user_input") or "").strip()
            response = str(turn.get("response") or "").strip()
            if user_input:
                messages.append({"role": "user", "content": user_input})
            if response:
                messages.append({"role": "assistant", "content": response})
    messages.append({"role": "user", "content": prompt})
    return messages


def _extract_openai_message_content(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts: List[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                parts.append(item.strip())
                continue
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
        return "\n".join(parts).strip()
    return _stringify_content(value)


def _extract_openai_compat_reply(response: Dict[str, Any]) -> str:
    choices = response.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message") or {}
            if isinstance(message, dict):
                return _extract_openai_message_content(message.get("content"))
    return ""


class ChatThreadAdapter(ExternalAgentAdapter):
    protocol_ids = ("chat-thread", "threaded-chat")

    def handoff(
        self,
        agent: Dict[str, Any],
        *,
        prompt: str,
        thread_id: str | None = None,
        timezone: str = "UTC",
        history_limit: int = 10,
    ) -> Dict[str, Any]:
        try:
            return submit_chat_thread_handoff(
                agent,
                prompt=prompt,
                thread_id=thread_id,
                timezone=timezone,
                history_limit=history_limit,
            )
        except ChatThreadGatewayError as exc:
            raise ExternalAgentGatewayError(
                str(exc),
                status_code=exc.status_code,
                details=exc.details,
            ) from exc

    def history(
        self,
        agent: Dict[str, Any],
        *,
        thread_id: str,
        limit: int = 10,
    ) -> Dict[str, Any]:
        try:
            return get_chat_thread_history(agent, thread_id=thread_id, limit=limit)
        except ChatThreadGatewayError as exc:
            raise ExternalAgentGatewayError(
                str(exc),
                status_code=exc.status_code,
                details=exc.details,
            ) from exc


class HttpJsonAdapter(ExternalAgentAdapter):
    protocol_ids = ("http-json", "json-http", "request-response-json")

    def handoff(
        self,
        agent: Dict[str, Any],
        *,
        prompt: str,
        thread_id: str | None = None,
        timezone: str = "UTC",
        history_limit: int = 10,
    ) -> Dict[str, Any]:
        action_url = str(agent.get("actionUrl") or "").strip()
        if not action_url:
            raise ExternalAgentGatewayError("External agent action URL is not configured", status_code=400)

        field_map = _field_map(agent.get("_requestFieldMap"))
        payload: Dict[str, Any] = {}
        payload[field_map.get("prompt", "prompt")] = prompt
        if thread_id:
            payload[field_map.get("threadId", "thread_id")] = thread_id
        if timezone:
            payload[field_map.get("timezone", "timezone")] = timezone

        response = _request_json(
            action_url,
            method="POST",
            payload=payload,
            auth_token=str(agent.get("_actionAuthToken") or "").strip() or None,
            headers=_headers(agent.get("_actionHeaders")),
        )

        response_map = _field_map(agent.get("_responseFieldMap"))
        resolved_thread_id = str(
            _dig(response, response_map.get("threadId", "thread_id"))
            or thread_id
            or ""
        ).strip()
        status = str(
            _dig(response, response_map.get("status", "status"))
            or "completed"
        ).strip() or "completed"
        latest_response = _stringify_content(
            _dig(response, response_map.get("response", "response"))
        )
        latest_turn = {
            "turn_number": 1,
            "user_input": prompt,
            "response": latest_response,
            "state": status,
            "started_at": None,
            "completed_at": None,
            "tool_calls": [],
        }

        return {
            "agentId": str(agent.get("id") or "external-agent"),
            "threadId": resolved_thread_id,
            "threadCreated": bool(resolved_thread_id and resolved_thread_id != str(thread_id or "").strip()),
            "messageId": str(_dig(response, response_map.get("messageId", "message_id")) or ""),
            "status": status,
            "actionUrl": action_url,
            "hasMore": False,
            "turns": [latest_turn],
            "latestTurn": latest_turn,
        }

    def history(
        self,
        agent: Dict[str, Any],
        *,
        thread_id: str,
        limit: int = 10,
    ) -> Dict[str, Any]:
        history_url = str(agent.get("historyUrl") or "").strip()
        if not history_url:
            raise ExternalAgentGatewayError(
                f"External agent '{agent.get('id')}' does not define a history URL",
                status_code=400,
            )

        request_map = _field_map(agent.get("_historyRequestFieldMap"))
        query = urlencode({
            request_map.get("threadId", "thread_id"): thread_id,
            request_map.get("limit", "limit"): max(1, min(int(limit), 100)),
        })
        separator = "&" if "?" in history_url else "?"
        response = _request_json(
            f"{history_url}{separator}{query}",
            method="GET",
            auth_token=str(agent.get("_historyAuthToken") or "").strip() or None,
            headers=_headers(agent.get("_historyHeaders")),
        )

        response_map = _field_map(agent.get("_historyResponseFieldMap") or agent.get("_responseFieldMap"))
        turns = _dig(response, response_map.get("turns", "turns"))
        if not isinstance(turns, list):
            turns = []
        latest_turn = _dig(response, response_map.get("latestTurn", "latestTurn"))
        if not isinstance(latest_turn, dict):
            latest_turn = _select_latest_turn(turns)

        return {
            "agentId": str(agent.get("id") or "external-agent"),
            "threadId": str(_dig(response, response_map.get("threadId", "thread_id")) or thread_id),
            "hasMore": bool(_dig(response, response_map.get("hasMore", "has_more"))),
            "turns": turns,
            "latestTurn": latest_turn,
        }


class NanobotAdapter(ExternalAgentAdapter):
    """Adapter for nanobot's OpenAI-compatible serve API (nanobot serve)."""

    protocol_ids = ("nanobot-mcp",)

    def handoff(
        self,
        agent: Dict[str, Any],
        *,
        prompt: str,
        thread_id: str | None = None,
        timezone: str = "UTC",
        history_limit: int = 10,
    ) -> Dict[str, Any]:
        action_url = str(agent.get("actionUrl") or "").strip()
        if not action_url:
            raise ExternalAgentGatewayError(
                "Nanobot action URL is not configured", status_code=400
            )
        # Derive base URL by stripping known API path suffixes
        base_url = action_url
        for suffix in ("/v1/chat/completions", "/v1/chat", "/v1", "/mcp/chat", "/mcp"):
            if base_url.rstrip("/").endswith(suffix):
                base_url = base_url.rstrip("/")[: -len(suffix)]
                break
        try:
            return _nanobot.send_message(
                base_url,
                prompt,
                thread_id=thread_id or None,
                timeout=90.0,
            )
        except _nanobot.NanobotGatewayError as exc:
            raise ExternalAgentGatewayError(
                str(exc), status_code=exc.status_code
            ) from exc

    def history(
        self,
        agent: Dict[str, Any],
        *,
        thread_id: str,
        limit: int = 10,
    ) -> Dict[str, Any]:
        try:
            return _nanobot.get_history(thread_id)
        except _nanobot.NanobotGatewayError as exc:
            raise ExternalAgentGatewayError(
                str(exc), status_code=exc.status_code
            ) from exc


class OpenClawGatewayAdapter(ExternalAgentAdapter):
    """Adapter for OpenClaw's OpenAI-compatible HTTP endpoint with OpenSpace-managed thread history."""

    protocol_ids = ("openclaw-gateway",)

    def handoff(
        self,
        agent: Dict[str, Any],
        *,
        prompt: str,
        thread_id: str | None = None,
        timezone: str = "UTC",
        history_limit: int = 10,
    ) -> Dict[str, Any]:
        action_url = str(agent.get("actionUrl") or "").strip()
        if not action_url:
            raise ExternalAgentGatewayError(
                f"External agent '{agent.get('id')}' action URL is not configured",
                status_code=400,
            )

        agent_id = str(agent.get("id") or "openclaw").strip() or "openclaw"
        resolved_thread_id = str(thread_id or "").strip() or _new_openclaw_thread_id()
        model = str(agent.get("model") or f"{agent_id}/default").strip() or f"{agent_id}/default"

        payload: Dict[str, Any] = {
            "model": model,
            "messages": _build_openclaw_messages(agent_id, thread_id, prompt),
        }

        response = _request_json(
            action_url,
            method="POST",
            payload=payload,
            auth_token=str(agent.get("_actionAuthToken") or "").strip() or None,
            headers=_headers(agent.get("_actionHeaders")),
            timeout=60.0,
        )

        latest_turn = _record_openclaw_turn(
            agent_id,
            resolved_thread_id,
            prompt=prompt,
            reply=_extract_openai_compat_reply(response),
        )

        return {
            "agentId": agent_id,
            "threadId": resolved_thread_id,
            "threadCreated": not str(thread_id or "").strip(),
            "messageId": str(response.get("id") or ""),
            "status": "completed",
            "actionUrl": action_url,
            "hasMore": False,
            "turns": [latest_turn],
            "latestTurn": latest_turn,
        }

    def history(
        self,
        agent: Dict[str, Any],
        *,
        thread_id: str,
        limit: int = 10,
    ) -> Dict[str, Any]:
        agent_id = str(agent.get("id") or "openclaw").strip() or "openclaw"
        history = _read_openclaw_history(agent_id, thread_id, limit=limit)
        return {
            "agentId": agent_id,
            "threadId": thread_id,
            **history,
        }


class OpenAICompatAdapter(ExternalAgentAdapter):
    """Adapter for standard OpenAI-compatible chat completion APIs (/v1/chat/completions)."""

    protocol_ids = ("openai-compat", "openai-compatible")

    def handoff(
        self,
        agent: Dict[str, Any],
        *,
        prompt: str,
        thread_id: str | None = None,
        timezone: str = "UTC",
        history_limit: int = 10,
    ) -> Dict[str, Any]:
        action_url = str(agent.get("actionUrl") or "").strip()
        if not action_url:
            raise ExternalAgentGatewayError(
                f"External agent '{agent.get('id')}' action URL is not configured",
                status_code=400,
            )

        model = str(agent.get("model") or agent.get("id") or "default").strip()
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }

        response = _request_json(
            action_url,
            method="POST",
            payload=payload,
            auth_token=str(agent.get("_actionAuthToken") or "").strip() or None,
            headers=_headers(agent.get("_actionHeaders")),
            timeout=60.0,
        )

        reply = _extract_openai_compat_reply(response)

        latest_turn = {
            "turn_number": 1,
            "user_input": prompt,
            "response": reply,
            "state": "completed",
            "started_at": None,
            "completed_at": None,
            "tool_calls": [],
        }

        return {
            "agentId": str(agent.get("id") or "hermes"),
            "threadId": thread_id or "",
            "threadCreated": False,
            "messageId": str(response.get("id") or ""),
            "status": "completed",
            "actionUrl": action_url,
            "hasMore": False,
            "turns": [latest_turn],
            "latestTurn": latest_turn,
        }

    def history(
        self,
        agent: Dict[str, Any],
        *,
        thread_id: str,
        limit: int = 10,
    ) -> Dict[str, Any]:
        raise ExternalAgentGatewayError(
            f"External agent '{agent.get('id')}' (openai-compat) does not support history retrieval",
            status_code=400,
        )


_ADAPTERS: List[ExternalAgentAdapter] = [
    ChatThreadAdapter(),
    HttpJsonAdapter(),
    NanobotAdapter(),
    OpenClawGatewayAdapter(),
    OpenAICompatAdapter(),
]


def list_external_agent_adapter_protocols() -> List[str]:
    protocols: List[str] = []
    for adapter in _ADAPTERS:
        protocols.extend(adapter.protocol_ids)
    return sorted(set(protocols))


def handoff_external_agent(
    agent: Dict[str, Any],
    *,
    prompt: str,
    thread_id: str | None = None,
    timezone: str = "UTC",
    history_limit: int = 10,
) -> Dict[str, Any]:
    adapter = _resolve_adapter(agent, require_capability="handoff")
    return adapter.handoff(
        agent,
        prompt=prompt,
        thread_id=thread_id,
        timezone=timezone,
        history_limit=history_limit,
    )


def get_external_agent_history(
    agent: Dict[str, Any],
    *,
    thread_id: str,
    limit: int = 10,
) -> Dict[str, Any]:
    adapter = _resolve_adapter(agent, require_capability="history")
    return adapter.history(agent, thread_id=thread_id, limit=limit)


def _has_authorization_header(headers: Any) -> bool:
    if not isinstance(headers, dict):
        return False
    for key, value in headers.items():
        if str(key).strip().lower() == "authorization" and str(value or "").strip():
            return True
    return False


def _ensure_required_auth(agent: Dict[str, Any], *, require_capability: str) -> None:
    if require_capability == "handoff":
        token = agent.get("_actionAuthToken")
        headers = agent.get("_actionHeaders")
        env_name = str(agent.get("_actionAuthTokenEnv") or "").strip()
        scope = "handoff"
    elif require_capability == "history":
        token = agent.get("_historyAuthToken")
        headers = agent.get("_historyHeaders")
        env_name = str(agent.get("_historyAuthTokenEnv") or "").strip()
        scope = "history"
    elif require_capability == "mcp":
        token = agent.get("_mcpAuthToken")
        headers = agent.get("_mcpHeaders")
        env_name = str(agent.get("_mcpAuthTokenEnv") or "").strip()
        scope = "mcp"
    else:
        return

    if str(token or "").strip() or _has_authorization_header(headers) or not env_name:
        return

    agent_id = str(agent.get("id") or "external-agent").strip() or "external-agent"
    raise ExternalAgentGatewayError(
        f"External agent '{agent_id}' requires auth for {scope}. Set {env_name}.",
        status_code=400,
    )


def _resolve_adapter(
    agent: Dict[str, Any],
    *,
    require_capability: str,
) -> ExternalAgentAdapter:
    agent_id = str(agent.get("id") or "external-agent")
    protocol = str(agent.get("protocol") or "").strip().lower()
    capabilities = {
        str(capability).strip().lower()
        for capability in agent.get("capabilities") or []
        if str(capability).strip()
    }

    if require_capability and require_capability not in capabilities:
        raise ExternalAgentGatewayError(
            f"External agent '{agent_id}' does not support '{require_capability}'",
            status_code=400,
            details={
                "agentId": agent_id,
                "protocol": protocol,
                "capabilities": sorted(capabilities),
            },
        )

    _ensure_required_auth(agent, require_capability=require_capability)

    for adapter in _ADAPTERS:
        if adapter.matches(protocol):
            return adapter

    status_code = 501 if protocol in {"mcp", "model-context-protocol"} else 400
    raise ExternalAgentGatewayError(
        f"No external-agent adapter is registered for protocol '{protocol or 'unknown'}'",
        status_code=status_code,
        details={
            "agentId": agent_id,
            "protocol": protocol,
            "supportedProtocols": list_external_agent_adapter_protocols(),
        },
    )


def _request_json(
    url: str,
    *,
    method: str,
    payload: Dict[str, Any] | None = None,
    headers: Dict[str, str] | None = None,
    auth_token: str | None = None,
    timeout: float = 20.0,
) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request_headers: Dict[str, str] = {
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
        message = _extract_error_message(details) or f"External agent request failed with HTTP {status_code}"
        raise ExternalAgentGatewayError(message, status_code=status_code, details=details) from exc
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise ExternalAgentGatewayError(f"External agent request failed: {exc}", status_code=502) from exc

    details = _decode_json(raw_body)
    if not isinstance(details, dict):
        raise ExternalAgentGatewayError("External agent returned an invalid JSON payload", details=raw_body)
    return details


def _field_map(raw: Any) -> Dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    return {
        str(key): str(value)
        for key, value in raw.items()
        if str(key).strip() and value is not None and str(value).strip()
    }


def _headers(raw: Any) -> Dict[str, str] | None:
    if not isinstance(raw, dict):
        return None
    return {
        str(key): str(value)
        for key, value in raw.items()
        if str(key).strip() and value is not None
    }


def _dig(data: Any, path: str) -> Any:
    if not path:
        return None
    current = data
    for segment in path.split("."):
        if isinstance(current, dict):
            current = current.get(segment)
        elif isinstance(current, list) and segment.isdigit():
            index = int(segment)
            if index < 0 or index >= len(current):
                return None
            current = current[index]
        else:
            return None
    return current


def _stringify_content(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False)


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