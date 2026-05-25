from __future__ import annotations

import os
from typing import Any, Dict

from openspace.openhuman_rpc_gateway import (
    OpenHumanRpcGatewayError,
    get_openhuman_inference_status,
    ping_openhuman_core,
    submit_openhuman_inference_prompt,
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
