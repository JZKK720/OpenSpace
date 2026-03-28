from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlsplit
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "openspace" / "config" / "external_agents.json"

_KNOWN_CAPABILITIES = {"handoff", "history", "mcp"}


def _load_registry_data() -> Dict[str, Any]:
    config_path = Path(os.environ.get("OPENSPACE_EXTERNAL_AGENTS_CONFIG", DEFAULT_CONFIG_PATH))
    if not config_path.exists():
        return {}

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    return raw if isinstance(raw, dict) else {}


def _resolve_value(item: Dict[str, Any], key: str) -> str:
    env_key = str(item.get(f"{key}_env") or "").strip()
    if env_key:
        env_value = os.environ.get(env_key, "").strip()
        if env_value:
            return env_value
    return str(item.get(key) or "").strip()


def _resolve_headers(item: Dict[str, Any], key: str) -> Dict[str, str]:
    env_key = str(item.get(f"{key}_env") or "").strip()
    if env_key:
        env_value = os.environ.get(env_key, "").strip()
        if env_value:
            try:
                parsed = json.loads(env_value)
                if isinstance(parsed, dict):
                    return {
                        str(header): str(value)
                        for header, value in parsed.items()
                        if str(header).strip() and value is not None
                    }
            except json.JSONDecodeError:
                return {}

    raw = item.get(key)
    if not isinstance(raw, dict):
        return {}
    return {
        str(header): str(value)
        for header, value in raw.items()
        if str(header).strip() and value is not None
    }


def _resolve_mapping(item: Dict[str, Any], key: str) -> Dict[str, str]:
    raw = item.get(key)
    if not isinstance(raw, dict):
        return {}
    return {
        str(mapping_key): str(mapping_value)
        for mapping_key, mapping_value in raw.items()
        if str(mapping_key).strip() and mapping_value is not None and str(mapping_value).strip()
    }


def _resolve_string_list(raw: Any) -> List[str]:
    if not isinstance(raw, list):
        return []

    values: List[str] = []
    seen = set()
    for item in raw:
        value = str(item or "").strip()
        if value and value not in seen:
            values.append(value)
            seen.add(value)
    return values


def _is_chat_thread_protocol(protocol: str) -> bool:
    return protocol in {"chat-thread", "threaded-chat"}


def _build_mcp_server_name(agent_id: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in agent_id.lower())
    return f"external-{safe}"


def _normalize_capabilities(
    item: Dict[str, Any],
    *,
    protocol: str,
    action_url: str,
    history_url: str,
    mcp_url: str,
) -> List[str]:
    configured = item.get("capabilities")
    capabilities: List[str] = []
    if isinstance(configured, list):
        for capability in configured:
            value = str(capability or "").strip().lower()
            if value and value in _KNOWN_CAPABILITIES and value not in capabilities:
                capabilities.append(value)

    if not capabilities:
        if _is_chat_thread_protocol(protocol):
            capabilities.extend(["handoff", "history"])
        elif protocol in {"mcp", "model-context-protocol"}:
            capabilities.append("mcp")
        elif action_url:
            capabilities.append("handoff")

    if action_url and "handoff" not in capabilities:
        capabilities.append("handoff")
    if _is_chat_thread_protocol(protocol) and action_url and "history" not in capabilities:
        capabilities.append("history")
    elif history_url and "history" not in capabilities:
        capabilities.append("history")
    if mcp_url and "mcp" not in capabilities:
        capabilities.append("mcp")

    if not action_url:
        capabilities = [capability for capability in capabilities if capability != "handoff"]
    if _is_chat_thread_protocol(protocol) and not action_url:
        capabilities = [capability for capability in capabilities if capability != "history"]
    if not _is_chat_thread_protocol(protocol) and not history_url:
        capabilities = [capability for capability in capabilities if capability != "history"]
    if not mcp_url:
        capabilities = [capability for capability in capabilities if capability != "mcp"]

    return capabilities


def _resolve_protocol(item: Dict[str, Any], *, action_url: str, mcp_url: str) -> str:
    explicit = str(item.get("protocol") or "").strip().lower()
    if explicit:
        return explicit
    if mcp_url and not action_url:
        return "mcp"
    if action_url:
        return "http-json"
    return "unknown"


def _resolve_handoff_mode(protocol: str, capabilities: List[str]) -> str:
    if "handoff" not in capabilities:
        return "none"
    if _is_chat_thread_protocol(protocol):
        return "chat_thread"
    return "request_response"


def _resolve_history_mode(protocol: str, capabilities: List[str]) -> str:
    if "history" not in capabilities:
        return "none"
    if _is_chat_thread_protocol(protocol):
        return "thread_history"
    return "poll"


def load_external_mcp_servers() -> List[Dict[str, Any]]:
    raw = _load_registry_data()
    mcp_servers = raw.get("mcp_servers")
    if not isinstance(mcp_servers, list):
        mcp_servers = raw.get("mcpServers")
    if not isinstance(mcp_servers, list):
        return []

    resolved_servers: List[Dict[str, Any]] = []
    for item in mcp_servers:
        if not isinstance(item, dict):
            continue

        server_id = str(item.get("id") or "").strip()
        if not server_id:
            continue

        url = _resolve_url(item, "url")
        ws_url = _resolve_url(item, "ws_url")
        health_url = _resolve_url(item, "health_url") or url
        command = str(item.get("command") or "").strip()
        cwd = str(item.get("cwd") or "").strip()
        args = _resolve_string_list(item.get("args"))
        env = _resolve_headers(item, "env")
        auth_token = _resolve_value(item, "auth_token")
        headers = _resolve_headers(item, "headers")
        tags = _resolve_string_list(item.get("tags"))

        if not any([url, ws_url, command]):
            continue

        server_name = str(
            item.get("server_name")
            or item.get("serverName")
            or _build_mcp_server_name(server_id)
        ).strip()

        resolved_servers.append(
            {
                "id": server_id,
                "name": str(item.get("name") or server_id.replace("-", " ").title()),
                "description": str(item.get("description") or ""),
                "serverName": server_name,
                "tags": tags,
                "url": url,
                "wsUrl": ws_url,
                "healthUrl": health_url,
                "command": command,
                "args": args,
                "cwd": cwd,
                "env": env,
                "_authToken": auth_token,
                "_headers": headers,
            }
        )

    return resolved_servers


def load_external_agents() -> List[Dict[str, Any]]:
    raw = _load_registry_data()

    agents = raw.get("agents") if isinstance(raw, dict) else None
    if not isinstance(agents, list):
        return []

    shared_mcp_servers = {server["id"]: server for server in load_external_mcp_servers()}
    resolved_agents: List[Dict[str, Any]] = []
    for item in agents:
        if not isinstance(item, dict):
            continue
        agent_id = str(item.get("id") or "").strip()
        if not agent_id:
            continue

        public_url = _resolve_url(item, "public_url")
        internal_url = _resolve_url(item, "internal_url") or public_url
        health_url = _resolve_url(item, "health_url") or internal_url or public_url
        action_url = _resolve_url(item, "action_url")
        history_url = _resolve_url(item, "history_url")
        mcp_url = _resolve_url(item, "mcp_url")
        action_auth_token = _resolve_value(item, "action_auth_token")
        history_auth_token = _resolve_value(item, "history_auth_token") or action_auth_token
        mcp_auth_token = _resolve_value(item, "mcp_auth_token")
        action_headers = _resolve_headers(item, "action_headers")
        history_headers = _resolve_headers(item, "history_headers") or action_headers
        mcp_headers = _resolve_headers(item, "mcp_headers")
        request_field_map = _resolve_mapping(item, "request_fields")
        response_field_map = _resolve_mapping(item, "response_fields")
        history_request_field_map = _resolve_mapping(item, "history_request_fields")
        history_response_field_map = _resolve_mapping(item, "history_response_fields")
        tags = _resolve_string_list(item.get("tags"))
        linked_mcp_server_ids = _resolve_string_list(
            item.get("linked_mcp_servers") or item.get("linkedMcpServers")
        )
        linked_mcp_servers = [
            _public_mcp_server_payload(shared_mcp_servers[server_id])
            for server_id in linked_mcp_server_ids
            if server_id in shared_mcp_servers
        ]
        unresolved_linked_mcp_server_ids = [
            server_id
            for server_id in linked_mcp_server_ids
            if server_id not in shared_mcp_servers
        ]

        if not any([public_url, internal_url, health_url, action_url, history_url, mcp_url]):
            continue

        protocol = _resolve_protocol(item, action_url=action_url, mcp_url=mcp_url)
        capabilities = _normalize_capabilities(
            item,
            protocol=protocol,
            action_url=action_url,
            history_url=history_url,
            mcp_url=mcp_url,
        )
        handoff_mode = str(item.get("handoff_mode") or _resolve_handoff_mode(protocol, capabilities)).strip().lower()
        history_mode = str(item.get("history_mode") or _resolve_history_mode(protocol, capabilities)).strip().lower()
        standalone_app_id = str(item.get("standalone_app_id") or "").strip()
        mcp_server_name = ""
        if mcp_url:
            mcp_server_name = str(item.get("mcp_server_name") or _build_mcp_server_name(agent_id)).strip()

        resolved_agents.append(
            {
                "id": agent_id,
                "name": str(item.get("name") or agent_id.replace("-", " ").title()),
                "description": str(item.get("description") or ""),
                "kind": str(item.get("kind") or "external-agent"),
                "protocol": protocol,
                "capabilities": capabilities,
                "handoffMode": handoff_mode,
                "historyMode": history_mode,
                "standaloneAppId": standalone_app_id,
                "linkedMcpServerIds": linked_mcp_server_ids,
                "linkedMcpServers": linked_mcp_servers,
                "unresolvedLinkedMcpServerIds": unresolved_linked_mcp_server_ids,
                "mcpServerName": mcp_server_name,
                "tags": tags,
                "publicUrl": public_url,
                "internalUrl": internal_url,
                "healthUrl": health_url,
                "actionUrl": action_url,
                "historyUrl": history_url,
                "mcpUrl": mcp_url,
                "hasActionUrl": bool(action_url),
                "hasMcpUrl": bool(mcp_url),
                "supportsHandoff": bool(action_url) and "handoff" in capabilities,
                "supportsHistory": bool(action_url) and "history" in capabilities,
                "supportsMcp": bool(mcp_url) and "mcp" in capabilities,
                "_actionAuthToken": action_auth_token,
                "_historyAuthToken": history_auth_token,
                "_mcpAuthToken": mcp_auth_token,
                "_actionHeaders": action_headers,
                "_historyHeaders": history_headers,
                "_mcpHeaders": mcp_headers,
                "_requestFieldMap": request_field_map,
                "_responseFieldMap": response_field_map,
                "_historyRequestFieldMap": history_request_field_map,
                "_historyResponseFieldMap": history_response_field_map,
            }
        )

    return resolved_agents


def get_external_agents_status(timeout: float = 1.5) -> List[Dict[str, Any]]:
    statuses: List[Dict[str, Any]] = []
    for agent in load_external_agents():
        probe_url = agent.get("healthUrl") or agent.get("internalUrl") or agent.get("publicUrl")
        probe = _probe_url(str(probe_url or ""), timeout=timeout)
        statuses.append(
            {
                **_public_agent_payload(agent),
                "available": probe["available"],
                "status": "up" if probe["available"] else "down",
                "statusCode": probe["statusCode"],
                "latencyMs": probe["latencyMs"],
                "error": probe["error"],
            }
        )
    return statuses


def get_external_agent(agent_id: str) -> Dict[str, Any] | None:
    lookup_id = str(agent_id or "").strip().lower()
    if not lookup_id:
        return None

    for agent in load_external_agents():
        if str(agent.get("id") or "").strip().lower() == lookup_id:
            return agent
    return None


def get_delegateable_external_agents(
    timeout: float = 1.5,
    *,
    available_only: bool = False,
) -> List[Dict[str, Any]]:
    items = [item for item in get_external_agents_status(timeout=timeout) if item.get("supportsHandoff")]
    if available_only:
        items = [item for item in items if item.get("available")]
    return items


def get_mcp_external_agents(*, available_only: bool = False) -> List[Dict[str, Any]]:
    items = [item for item in load_external_agents() if item.get("supportsMcp")]
    if not available_only:
        return items

    available_ids = {
        item.get("id")
        for item in get_external_agents_status()
        if item.get("supportsMcp") and item.get("available")
    }
    return [item for item in items if item.get("id") in available_ids]


def get_external_mcp_servers(*, available_only: bool = False) -> List[Dict[str, Any]]:
    items = load_external_mcp_servers()
    if not available_only:
        return items

    available_ids = {
        item.get("id")
        for item in get_external_mcp_servers_status()
        if item.get("available")
    }
    return [item for item in items if item.get("id") in available_ids]


def get_external_mcp_servers_status(timeout: float = 1.5) -> List[Dict[str, Any]]:
    statuses: List[Dict[str, Any]] = []
    for server in load_external_mcp_servers():
        probe = _probe_mcp_server(server, timeout=timeout)
        statuses.append(
            {
                **_public_mcp_server_payload(server),
                "available": probe["available"],
                "status": "up" if probe["available"] else "down",
                "statusCode": probe["statusCode"],
                "latencyMs": probe["latencyMs"],
                "error": probe["error"],
            }
        )
    return statuses


def build_external_mcp_server_configs(*, available_only: bool = False) -> Dict[str, Dict[str, Any]]:
    servers: Dict[str, Dict[str, Any]] = {}
    for shared_server in get_external_mcp_servers(available_only=available_only):
        server_name = str(shared_server.get("serverName") or _build_mcp_server_name(str(shared_server.get("id") or "external"))).strip()
        server_config = _build_mcp_server_config(shared_server)
        if server_name and server_config and server_name not in servers:
            servers[server_name] = server_config

    for agent in get_mcp_external_agents(available_only=available_only):
        server_name = str(agent.get("mcpServerName") or _build_mcp_server_name(str(agent.get("id") or "external")))
        server_config = _build_mcp_server_config(
            {
                "url": agent.get("mcpUrl"),
                "serverName": server_name,
                "_authToken": agent.get("_mcpAuthToken"),
                "_headers": agent.get("_mcpHeaders"),
            }
        )
        if server_name and server_config and server_name not in servers:
            servers[server_name] = server_config
    return servers


def _resolve_url(item: Dict[str, Any], key: str) -> str:
    return _resolve_value(item, key)


def _public_agent_payload(agent: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: value
        for key, value in agent.items()
        if not str(key).startswith("_")
    }


def _public_mcp_server_payload(server: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: value
        for key, value in server.items()
        if not str(key).startswith("_")
    }


def _build_mcp_server_config(server: Dict[str, Any]) -> Dict[str, Any]:
    config: Dict[str, Any] = {}
    url = str(server.get("url") or "").strip()
    ws_url = str(server.get("wsUrl") or "").strip()
    command = str(server.get("command") or "").strip()
    args = server.get("args") if isinstance(server.get("args"), list) else []
    cwd = str(server.get("cwd") or "").strip()
    env = server.get("env") if isinstance(server.get("env"), dict) else {}
    auth_token = str(server.get("_authToken") or "").strip()
    headers = server.get("_headers") if isinstance(server.get("_headers"), dict) else {}

    if ws_url:
        config["ws_url"] = ws_url
    elif url:
        parsed = urlsplit(url)
        if parsed.scheme in {"ws", "wss"}:
            config["ws_url"] = url
        else:
            config["url"] = url
    elif command:
        config["command"] = command
    else:
        return {}

    if args:
        config["args"] = args
    if cwd:
        config["cwd"] = cwd
    if env:
        config["env"] = env
    if auth_token:
        config["auth_token"] = auth_token
    if headers:
        config["headers"] = headers
    return config


def _probe_mcp_server(server: Dict[str, Any], *, timeout: float) -> Dict[str, Any]:
    probe_url = str(server.get("healthUrl") or server.get("url") or "").strip()
    if probe_url:
        return _probe_url(probe_url, timeout=timeout)

    if str(server.get("wsUrl") or "").strip() or str(server.get("command") or "").strip():
        return {
            "available": True,
            "statusCode": 0,
            "latencyMs": None,
            "error": None,
        }

    return {
        "available": False,
        "statusCode": 0,
        "latencyMs": None,
        "error": "No probe URL configured",
    }


def _probe_url(url: str, timeout: float) -> Dict[str, Any]:
    if not url:
        return {
            "available": False,
            "statusCode": 0,
            "latencyMs": None,
            "error": "No probe URL configured",
        }

    head_result = _probe_once(url, method="HEAD", timeout=timeout)
    if head_result["available"] or head_result["statusCode"] not in {405, 501}:
        return head_result
    return _probe_once(url, method="GET", timeout=timeout)


def _probe_once(url: str, *, method: str, timeout: float) -> Dict[str, Any]:
    request = Request(url, method=method, headers={"User-Agent": "OpenSpaceDashboard/1.0"})
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=timeout) as response:
            status_code = int(getattr(response, "status", 200))
            latency_ms = int((time.perf_counter() - started) * 1000)
            return {
                "available": 200 <= status_code < 500,
                "statusCode": status_code,
                "latencyMs": latency_ms,
                "error": None,
            }
    except HTTPError as exc:
        status_code = int(getattr(exc, "code", 0) or 0)
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            "available": 200 <= status_code < 500,
            "statusCode": status_code,
            "latencyMs": latency_ms,
            "error": None if 200 <= status_code < 500 else str(exc.reason),
        }
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        return {
            "available": False,
            "statusCode": 0,
            "latencyMs": int(timeout * 1000),
            "error": str(exc),
        }