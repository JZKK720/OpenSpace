from __future__ import annotations

import os
from typing import Any, Dict

from openspace.openhuman_rpc_gateway import (
    OpenHumanRpcGatewayError,
    get_openhuman_agent_server_status,
    get_openhuman_client_config,
    get_openhuman_inference_status,
    get_openhuman_runtime_flags,
    get_openhuman_version,
    ping_openhuman_core,
    submit_openhuman_inference_prompt,
    update_openhuman_local_ai_settings,
    update_openhuman_model_settings,
)

_DEFAULT_RPC_URL = "http://openhuman:7788/rpc"
_DEFAULT_TIMEOUT_MS = 120_000


def _rpc_url() -> str:
    value = os.environ.get("OPENHUMAN_RPC_URL", "").strip()
    return value or _DEFAULT_RPC_URL


def _auth_token() -> str | None:
    value = os.environ.get("OPENHUMAN_CORE_TOKEN", "").strip()
    return value or None


def _timeout_seconds() -> float:
    raw = os.environ.get("OPENHUMAN_REQUEST_TIMEOUT_MS", "").strip()
    try:
        ms = int(raw)
        if ms > 0:
            return ms / 1000.0
    except (ValueError, TypeError):
        pass
    return _DEFAULT_TIMEOUT_MS / 1000.0


def ping() -> bool:
    """Call core.ping. Returns True if OpenHuman responds ok, False on any error."""
    try:
        result = ping_openhuman_core(
            _rpc_url(),
            auth_token=_auth_token(),
            timeout=_timeout_seconds(),
        )
        return bool(result.get("ok"))
    except (OpenHumanRpcGatewayError, Exception):
        return False


def inference_status() -> Dict[str, Any]:
    """Call openhuman.inference_status. Returns the result dict or raises on error."""
    return get_openhuman_inference_status(
        _rpc_url(),
        auth_token=_auth_token(),
        timeout=_timeout_seconds(),
    )


def inference_prompt(prompt: str, max_tokens: int = 512, no_think: bool = True) -> str:
    """Call openhuman.inference_prompt. Returns the response string or raises on error."""
    result = submit_openhuman_inference_prompt(
        _rpc_url(),
        prompt=prompt,
        auth_token=_auth_token(),
        max_tokens=max_tokens,
        no_think=no_think,
        timeout=_timeout_seconds(),
    )
    return result.get("response", "")


def inference_chat() -> None:
    # TODO: implement after inference_prompt path is stable
    raise NotImplementedError("inference_chat is not yet implemented")


def client_config() -> Dict[str, Any]:
    """Call config.get_client_config. Returns the config dict (api_key_set is bool, never raw key)."""
    return get_openhuman_client_config(
        _rpc_url(),
        auth_token=_auth_token(),
        timeout=_timeout_seconds(),
    )


def runtime_flags() -> Dict[str, Any]:
    """Call config.get_runtime_flags. Returns the runtime flags dict."""
    return get_openhuman_runtime_flags(
        _rpc_url(),
        auth_token=_auth_token(),
        timeout=_timeout_seconds(),
    )


def agent_server_status() -> Dict[str, Any]:
    """Call config.agent_server_status. Returns the agent server status dict."""
    return get_openhuman_agent_server_status(
        _rpc_url(),
        auth_token=_auth_token(),
        timeout=_timeout_seconds(),
    )


def update_local_ai(patch: Dict[str, Any]) -> Dict[str, Any]:
    """Call config.update_local_ai_settings with the given patch dict."""
    return update_openhuman_local_ai_settings(
        _rpc_url(),
        patch=patch,
        auth_token=_auth_token(),
        timeout=_timeout_seconds(),
    )


def update_model_settings(patch: Dict[str, Any]) -> Dict[str, Any]:
    """Call config.update_model_settings with the given patch dict.

    api_key is write-only: it is forwarded to OpenHuman but never echoed or logged.
    """
    return update_openhuman_model_settings(
        _rpc_url(),
        patch=patch,
        auth_token=_auth_token(),
        timeout=_timeout_seconds(),
    )


def version() -> str:
    """Call core.version. Returns the version string."""
    result = get_openhuman_version(
        _rpc_url(),
        auth_token=_auth_token(),
        timeout=_timeout_seconds(),
    )
    return result.get("version", "")
