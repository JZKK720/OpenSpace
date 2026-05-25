from __future__ import annotations

import json
from typing import Any, Dict, List
from uuid import uuid4
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class OpenHumanRpcGatewayError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 502, details: Any | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details


def ping_openhuman_core(
    rpc_url: str,
    *,
    auth_token: str | None = None,
    headers: Dict[str, str] | None = None,
    timeout: float = 20.0,
) -> Dict[str, Any]:
    result, request_id = _call_openhuman_rpc(
        rpc_url,
        method="core.ping",
        params={},
        auth_token=auth_token,
        headers=headers,
        timeout=timeout,
    )
    return {
        "requestId": request_id,
        "ok": bool(result.get("ok")),
        "result": result,
    }


def get_openhuman_inference_status(
    rpc_url: str,
    *,
    auth_token: str | None = None,
    headers: Dict[str, str] | None = None,
    timeout: float = 20.0,
) -> Dict[str, Any]:
    result, request_id = _call_openhuman_rpc(
        rpc_url,
        method="openhuman.inference_status",
        params={},
        auth_token=auth_token,
        headers=headers,
        timeout=timeout,
    )
    payload = result.get("result") if isinstance(result.get("result"), dict) else {}
    logs = _string_list(result.get("logs"))
    return {
        "requestId": request_id,
        "state": str(payload.get("state") or "").strip(),
        "provider": str(payload.get("provider") or "").strip(),
        "logs": logs,
        "result": payload,
    }


def submit_openhuman_inference_prompt(
    rpc_url: str,
    *,
    prompt: str,
    auth_token: str | None = None,
    headers: Dict[str, str] | None = None,
    max_tokens: int = 512,
    no_think: bool = True,
    timeout: float = 120.0,
) -> Dict[str, Any]:
    cleaned_prompt = str(prompt or "").strip()
    if not cleaned_prompt:
        raise OpenHumanRpcGatewayError("prompt is required", status_code=400)

    result, request_id = _call_openhuman_rpc(
        rpc_url,
        method="openhuman.inference_prompt",
        params={
            "prompt": cleaned_prompt,
            "max_tokens": max(1, int(max_tokens)),
            "no_think": bool(no_think),
        },
        auth_token=auth_token,
        headers=headers,
        timeout=timeout,
    )
    return {
        "requestId": request_id,
        "response": str(result.get("result") or "").strip(),
        "logs": _string_list(result.get("logs")),
        "result": result,
    }


def get_openhuman_client_config(
    rpc_url: str,
    *,
    auth_token: str | None = None,
    headers: Dict[str, str] | None = None,
    timeout: float = 20.0,
) -> Dict[str, Any]:
    result, request_id = _call_openhuman_rpc(
        rpc_url,
        method="config.get_client_config",
        params={},
        auth_token=auth_token,
        headers=headers,
        timeout=timeout,
    )
    return {"requestId": request_id, "result": result}


def get_openhuman_runtime_flags(
    rpc_url: str,
    *,
    auth_token: str | None = None,
    headers: Dict[str, str] | None = None,
    timeout: float = 20.0,
) -> Dict[str, Any]:
    result, request_id = _call_openhuman_rpc(
        rpc_url,
        method="config.get_runtime_flags",
        params={},
        auth_token=auth_token,
        headers=headers,
        timeout=timeout,
    )
    return {"requestId": request_id, "result": result}


def get_openhuman_agent_server_status(
    rpc_url: str,
    *,
    auth_token: str | None = None,
    headers: Dict[str, str] | None = None,
    timeout: float = 20.0,
) -> Dict[str, Any]:
    result, request_id = _call_openhuman_rpc(
        rpc_url,
        method="config.agent_server_status",
        params={},
        auth_token=auth_token,
        headers=headers,
        timeout=timeout,
    )
    return {"requestId": request_id, "result": result}


def update_openhuman_local_ai_settings(
    rpc_url: str,
    *,
    patch: Dict[str, Any],
    auth_token: str | None = None,
    headers: Dict[str, str] | None = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    if not isinstance(patch, dict):
        raise OpenHumanRpcGatewayError("patch must be a dict", status_code=400)
    result, request_id = _call_openhuman_rpc(
        rpc_url,
        method="config.update_local_ai_settings",
        params=patch,
        auth_token=auth_token,
        headers=headers,
        timeout=timeout,
    )
    return {"requestId": request_id, "result": result}


def update_openhuman_model_settings(
    rpc_url: str,
    *,
    patch: Dict[str, Any],
    auth_token: str | None = None,
    headers: Dict[str, str] | None = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    if not isinstance(patch, dict):
        raise OpenHumanRpcGatewayError("patch must be a dict", status_code=400)
    result, request_id = _call_openhuman_rpc(
        rpc_url,
        method="config.update_model_settings",
        params=patch,
        auth_token=auth_token,
        headers=headers,
        timeout=timeout,
    )
    return {"requestId": request_id, "result": result}


def get_openhuman_version(
    rpc_url: str,
    *,
    auth_token: str | None = None,
    headers: Dict[str, str] | None = None,
    timeout: float = 20.0,
) -> Dict[str, Any]:
    result, request_id = _call_openhuman_rpc(
        rpc_url,
        method="core.version",
        params={},
        auth_token=auth_token,
        headers=headers,
        timeout=timeout,
    )
    return {
        "requestId": request_id,
        "version": str(result.get("version") or "").strip(),
        "result": result,
    }


def _call_openhuman_rpc(
    rpc_url: str,
    *,
    method: str,
    params: Dict[str, Any],
    auth_token: str | None = None,
    headers: Dict[str, str] | None = None,
    timeout: float = 20.0,
) -> tuple[Dict[str, Any], str]:
    cleaned_rpc_url = str(rpc_url or "").strip()
    if not cleaned_rpc_url:
        raise OpenHumanRpcGatewayError("OpenHuman RPC URL is not configured", status_code=400)

    request_id = _new_request_id(method)
    response = _request_json(
        cleaned_rpc_url,
        method="POST",
        payload={
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        },
        auth_token=auth_token,
        headers=headers,
        timeout=timeout,
    )

    error = response.get("error")
    if isinstance(error, dict):
        status_code = int(error.get("code") or 0)
        raise OpenHumanRpcGatewayError(
            _extract_error_message(error) or f"OpenHuman RPC method '{method}' failed",
            status_code=400 if status_code == 0 else 502,
            details=error,
        )
    if error is not None:
        raise OpenHumanRpcGatewayError(
            str(error),
            status_code=502,
            details=error,
        )

    result = response.get("result")
    if not isinstance(result, dict):
        raise OpenHumanRpcGatewayError(
            f"OpenHuman RPC method '{method}' returned an invalid result payload",
            details=response,
        )

    return result, request_id


def _new_request_id(method: str) -> str:
    suffix = str(method or "rpc").strip().lower().replace(".", "-") or "rpc"
    return f"openspace-{suffix}-{uuid4().hex[:8]}"


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
    request_headers: Dict[str, str] = {
        "User-Agent": "OpenSpaceOpenHumanRPC/1.0",
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
        raise OpenHumanRpcGatewayError(
            _extract_error_message(details) or f"OpenHuman RPC request failed with HTTP {status_code}",
            status_code=status_code,
            details=details,
        ) from exc
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise OpenHumanRpcGatewayError(f"OpenHuman RPC request failed: {exc}", status_code=502) from exc

    details = _decode_json(raw_body)
    if not isinstance(details, dict):
        raise OpenHumanRpcGatewayError("OpenHuman RPC returned an invalid JSON payload", details=raw_body)
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


def _string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item or "").strip()]